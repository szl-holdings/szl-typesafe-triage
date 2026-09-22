# szl_bake_admin.ps1 - SZL typesafe-triage governed bake, elevated runner
# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
#
# ============================================================================
# WHY THIS ONE IS ELEVATED
# ============================================================================
# Three operations here genuinely require administrator rights. Everything else
# runs in a local venv and would work unelevated:
#
#   1. Win32 long-path support (HKLM registry) - HF cache paths routinely
#      exceed 260 chars and fail opaquely mid-download.
#   2. Machine-wide execution policy (RemoteSigned) - needed only if policy is
#      Restricted.
#   3. Defender exclusion for the venv (-AddDefenderExclusion) - pip unpacking
#      torch triggers per-file scanning; exclusion cuts install time hard.
#
# Both 1 and 3 are OPT-IN switches. They are off unless you ask.
#
# KNOWN COST OF ELEVATION: pip executes third-party package code. Under admin,
# that code runs elevated. torch + transformers + trl pull in a large
# transitive tree. This is the actual risk of running the block this way.
#
# ============================================================================
# A NOTE ON COMPARING COMMAND OUTPUT
# ============================================================================
# `& python script.py` returns an ARRAY of lines. In PowerShell, -match and
# -notmatch against a collection act as FILTERS: they return the matching or
# non-matching elements and do NOT populate $Matches. A non-empty array is
# truthy. An earlier revision wrote
#
#     if ($oracle -notmatch "FALSE LABEL ON REFUSAL:\s*0") { Die ... }
#
# which fired on a perfect run, because most lines do not contain that phrase.
# Every output comparison below goes through Out-String first. Collection
# membership uses -contains / -notcontains, which are real booleans.
#
# ============================================================================
# USAGE
# ============================================================================
#   .\szl_bake_admin.ps1                          # self-elevates, runs the bake
#   .\szl_bake_admin.ps1 -EnableLongPaths         # + registry fix
#   .\szl_bake_admin.ps1 -AddDefenderExclusion    # + AV exclusion (read above)
#   .\szl_bake_admin.ps1 -DiagnoseOnly            # preflight report, no changes
#   .\szl_bake_admin.ps1 -SkipTrain               # corpus + CPU gates only
#   .\szl_bake_admin.ps1 -CudaTag cu128           # override the wheel index
#
# Run it from the repo root and pass -RepoDir explicitly if the repo is the
# current directory; the default assumes you are one level above it.

[CmdletBinding()]
param(
    [string]$RepoDir    = "$PWD\szl-typesafe-triage",
    [string]$RepoUrl    = "https://github.com/szl-holdings/szl-typesafe-triage.git",
    [string]$BaseModel  = "Qwen/Qwen2.5-0.5B-Instruct",
    [string]$AdapterOut = "out\adapter",
    [string]$CudaTag    = "cu130",
    [int]$MinFreeGB     = 25,
    [switch]$EnableLongPaths,
    [switch]$AddDefenderExclusion,
    [switch]$DiagnoseOnly,
    [switch]$SkipTrain,
    [switch]$NoElevate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$script:transcribing = $false

function Stop-TranscriptSafely {
    # Stop-Transcript throws if the host is not transcribing, which buried the
    # real error message on every failure path.
    if (-not $script:transcribing) { return }
    $script:transcribing = $false
    try { Stop-Transcript | Out-Null } catch { }
}

function Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK]    $m" -ForegroundColor Green }
function Info($m) { Write-Host "  [INFO]  $m" -ForegroundColor Gray }
function Warn($m) { Write-Host "  [WARN]  $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "  [STOP]  $m" -ForegroundColor Red; Stop-TranscriptSafely; exit 1 }
function Assert-Exit($what) { if ($LASTEXITCODE -ne 0) { Die "$what exited $LASTEXITCODE" } }

# ---------------------------------------------------------------- elevation
function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin) -and -not $NoElevate) {
    Write-Host "Re-launching elevated..." -ForegroundColor Yellow
    $argList = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-RepoDir", "`"$RepoDir`"", "-BaseModel", "`"$BaseModel`"",
        "-AdapterOut", "`"$AdapterOut`"", "-CudaTag", $CudaTag
    )
    if ($EnableLongPaths)      { $argList += "-EnableLongPaths" }
    if ($AddDefenderExclusion) { $argList += "-AddDefenderExclusion" }
    if ($DiagnoseOnly)         { $argList += "-DiagnoseOnly" }
    if ($SkipTrain)            { $argList += "-SkipTrain" }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
    exit 0
}

if (-not (Test-Admin)) { Warn "running WITHOUT admin (-NoElevate); admin-only steps will be skipped" }
else { Ok "elevated" }

# ---------------------------------------------------------------- transcript
New-Item -ItemType Directory -Force -Path "$PWD\logs" | Out-Null
$logPath = "$PWD\logs\bake-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
try {
    Start-Transcript -Path $logPath -Force | Out-Null
    $script:transcribing = $true
    Info "transcript: $logPath"
} catch {
    Warn "transcript unavailable: $($_.Exception.Message)"
}

# ================================================================ DIAGNOSTICS
Step "System diagnostics"

$os = Get-CimInstance Win32_OperatingSystem
Info "OS        : $($os.Caption) build $($os.BuildNumber)"
Info "PowerShell: $($PSVersionTable.PSVersion)"

$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
Info "CPU       : $($cpu.Name.Trim()) ($($cpu.NumberOfLogicalProcessors) threads)"
Info "RAM       : $([math]::Round($os.TotalVisibleMemorySize/1MB,1)) GB"

$drive = (Get-Item $PWD).PSDrive.Name
$free  = [math]::Round((Get-PSDrive $drive).Free / 1GB, 1)
Info "Disk $drive`:  : $free GB free"
if ($free -lt $MinFreeGB) { Die "need >= $MinFreeGB GB free on $drive`:, found $free GB" }

$gpuName = $null; $vram = $null; $driver = $null
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $gpuName = (& nvidia-smi --query-gpu=name           --format=csv,noheader | Select-Object -First 1)
    $vram    = (& nvidia-smi --query-gpu=memory.total   --format=csv,noheader | Select-Object -First 1)
    $driver  = (& nvidia-smi --query-gpu=driver_version --format=csv,noheader | Select-Object -First 1)
    Info "GPU       : $gpuName"
    Info "VRAM      : $vram"
    Info "Driver    : $driver"
} else {
    Warn "nvidia-smi absent - no NVIDIA GPU detected"
    if (-not $SkipTrain -and -not $DiagnoseOnly) {
        Die "training needs a GPU; re-run with -SkipTrain to do corpus + CPU gates only"
    }
}

foreach ($tool in @("python", "git")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Die "$tool not on PATH" }
}
$pyVer = (& python -c "import sys;print('%d.%d'%sys.version_info[:2])").Trim()
if ([version]$pyVer -lt [version]"3.10") { Die "Python $pyVer found; 3.10+ required (PEP 604 unions)" }
Ok "python $pyVer, git present"

$lpKey = "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem"
$lpNow = (Get-ItemProperty -Path $lpKey -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
Info "LongPathsEnabled: $(if ($null -eq $lpNow) { 'unset' } else { $lpNow })"

if ($DiagnoseOnly) { Ok "-DiagnoseOnly: no changes made"; Stop-TranscriptSafely; exit 0 }

# ================================================================ ADMIN WORK
Step "Administrator operations"

if (Test-Admin) {
    $pol = Get-ExecutionPolicy -Scope LocalMachine
    if ($pol -eq "Restricted") {
        Set-ExecutionPolicy RemoteSigned -Scope LocalMachine -Force
        Ok "execution policy: Restricted -> RemoteSigned"
    } else { Info "execution policy already $pol; unchanged" }

    if ($EnableLongPaths) {
        if ($lpNow -ne 1) {
            Set-ItemProperty -Path $lpKey -Name LongPathsEnabled -Value 1 -Type DWord
            Ok "LongPathsEnabled=1 (reboot may be required for all processes)"
        } else { Info "long paths already enabled" }
    } else {
        Info "long paths NOT changed (pass -EnableLongPaths to enable)"
    }

    if ($AddDefenderExclusion) {
        Warn "adding a Defender exclusion REDUCES scanning coverage for that path"
        try {
            Add-MpPreference -ExclusionPath (Join-Path $RepoDir ".venv") -ErrorAction Stop
            Ok "Defender exclusion added for .venv"
        } catch { Warn "could not add exclusion: $($_.Exception.Message)" }
    } else {
        Info "no Defender exclusion (pass -AddDefenderExclusion if pip is slow)"
    }
} else {
    Warn "not elevated; skipped policy/registry/Defender steps"
}

# ================================================================ SOURCE
Step "Source"

if (Test-Path $RepoDir) {
    Push-Location $RepoDir
    git pull --ff-only; Assert-Exit "git pull"
    Pop-Location
    Ok "pulled"
} else {
    git clone $RepoUrl $RepoDir; Assert-Exit "git clone"
    Ok "cloned"
}

Push-Location $RepoDir
try {
    $head    = (git rev-parse --short HEAD).Trim()
    $subject = (git log -1 --pretty=%s).Trim()
    Ok "HEAD $head - $subject"

    # ============================================================ ENVIRONMENT
    Step "Python environment"

    if (-not (Test-Path ".venv")) { & python -m venv .venv; Assert-Exit "venv create" }
    $vpy = Join-Path $RepoDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $vpy)) { Die "venv python missing: $vpy" }

    & $vpy -m pip install --upgrade pip setuptools wheel --quiet; Assert-Exit "pip bootstrap"
    & $vpy -m pip install -e . --quiet; Assert-Exit "install szl_triage"
    & $vpy -m pip install pytest --quiet; Assert-Exit "install pytest"
    $installed = (& $vpy -c "import szl_triage;print(szl_triage.__version__)").Trim()
    Ok "szl_triage $installed installed"

    # ============================================================ GATE 0
    Step "GATE 0 - test suite must be green"

    & $vpy -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        Die "suite RED at $head. Do not train. A model distilled from a broken engine inherits the break and hides it in weights."
    }
    Ok "suite green"

    # ============================================================ CORPUS
    Step "Corpus"

    & $vpy scripts\build_corpus.py; Assert-Exit "build_corpus.py"

    $corpus = "output\triage_distill_v0.3.0.jsonl"
    if (-not (Test-Path $corpus)) { Die "corpus missing: $corpus" }
    $corpusHash = (Get-FileHash $corpus -Algorithm SHA256).Hash.ToLower()
    $rows = (Get-Content $corpus | Measure-Object -Line).Lines
    Ok "$rows rows, sha256 $($corpusHash.Substring(0,16))..."
    Warn "corpus does NOT yet contain doctrine-disposition cases; the student"
    Warn "will learn a gate one commit out of date."

    # ============================================================ GATE 1
    Step "GATE 1 - oracle smoke test (CPU, ~1s)"

    $oracle = & $vpy scripts\eval_receipts.py --oracle; Assert-Exit "oracle eval"
    $oracle | ForEach-Object { Write-Host "    $_" }

    # Out-String: the left operand MUST be a single string, not an array.
    $oracleText = ($oracle | Out-String)
    if ($oracleText -notmatch "FALSE LABEL ON REFUSAL:\s*0\b") {
        Die "oracle did not report zero false labels. Harness is miswired - do not spend GPU time."
    }
    Ok "harness verified against the engine"

    if ($SkipTrain) { Ok "-SkipTrain set; stopping here"; Stop-TranscriptSafely; exit 0 }

    # ============================================================ ML DEPS
    Step "ML dependencies"

    Warn "train_distill.py has NEVER been executed. Expect a version-specific"
    Warn "SFTConfig / processing_class argument to need fixing on first run."
    Warn "Despite the name it is bf16 LoRA, NOT 4-bit QLoRA - bitsandbytes is"
    Warn "deliberately omitted."

    & $vpy -m pip install --quiet torch --index-url "https://download.pytorch.org/whl/$CudaTag"
    if ($LASTEXITCODE -ne 0) { Die "torch install failed for $CudaTag - try -CudaTag cu128 or cu132" }
    & $vpy -m pip install --quiet transformers datasets accelerate peft trl; Assert-Exit "transformers stack"

    $torchVer = (& $vpy -c "import torch;print(torch.__version__)").Trim()
    $cudaOk   = (& $vpy -c "import torch;print(torch.cuda.is_available())").Trim()
    if ($cudaOk -ne "True") { Die "torch $torchVer present but CUDA unavailable - driver/$CudaTag mismatch" }

    # is_available() is NOT sufficient on Blackwell: it returns True even when
    # the wheel carries no sm_120 kernels, and the failure then surfaces
    # mid-training as "no kernel image is available for execution on the
    # device". Compare the device capability against the compiled arch list.
    # -notcontains is a real boolean over a collection, unlike -notmatch.
    $cap = (& $vpy -c "import torch;print('%d%d' % torch.cuda.get_device_capability())").Trim()
    $archList = ((& $vpy -c "import torch;print(';'.join(torch.cuda.get_arch_list()))").Trim()) -split ';'
    Info "torch $torchVer | device sm_$cap | wheel arch list: $($archList -join ' ')"
    if ($archList -notcontains "sm_$cap") {
        Die "wheel lacks sm_$cap. torch $torchVer was built for [$($archList -join ' ')]. Blackwell needs CUDA 12.8+/PyTorch 2.7+; try -CudaTag cu128 or a newer tag. Training would fail with 'no kernel image is available'."
    }
    Ok "torch $torchVer, sm_$cap present in the wheel"

    # ============================================================ BAKE
    Step "BAKE"

    $t0 = Get-Date
    & $vpy scripts\train_distill.py --base $BaseModel --out $AdapterOut
    Assert-Exit "train_distill.py"
    $mins = [int](((Get-Date) - $t0).TotalMinutes)
    Ok "adapter at $AdapterOut ($mins min)"

    # ============================================================ GATE 2
    Step "GATE 2 - promotion gate"

    $res = & $vpy scripts\eval_receipts.py --adapter $AdapterOut --base $BaseModel
    Assert-Exit "adapter eval"
    $res | ForEach-Object { Write-Host "    $_" }

    # Out-String again: against an array, -match does not populate $Matches at
    # all, so this branch previously ALWAYS fell through to "unparseable" and
    # reported BLOCKED no matter how good the model was.
    $resText = ($res | Out-String)
    $promote = $false
    if ($resText -match "FALSE LABEL ON REFUSAL:\s*(\d+)") {
        $bad = [int]$Matches[1]
        if ($bad -eq 0) { $promote = $true; Ok "false_label_on_refusal = 0 - PROMOTABLE" }
        else {
            Warn "false_label_on_refusal = $bad - BLOCKED"
            Warn "The model labelled inputs the engine refused. It learned to guess,"
            Warn "and it will guess on adversarial inputs too. Do not publish."
        }
    } else { Warn "promotion metric unparseable - treating as BLOCKED" }

    # ============================================================ RECEIPT
    Step "Run receipt"

    $adapterHash = "UNAVAILABLE"
    $af = Join-Path $AdapterOut "adapter_model.safetensors"
    if (Test-Path $af) { $adapterHash = (Get-FileHash $af -Algorithm SHA256).Hash.ToLower() }

    $receipt = [ordered]@{
        schema           = "szl.bake.run-receipt/v1"
        timestamp_utc    = (Get-Date).ToUniversalTime().ToString("o")
        repo_head        = $head
        repo_subject     = $subject
        package_version  = $installed
        base_model       = $BaseModel
        corpus_path      = $corpus
        corpus_rows      = $rows
        corpus_sha256    = $corpusHash
        adapter_sha256   = $adapterHash
        gpu              = if ($gpuName) { $gpuName } else { "UNAVAILABLE" }
        vram             = if ($vram)    { $vram }    else { "UNAVAILABLE" }
        driver           = if ($driver)  { $driver }  else { "UNAVAILABLE" }
        torch            = $torchVer
        cuda_tag         = $CudaTag
        device_arch      = "sm_$cap"
        wheel_arch_list  = ($archList -join " ")
        train_minutes    = $mins
        energy_joules    = $null   # honest null: no RAPL/NVML sampling here
        label_provenance = "ENGINE_DERIVED_v0.3.0"
        promotion        = if ($promote) { "PROMOTABLE" } else { "BLOCKED" }
        signature        = "UNSIGNED_HONEST"
        transcript       = $logPath
        caveats          = @(
            "labels are engine-derived, NOT human-ratified ground truth",
            "paraphrase bypass (docs/redteam.md) is present in the training targets",
            "a 36-config sweep found NO weighting that closes it (docs/calibration.md)",
            "corpus predates the doctrine-disposition gate",
            "no public adversarial benchmark (Garak/PINT) has been run",
            "train_distill.py was unverified prior to this run",
            "run executed ELEVATED; pip package code ran with admin rights"
        )
    }

    New-Item -ItemType Directory -Force -Path "output" | Out-Null
    $rp = "output\bake-receipt.json"
    $receipt | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $rp
    Ok "receipt: $rp"

    Step "Summary"
    Write-Host "  head        $head"
    Write-Host "  corpus      $rows rows"
    Write-Host "  device      sm_$cap | torch $torchVer ($CudaTag)"
    Write-Host "  promotion   $(if ($promote) { 'PROMOTABLE' } else { 'BLOCKED' })"
    Write-Host "  signature   UNSIGNED_HONEST"
    Write-Host "`n  Next: submit output\bake-receipt.json to szl-gpu-bridge so the" -ForegroundColor Cyan
    Write-Host "  bake is signed rather than merely recorded." -ForegroundColor Cyan
}
finally {
    Pop-Location
    Stop-TranscriptSafely
}
