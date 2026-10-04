<#
.SYNOPSIS
  SZL twelfth gate v1.1.0 runner for Windows PowerShell 5.1. Restartable and fail-closed.

.DESCRIPTION
  Trains the five study seeds with scripts/train_lora.py plus the 50 owner-ratified refusal rows
  (the only declared change), evaluates the sha-verified frozen held split with
  scripts/five_seed_eval.py, scores the 42-row challenge with challenge_eval through the study
  inference boundary, and computes the verdict with scripts/twelfth_gate_v110.py.

  EARNED      -> unHOLD #44, evidence PR, tag, GitHub release (Zenodo mints the DOI), Hub adapters.
  NOT_EARNED  -> measured failure evidence PR only; #44 stays on HOLD.
  INCOMPLETE  -> nothing is published.

  Finished seeds, held evaluations and challenge receipts are reused on rerun.
  A release condition is not promotion: every receipt keeps promotion_status NOT_PROMOTABLE.
#>
param(
    [string]$Python = "C:\Users\steph\szl-typesafe-triage\.venv\Scripts\python.exe",
    [string]$StudyRepo = "C:\Users\steph\szl-typesafe-triage",
    [switch]$NoPublish
)

$ErrorActionPreference = "Continue"
Set-StrictMode -Version Latest

$Repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Repo
$Org = "szl-holdings/szl-typesafe-triage"
$Work = Join-Path $Repo "out\retrain-v110"
$Logs = Join-Path $Work "logs"
$Runner = "scripts\twelfth_gate_v110.py"
$Seeds = @(11, 23, 37, 53, 71)
$ReleaseTag = "typesafe-triage-v1.1.0"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
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

function Assert-Native([string]$What) {
    if ($LASTEXITCODE -ne 0) { Stop-Run ("git/gh step failed: " + $What + " (exit " + $LASTEXITCODE + ")") }
}

function Write-Utf8([string]$Path, [string[]]$Lines) {
    [System.IO.File]::WriteAllText($Path, (($Lines -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))
}

Say "=== SZL twelfth gate v1.1.0 | study trainer + 50 ratified rows | frozen held | 42-row challenge ==="
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
$code = Invoke-Py "preflight" ($Runner + " preflight") $log
Show-Tail $log 2
if ($code -ne 0) { Stop-Run "preflight refused - see out\retrain-v110\logs\preflight.log" }

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
if ($NoPublish) { Say ("NoPublish set. " + $summary) "Yellow"; exit $verdictCode }

git fetch origin --prune 2>&1 | Out-Null
Assert-Native "git fetch"

# ---------------------------------------------------------------- 5) publish
if ($verdictCode -eq 0) {
    gh release view $ReleaseTag --repo $Org 2>&1 | Out-Null
    $releaseExists = ($LASTEXITCODE -eq 0)
    if ($releaseExists) {
        Say ("[5/6] release " + $ReleaseTag + " already exists - skipping straight to the Hub step") "DarkGray"
    }
    else {
        Say "[5/6] EARNED on all five seeds - unHOLD #44, evidence PR, tag, release" "Green"
        $state44 = (((gh pr view 44 --repo $Org --json state --jq ".state" 2>$null) -join "") -replace "\s", "")
        if ($state44 -eq "OPEN") {
            gh pr merge 44 --repo $Org --squash --admin 2>&1 | Out-Null
            Assert-Native "merge #44"
            git fetch origin --prune 2>&1 | Out-Null
        }
        $branch = "release/v1.1.0-evidence-" + $Stamp
        git checkout -B $branch origin/main 2>&1 | Out-Null
        Assert-Native "branch from origin/main"
        if (-not (Test-Path -LiteralPath "docs\release\release-notes-v1.1.0.md")) { Stop-Run "the #44 release notes are not on main" }
        $log = Join-Path $Logs "fill-notes.log"
        $code = Invoke-Py "notes" ($Runner + " fill-notes") $log
        if ($code -ne 0) { Show-Tail $log; Stop-Run "release notes fill refused" }
        $log = Join-Path $Logs "bundle.log"
        $code = Invoke-Py "bundle" ($Runner + " bundle --dest docs/release/v1.1.0-evidence") $log
        if ($code -ne 0) { Show-Tail $log; Stop-Run "evidence bundle failed" }
        git add docs/release 2>&1 | Out-Null
        git commit -q -m ("release(v1.1.0): " + $summary) 2>&1 | Out-Null
        Assert-Native "commit evidence"
        git push -u origin $branch 2>&1 | Out-Null
        Assert-Native "push evidence branch"
        $bodyPath = Join-Path $Work "pr-body-release.md"
        Write-Utf8 $bodyPath @(
            $summary,
            "",
            "Measured on the owner's GPU with the study's own tools: scripts/train_lora.py (patched per seed as in bootstrap-five-seed-study.ps1, plus the declared append of 50 ratified refusal rows), scripts/five_seed_eval.py on the sha-verified frozen held split, and challenge_eval scoring through the study inference boundary (user-only, non-thinking, no system message).",
            "",
            "Release condition met on every seed: 12/12 typed refusals with 0 false labels and 0 malformed on the 42-row challenge, plus held non-regression. ECE and the stratified accuracy audit are UNAVAILABLE in this run and are labeled so. Promotion stays NOT_PROMOTABLE.",
            "",
            "Evidence: docs/release/v1.1.0-evidence/ (receipts, metrics, predictions, logs, patched trainers, SHA256SUMS). No model weights."
        )
        $prUrl = ((gh pr create --repo $Org --base main --head $branch --title "release(v1.1.0): twelfth gate EARNED on all five seeds - measured receipts" --body-file $bodyPath 2>$null) -join "`n")
        if (-not ($prUrl -match "/pull/(\d+)")) { Stop-Run "the evidence PR was not created" }
        $prNumber = $Matches[1]
        gh pr merge $prNumber --repo $Org --squash --admin 2>&1 | Out-Null
        Assert-Native ("merge evidence PR #" + $prNumber)
        git fetch origin --prune 2>&1 | Out-Null
        git checkout -B main origin/main 2>&1 | Out-Null
        Assert-Native "checkout main"
        $remoteTag = ((git ls-remote --tags origin ("refs/tags/" + $ReleaseTag) 2>$null) -join "")
        if (-not $remoteTag) {
            git tag -a $ReleaseTag -m ("Governed Type-Safe Triage v1.1.0 - " + $summary) 2>&1 | Out-Null
            Assert-Native "create tag"
            git push origin $ReleaseTag 2>&1 | Out-Null
            Assert-Native "push tag"
        }
        gh release create $ReleaseTag --repo $Org --title "Governed Type-Safe Triage v1.1.0 - twelfth gate earned on five seeds" --notes-file "docs\release\release-notes-v1.1.0.md" 2>&1 | Out-Null
        Assert-Native "gh release create"
        Say ("      evidence PR " + $prUrl + " merged") "Green"
        Say ("      release https://github.com/" + $Org + "/releases/tag/" + $ReleaseTag) "Green"
        Say "      Zenodo mints the versioned DOI from this release (concept 10.5281/zenodo.20567256)" "Green"
    }

    Say "[6/6] Hub: five adapters to SZLHOLDINGS/szl-triage-retrain/adapters-v1.1.0 (PUBLIC_EXPERIMENTAL_ARTIFACT, NOT_PROMOTABLE)"
    $hubMarker = Join-Path $Work "hub.ok"
    if (Test-Path -LiteralPath $hubMarker) { Say "      adapters already published" "DarkGray" }
    else {
        $log = Join-Path $Logs "hub.log"
        $code = Invoke-Py "hub" ($Runner + " publish-adapters") $log
        Show-Tail $log 7
        if ($code -eq 0) { Set-Content -LiteralPath $hubMarker -Value $summary -Encoding ASCII }
        else { Say "      Hub upload did not complete (local HF login?). The release and DOI stand; run 'huggingface-cli login' and rerun this command to finish only this step." "Yellow" }
    }
    Say ("DONE. " + $summary) "Green"
    exit 0
}

Say "[5/6] NOT EARNED - publishing the measured failure evidence; #44 stays on HOLD" "Yellow"
$branch = "evidence/twelfth-gate-v110-" + $Stamp
git checkout -B $branch origin/main 2>&1 | Out-Null
Assert-Native "branch from origin/main"
$dest = "evidence/twelfth-gate-v110/" + $Stamp
$log = Join-Path $Logs "bundle.log"
$code = Invoke-Py "bundle" ($Runner + " bundle --dest " + $dest) $log
if ($code -ne 0) { Show-Tail $log; Stop-Run "failure-evidence bundle failed" }
git add evidence/twelfth-gate-v110 2>&1 | Out-Null
git commit -q -m ("evidence: twelfth-gate v1.1.0 retrain - " + $summary + " (NOT_PROMOTABLE stands)") 2>&1 | Out-Null
Assert-Native "commit failure evidence"
git push -u origin $branch 2>&1 | Out-Null
Assert-Native "push failure evidence"
$bodyPath = Join-Path $Work "pr-body-failure.md"
Write-Utf8 $bodyPath @(
    $summary,
    "",
    "Measured with the study's own tools on all five retrained seeds. At least one seed missed the release condition (12/12 typed refusals with 0 false labels on the 42-row challenge plus held non-regression). Per-seed rows: TWELFTH_GATE_VERDICT.json in this bundle.",
    "",
    "The v1.1.0 release stays on HOLD (#44). Publication of failure evidence is not promotion; NOT_PROMOTABLE stands."
)
$prUrl = ((gh pr create --repo $Org --base main --head $branch --title ("evidence: twelfth-gate v1.1.0 retrain measured - " + $summary) --body-file $bodyPath 2>$null) -join "`n")
if ($prUrl -match "/pull/(\d+)") {
    gh pr merge $Matches[1] --repo $Org --squash --admin 2>&1 | Out-Null
    gh pr comment 44 --repo $Org --body ("Twelfth-gate retrain measured: " + $summary + ". HOLD stays. Evidence: " + $prUrl) 2>&1 | Out-Null
    Say ("      measured failure evidence: " + $prUrl) "Yellow"
}
else { Say "      evidence branch pushed but the PR was not created; open it from the branch on GitHub" "Yellow" }
Say ("DONE. " + $summary) "Yellow"
exit 1
