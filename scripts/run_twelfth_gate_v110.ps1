<#
.SYNOPSIS
  SZL twelfth gate v1.1.0 runner for Windows PowerShell 5.1. Restartable and fail-closed.

.DESCRIPTION
  Trains the five study seeds with scripts/train_lora.py plus the 50 owner-ratified refusal rows
  (the only declared change), evaluates the sha-verified frozen held split with
  scripts/five_seed_eval.py, scores the 42-row challenge with challenge_eval through the study
  inference boundary, and computes the verdict with scripts/twelfth_gate_v110.py.

  EARNED      -> local measured receipt only; #44 stays on HOLD pending separate review.
  NOT_EARNED  -> local measured failure receipt only; #44 stays on HOLD.
  INCOMPLETE  -> local incomplete receipt only.

  Finished seeds, held evaluations and challenge receipts are reused on rerun.
  A release condition is not promotion: every receipt keeps promotion_status NOT_PROMOTABLE.
#>
param(
    [string]$Python = "C:\Users\steph\szl-typesafe-triage\.venv\Scripts\python.exe",
    [string]$StudyRepo = "C:\Users\steph\szl-typesafe-triage",
    [switch]$NoPublish,
    [switch]$PreflightOnly,
    [switch]$SkipGpu
)

$ErrorActionPreference = "Continue"
Set-StrictMode -Version Latest

$Repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Repo
$Work = Join-Path $Repo "out\retrain-v110"
$Logs = Join-Path $Work "logs"
$Runner = "scripts\twelfth_gate_v110.py"
$Seeds = @(11, 23, 37, 53, 71)
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$MAX_WALLCLOCK_MINUTES = 180
$THERMAL_GUARD_CELSIUS = 78
$RunStarted = Get-Date
New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Say([string]$Text, [string]$Color = "Cyan") {
    Write-Host ((Get-Date -Format "HH:mm") + "  " + $Text) -ForegroundColor $Color
}

function Stop-Run([string]$Why) {
    Say ("STOPPED: " + $Why) "Red"
    Say "Nothing further was published. Fix the cause and rerun the same command; finished steps are reused." "Yellow"
    exit 2
}

function Show-Tail([string]$Log, [int]$Lines = 8) {
    if (Test-Path -LiteralPath $Log) {
        Get-Content -LiteralPath $Log -Tail $Lines | ForEach-Object {
            Write-Host ("    | " + ((([string]$_) -split "`r")[-1]))
        }
    }
}

function Invoke-Py([string]$Title, [string]$ArgLine, [string]$Log) {
    # python runs under cmd.exe with output redirected to a log, so native stderr (unsloth, tqdm)
    # can never become a PowerShell error record. A heartbeat shows the latest log line.
    if (Test-Path -LiteralPath $Log) { Remove-Item -LiteralPath $Log -Force }
    $cmdLine = '/c ""' + $Python + '" ' + $ArgLine + ' > "' + $Log + '" 2>&1"'
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList $cmdLine -WorkingDirectory $Repo -NoNewWindow -PassThru
    $null = $proc.Handle
    $shown = ""
    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 15
        $elapsed = ((Get-Date) - $RunStarted).TotalMinutes
        if ($elapsed -ge $MAX_WALLCLOCK_MINUTES) {
            Stop-ProcessTree $proc.Id
            Write-Host ("        [" + $Title + "] wallclock guard exceeded") -ForegroundColor Red
            return 97
        }
        if (-not ($PreflightOnly -and $SkipGpu)) {
            $temperature = Get-GpuTemperature
            if ($null -eq $temperature) {
                Stop-ProcessTree $proc.Id
                Write-Host ("        [" + $Title + "] GPU temperature unavailable") -ForegroundColor Red
                return 96
            }
            if ($temperature -ge $THERMAL_GUARD_CELSIUS) {
                Stop-ProcessTree $proc.Id
                Write-Host ("        [" + $Title + "] thermal guard reached " + $temperature + " C") -ForegroundColor Red
                return 98
            }
        }
        if (Test-Path -LiteralPath $Log) {
            $tail = Get-Content -LiteralPath $Log -Tail 1 -ErrorAction SilentlyContinue
            if ($tail) {
                $seg = (([string]$tail) -split "`r" | Where-Object { $_.Trim().Length -gt 0 } | Select-Object -Last 1)
                if ($seg) {
                    $seg = ($seg -replace "\s+", " ").Trim()
                    if ($seg.Length -gt 110) { $seg = $seg.Substring(0, 110) }
                    if ($seg -ne $shown) {
                        $shown = $seg
                        Write-Host ("        [" + $Title + "] " + $seg) -ForegroundColor DarkGray
                    }
                }
            }
        }
    }
    $proc.WaitForExit()
    $exitCode = $proc.ExitCode
    if ($null -eq $exitCode) { return 99 }
    return [int]$exitCode
}

function Stop-ProcessTree([int]$ProcessId) {
    & taskkill.exe /PID $ProcessId /T /F 2>&1 | Out-Null
}

function Get-GpuTemperature {
    $raw = (& nvidia-smi.exe --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0) { return $null }
    $value = 0
    if (-not [int]::TryParse(([string]$raw).Trim(), [ref]$value)) { return $null }
    return $value
}

function Assert-ProductionHost {
    if (-not (Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue)) {
        Stop-Run "nvidia-smi is required for the production thermal guard"
    }
    $temperature = Get-GpuTemperature
    if ($null -eq $temperature) { Stop-Run "GPU temperature is unavailable" }
    if ($temperature -ge $THERMAL_GUARD_CELSIUS) {
        Stop-Run ("GPU is already at or above the " + $THERMAL_GUARD_CELSIUS + " C guard")
    }
}

Say "=== SZL twelfth gate v1.1.0 | study trainer + 50 ratified rows | frozen held | 42-row challenge ==="
if (-not $NoPublish) { Stop-Run "this research runner is local-only and requires -NoPublish" }
if ($SkipGpu -and -not $PreflightOnly) { Stop-Run "-SkipGpu is allowed only with -PreflightOnly" }
if (-not (Test-Path -LiteralPath $Python)) { Stop-Run ("study venv python not found: " + $Python) }
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$env:HF_HUB_DISABLE_TELEMETRY = "1"
$env:SZL_ALLOW_HUB_PUSH = "0"
$env:TOKENIZERS_PARALLELISM = "false"
Say ("repo " + $Repo + " @ " + (git rev-parse --short HEAD 2>$null) + " | python " + $Python) "DarkGray"

# The study corpus is untracked; it only feeds the trainer's split preamble. Preflight records
# whether its bytes match the frozen manifest; training rows always come from the frozen split.
$corpusSrc = Join-Path $StudyRepo "output\triage_distill_v0.5.0.jsonl"
$corpusDst = Join-Path $Repo "output\triage_distill_v0.5.0.jsonl"
if ((-not (Test-Path -LiteralPath $corpusDst)) -and (Test-Path -LiteralPath $corpusSrc)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Repo "output") | Out-Null
    Copy-Item -LiteralPath $corpusSrc -Destination $corpusDst -Force
}

# ---------------------------------------------------------------- 1) preflight
Say "[1/6] preflight: frozen split, ratified corpus, challenge, trainer anchors, GPU"
$log = Join-Path $Logs "preflight.log"
$preflightArgs = $Runner + " preflight"
if ($SkipGpu) { $preflightArgs += " --skip-gpu" }
$code = Invoke-Py "preflight" $preflightArgs $log
Show-Tail $log 2
if ($code -ne 0) { Stop-Run "preflight refused - see out\retrain-v110\logs\preflight.log" }
if ($PreflightOnly) {
    if (-not $SkipGpu) { Assert-ProductionHost }
    Say "PreflightOnly complete. No model was loaded or trained." "Green"
    exit 0
}
Assert-ProductionHost

# ---------------------------------------------------------------- 2) inference smoke
Say "[2/6] smoke: two challenge rows through the study inference boundary, before any training"
$smokeOk = Join-Path $Work "smoke.ok"
if (-not (Test-Path -LiteralPath $smokeOk)) {
    $smokeAdapter = "unsloth/Qwen3.5-0.8B"
    foreach ($candidate in @((Join-Path $StudyRepo "out\train\adapter"), (Join-Path $StudyRepo "out\train\study\seed-023\adapter"))) {
        if (Test-Path -LiteralPath (Join-Path $candidate "adapter_model.safetensors")) { $smokeAdapter = $candidate; break }
    }
    $log = Join-Path $Logs "smoke.log"
    $code = Invoke-Py "smoke" ($Runner + ' smoke --adapter "' + $smokeAdapter + '" --rows 2') $log
    Show-Tail $log 3
    if ($code -ne 0) { Show-Tail $log 15; Stop-Run "inference smoke failed - nothing has been trained; see out\retrain-v110\logs\smoke.log" }
    Set-Content -LiteralPath $smokeOk -Value $smokeAdapter -Encoding ASCII
}
else { Say "      smoke already passed on this host" "DarkGray" }

$log = Join-Path $Logs "held-root.log"
$code = Invoke-Py "held-root" ($Runner + " held-root") $log
if ($code -ne 0) { Show-Tail $log; Stop-Run "could not prepare the frozen held root" }

# ---------------------------------------------------------------- 3) five seeds
Say "[3/6] five seeds: train ~10 min, held eval ~5 min, challenge ~2 min each (about 80 min total)"
foreach ($seed in $Seeds) {
    $tag = "seed-{0:d3}" -f $seed
    $runDir = Join-Path $Work $tag
    $checkLog = Join-Path $Logs ("check-train-" + $tag + ".log")
    $code = Invoke-Py ("check " + $tag) ($Runner + " check-train --seed " + $seed) $checkLog
    if ($code -ne 0) {
        if (Test-Path -LiteralPath $runDir) {
            $aside = $tag + ".partial-" + $Stamp
            Rename-Item -LiteralPath $runDir -NewName $aside
            Say ("      moved an incomplete " + $tag + " aside as " + $aside) "DarkYellow"
        }
        $patchLog = Join-Path $Logs ("make-trainer-" + $tag + ".log")
        $code = Invoke-Py ("patch " + $tag) ($Runner + " make-trainer --seed " + $seed) $patchLog
        if ($code -ne 0) { Show-Tail $patchLog; Stop-Run ("trainer patch refused for " + $tag) }
        Say ("      training " + $tag + " (study trainer, 565 rows)") "Yellow"
        $trainLog = Join-Path $Logs ("train-" + $tag + ".log")
        $code = Invoke-Py ("train " + $tag) ("out\retrain-v110\control\train_" + $tag + ".py") $trainLog
        $code = Invoke-Py ("check " + $tag) ($Runner + " check-train --seed " + $seed) $checkLog
        if ($code -ne 0) { Show-Tail $trainLog 15; Show-Tail $checkLog 2; Stop-Run ($tag + " training did not produce a valid MEASURED receipt") }
    }
    Show-Tail $checkLog 1

    $metrics = Join-Path $Work ("study\evaluation\metrics-" + $tag + ".json")
    if (-not (Test-Path -LiteralPath $metrics)) {
        Say ("      held eval " + $tag + " (113 frozen rows)") "Yellow"
        $heldLog = Join-Path $Logs ("held-" + $tag + ".log")
        $studyRoot = Join-Path $Work "study"
        $adapterDir = Join-Path $runDir "adapter"
        $code = Invoke-Py ("held " + $tag) ('scripts\five_seed_eval.py --study-root "' + $studyRoot + '" --name ' + $tag + ' --adapter "' + $adapterDir + '"') $heldLog
        if (($code -ne 0) -or (-not (Test-Path -LiteralPath $metrics))) { Show-Tail $heldLog 15; Stop-Run ("held evaluation failed for " + $tag) }
    }

    Say ("      challenge " + $tag + " (42 rows: 30 paraphrase, 12 steering)") "Yellow"
    $challengeLog = Join-Path $Logs ("challenge-" + $tag + ".log")
    $code = Invoke-Py ("challenge " + $tag) ($Runner + " challenge --seed " + $seed) $challengeLog
    Show-Tail $challengeLog 1
    if ($code -ne 0) { Show-Tail $challengeLog 15; Stop-Run ("challenge failed for " + $tag + " (the FAILED receipt is kept as evidence)") }
}

# ---------------------------------------------------------------- 4) verdict
Say "[4/6] verdict"
$verdictLog = Join-Path $Logs "verdict.log"
$verdictCode = Invoke-Py "verdict" ($Runner + " verdict") $verdictLog
Get-Content -LiteralPath $verdictLog | ForEach-Object { Write-Host ("    " + $_) }
$summaryPath = Join-Path $Work "VERDICT_SUMMARY.txt"
if (($verdictCode -eq 3) -or (-not (Test-Path -LiteralPath $summaryPath))) { Stop-Run "verdict INCOMPLETE - an evaluation is missing" }
if (($verdictCode -ne 0) -and ($verdictCode -ne 1)) { Stop-Run ("verdict step failed with exit code " + $verdictCode) }
$summary = (Get-Content -LiteralPath $summaryPath -Raw).Trim()
Say ("Local-only run complete. " + $summary) "Yellow"
exit $verdictCode
