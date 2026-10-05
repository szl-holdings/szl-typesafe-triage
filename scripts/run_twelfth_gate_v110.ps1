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
    [switch]$SkipGpu,
    [int]$GpuIndex = 0
)

$ErrorActionPreference = "Continue"
Set-StrictMode -Version Latest

$Repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Repo
$Work = Join-Path $Repo "out\retrain-v110"
$Logs = Join-Path $Work "logs"
$Runner = "scripts\twelfth_gate_v110.py"
$Supervisor = "scripts\study_process_guard.py"
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

function Invoke-Py([string]$Title, [string[]]$PyArgs, [string]$Log) {
    # A model-free supervisor verifies selected-GPU telemetry before launch and
    # during execution, applies the remaining global wall-clock budget, and
    # proves descendant-tree termination after a guard trip.
    if (Test-Path -LiteralPath $Log) { Remove-Item -LiteralPath $Log -Force }
    $elapsedSeconds = [int](((Get-Date) - $RunStarted).TotalSeconds)
    $remainingSeconds = ($MAX_WALLCLOCK_MINUTES * 60) - $elapsedSeconds
    $guardArgs = @(
        $Supervisor, "--python", $Python, "--log", $Log,
        "--max-seconds", ([string]$remainingSeconds),
        "--thermal-celsius", ([string]$THERMAL_GUARD_CELSIUS),
        "--gpu-index", ([string]$GpuIndex)
    )
    if ($SkipGpu) { $guardArgs += "--skip-gpu" }
    $guardArgs += "--"
    $guardArgs += $PyArgs
    & $Python @guardArgs
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { return 99 }
    if ($exitCode -ge 96) {
        Write-Host ("        [" + $Title + "] process guard refused with exit " + $exitCode) -ForegroundColor Red
    }
    return [int]$exitCode
}

Say "=== SZL twelfth gate v1.1.0 | study trainer + 50 ratified rows | frozen held | 42-row challenge ==="
if (-not $NoPublish) { Stop-Run "this research runner is local-only and requires -NoPublish" }
if ($SkipGpu -and -not $PreflightOnly) { Stop-Run "-SkipGpu is allowed only with -PreflightOnly" }
if ($GpuIndex -lt 0) { Stop-Run "GpuIndex must name a nonnegative physical device index" }
if (-not (Test-Path -LiteralPath $Python)) { Stop-Run ("study venv python not found: " + $Python) }
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$env:HF_HUB_DISABLE_TELEMETRY = "1"
$env:SZL_ALLOW_HUB_PUSH = "0"
$env:TOKENIZERS_PARALLELISM = "false"
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:CUDA_VISIBLE_DEVICES = [string]$GpuIndex
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
$preflightArgs = @($Runner, "preflight")
if ($SkipGpu) { $preflightArgs += "--skip-gpu" }
$code = Invoke-Py "preflight" $preflightArgs $log
Show-Tail $log 2
if ($code -ne 0) { Stop-Run "preflight refused - see out\retrain-v110\logs\preflight.log" }
if ($PreflightOnly) {
    Say "PreflightOnly complete. No model was loaded or trained." "Green"
    exit 0
}

# ---------------------------------------------------------------- 2) inference smoke
Say "[2/6] smoke: two challenge rows through the study inference boundary, before any training"
$smokeAdapter = "Qwen/Qwen3.5-0.8B"
$log = Join-Path $Logs "smoke.log"
$code = Invoke-Py "smoke" @($Runner, "smoke", "--adapter", $smokeAdapter, "--rows", "2") $log
Show-Tail $log 3
if ($code -ne 0) { Show-Tail $log 15; Stop-Run "inference smoke failed - nothing has been trained; see out\retrain-v110\logs\smoke.log" }

$log = Join-Path $Logs "held-root.log"
$code = Invoke-Py "held-root" @($Runner, "held-root") $log
if ($code -ne 0) { Show-Tail $log; Stop-Run "could not prepare the frozen held root" }

# ---------------------------------------------------------------- 3) five seeds
Say "[3/6] five seeds: train ~10 min, held eval ~5 min, challenge ~2 min each (about 80 min total)"
foreach ($seed in $Seeds) {
    $tag = "seed-{0:d3}" -f $seed
    $runDir = Join-Path $Work $tag
    $checkLog = Join-Path $Logs ("check-train-" + $tag + ".log")
    $code = Invoke-Py ("check " + $tag) @($Runner, "check-train", "--seed", [string]$seed) $checkLog
    if ($code -ne 0) {
        if (Test-Path -LiteralPath $runDir) {
            $aside = $tag + ".partial-" + $Stamp
            Rename-Item -LiteralPath $runDir -NewName $aside
            Say ("      moved an incomplete " + $tag + " aside as " + $aside) "DarkYellow"
        }
        $patchLog = Join-Path $Logs ("make-trainer-" + $tag + ".log")
        $code = Invoke-Py ("patch " + $tag) @($Runner, "make-trainer", "--seed", [string]$seed) $patchLog
        if ($code -ne 0) { Show-Tail $patchLog; Stop-Run ("trainer patch refused for " + $tag) }
        Say ("      training " + $tag + " (study trainer, 565 rows)") "Yellow"
        $trainLog = Join-Path $Logs ("train-" + $tag + ".log")
        $code = Invoke-Py ("train " + $tag) @(("out\retrain-v110\control\train_" + $tag + ".py")) $trainLog
        if ($code -ne 0) { Show-Tail $trainLog 15; Stop-Run ($tag + " training process failed") }
        $code = Invoke-Py ("check " + $tag) @($Runner, "check-train", "--seed", [string]$seed) $checkLog
        if ($code -ne 0) { Show-Tail $trainLog 15; Show-Tail $checkLog 2; Stop-Run ($tag + " training did not produce a valid MEASURED receipt") }
    }
    Show-Tail $checkLog 1

    $metrics = Join-Path $Work ("study\evaluation\metrics-" + $tag + ".json")
    $heldCheckLog = Join-Path $Logs ("check-held-" + $tag + ".log")
    $code = Invoke-Py ("check held " + $tag) @($Runner, "check-held", "--seed", [string]$seed) $heldCheckLog
    if ($code -ne 0) {
        foreach ($name in @(("metrics-" + $tag + ".json"), ("predictions-" + $tag + ".jsonl"), ("failures-" + $tag + ".jsonl"))) {
            $stale = Join-Path $Work ("study\evaluation\" + $name)
            if (Test-Path -LiteralPath $stale) { Rename-Item -LiteralPath $stale -NewName ($name + ".stale-" + $Stamp) }
        }
        Say ("      held eval " + $tag + " (113 frozen rows)") "Yellow"
        $heldLog = Join-Path $Logs ("held-" + $tag + ".log")
        $studyRoot = Join-Path $Work "study"
        $adapterDir = Join-Path $runDir "adapter"
        $code = Invoke-Py ("held " + $tag) @("scripts\five_seed_eval.py", "--study-root", $studyRoot, "--name", $tag, "--adapter", $adapterDir) $heldLog
        if (($code -ne 0) -or (-not (Test-Path -LiteralPath $metrics))) { Show-Tail $heldLog 15; Stop-Run ("held evaluation failed for " + $tag) }
        $code = Invoke-Py ("check held " + $tag) @($Runner, "check-held", "--seed", [string]$seed) $heldCheckLog
        if ($code -ne 0) { Show-Tail $heldCheckLog 4; Stop-Run ("held receipt binding failed for " + $tag) }
    }
    Show-Tail $heldCheckLog 1

    Say ("      challenge " + $tag + " (42 rows: 30 paraphrase, 12 steering)") "Yellow"
    $challengeLog = Join-Path $Logs ("challenge-" + $tag + ".log")
    $code = Invoke-Py ("challenge " + $tag) @($Runner, "challenge", "--seed", [string]$seed) $challengeLog
    Show-Tail $challengeLog 1
    if ($code -ne 0) { Show-Tail $challengeLog 15; Stop-Run ("challenge failed for " + $tag + " (the FAILED receipt is kept as evidence)") }
    $challengeCheckLog = Join-Path $Logs ("check-challenge-" + $tag + ".log")
    $code = Invoke-Py ("check challenge " + $tag) @($Runner, "check-challenge", "--seed", [string]$seed) $challengeCheckLog
    if ($code -ne 0) { Show-Tail $challengeCheckLog 4; Stop-Run ("challenge receipt binding failed for " + $tag) }
}

# ---------------------------------------------------------------- 4) verdict
Say "[4/6] verdict"
$verdictLog = Join-Path $Logs "verdict.log"
$verdictCode = Invoke-Py "verdict" @($Runner, "verdict") $verdictLog
Get-Content -LiteralPath $verdictLog | ForEach-Object { Write-Host ("    " + $_) }
$summaryPath = Join-Path $Work "VERDICT_SUMMARY.txt"
if (($verdictCode -eq 3) -or (-not (Test-Path -LiteralPath $summaryPath))) { Stop-Run "verdict INCOMPLETE - an evaluation is missing" }
if (($verdictCode -ne 0) -and ($verdictCode -ne 1)) { Stop-Run ("verdict step failed with exit code " + $verdictCode) }
$summary = (Get-Content -LiteralPath $summaryPath -Raw).Trim()
Say ("Local-only run complete. " + $summary) "Yellow"
exit $verdictCode
