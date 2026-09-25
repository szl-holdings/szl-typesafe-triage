param(
    [string]$Repo = "C:\Users\steph\szl-typesafe-triage"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location $Repo

$Python = (Resolve-Path ".venv\Scripts\python.exe").Path
$Study = Join-Path $Repo "out\train\study"
$Control = Join-Path $Study "control"
$Evidence = Join-Path $Repo "evidence\five-seed-study"
$Trainer = Join-Path $Repo "scripts\train_lora.py"
$Evaluator = Join-Path $Repo "scripts\five_seed_eval.py"
$Seeds = @(23, 37, 53, 71)

New-Item -ItemType Directory -Force $Study | Out-Null
New-Item -ItemType Directory -Force $Control | Out-Null
New-Item -ItemType Directory -Force $Evidence | Out-Null

function Refuse([string]$Message) {
    throw "REFUSE: $Message"
}

function Invoke-Python {
    param(
        [string[]]$Arguments,
        [string]$LogPath
    )

    & $Python @Arguments 2>&1 | Tee-Object -FilePath $LogPath
    $code = $LASTEXITCODE

    if ($code -ne 0) {
        Refuse "Python exited with code $code. Read $LogPath"
    }
}

function Test-CorpusHash {
    $manifestPath = Join-Path $Study "frozen\experiment_manifest.json"

    if (-not (Test-Path $manifestPath)) {
        Refuse "frozen experiment manifest is absent"
    }

    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    $corpusPath = Join-Path $Repo $manifest.corpus

    if (-not (Test-Path $corpusPath)) {
        Refuse "frozen corpus is absent: $corpusPath"
    }

    $actual = (Get-FileHash $corpusPath -Algorithm SHA256).Hash.ToLowerInvariant()

    if ($actual -ne $manifest.corpus_sha256.ToLowerInvariant()) {
        Refuse "corpus changed after the split was frozen"
    }
}

Write-Host "=== FREEZE FAMILY SPLIT ===" -ForegroundColor Cyan

Invoke-Python `
    -Arguments @(
        $Evaluator,
        "--study-root", $Study,
        "--freeze"
    ) `
    -LogPath (Join-Path $Study "freeze.log")

Test-CorpusHash

Write-Host "=== EVALUATE UNTOUCHED BASE MODEL ===" -ForegroundColor Cyan

$baseMetrics = Join-Path $Study "evaluation\metrics-base.json"
if (-not (Test-Path $baseMetrics)) {
    Invoke-Python `
        -Arguments @(
            $Evaluator,
            "--study-root", $Study,
            "--name", "base"
        ) `
        -LogPath (Join-Path $Study "evaluation-base.log")
}
else {
    Write-Host "Base evaluation already exists; preserving it." -ForegroundColor Yellow
}

Write-Host "=== EVALUATE IMMUTABLE RUN 1 / SEED 11 ===" -ForegroundColor Cyan

$run1Adapter = Join-Path $Repo "out\train\adapter"
$run1Metrics = Join-Path $Study "evaluation\metrics-seed-011.json"

if (-not (Test-Path $run1Metrics)) {
    Invoke-Python `
        -Arguments @(
            $Evaluator,
            "--study-root", $Study,
            "--name", "seed-011",
            "--adapter", $run1Adapter
        ) `
        -LogPath (Join-Path $Study "evaluation-seed-011.log")
}
else {
    Write-Host "Seed 11 evaluation already exists; preserving it." -ForegroundColor Yellow
}

$originalTrainer = [IO.File]::ReadAllText($Trainer).Replace("`r`n", "`n")

if (-not $originalTrainer.Contains('OUT = Path("out/train"); OUT.mkdir(parents=True, exist_ok=True)')) {
    Refuse "trainer OUT assignment no longer matches the tagged run"
}
if (-not $originalTrainer.Contains("random_state=11")) {
    Refuse "trainer random_state marker is absent"
}
if (-not $originalTrainer.Contains("seed=11")) {
    Refuse "trainer seed marker is absent"
}
if (-not $originalTrainer.Contains('"seed": 11')) {
    Refuse "trainer receipt seed marker is absent"
}

foreach ($seed in $Seeds) {
    Test-CorpusHash

    $name = "seed-{0:d3}" -f $seed
    $relativeOutput = "out/train/study/$name"
    $runDirectory = Join-Path $Repo $relativeOutput
    $receiptPath = Join-Path $runDirectory "training_receipt.json"
    $adapterPath = Join-Path $runDirectory "adapter"
    $adapterFile = Join-Path $adapterPath "adapter_model.safetensors"
    $metricsPath = Join-Path $Study "evaluation\metrics-$name.json"
    $patchedTrainer = Join-Path $Control "train_$name.py"

    Write-Host "=== TRAIN $name ===" -ForegroundColor Cyan

    if (Test-Path $receiptPath) {
        $existingReceipt = Get-Content $receiptPath -Raw | ConvertFrom-Json

        if (
            $existingReceipt.state -ne "MEASURED" -or
            $existingReceipt.binding_check -ne "PASS" -or
            [int]$existingReceipt.hyperparameters.seed -ne $seed -or
            -not (Test-Path $adapterFile)
        ) {
            Refuse "$name is partial or invalid; no automatic overwrite permitted"
        }

        Write-Host "$name already measured; preserving adapter." -ForegroundColor Yellow
    }
    else {
        if (Test-Path $runDirectory) {
            $existingItems = Get-ChildItem $runDirectory -Force -ErrorAction SilentlyContinue
            if ($existingItems) {
                Refuse "$name has partial files; inspect them before retrying"
            }
        }

        New-Item -ItemType Directory -Force $runDirectory | Out-Null

        $patched = $originalTrainer.Replace(
            'OUT = Path("out/train"); OUT.mkdir(parents=True, exist_ok=True)',
            ('OUT = Path("' + $relativeOutput + '"); OUT.mkdir(parents=True, exist_ok=True)')
        )

        $patched = $patched.Replace(
            "random_state=11",
            "random_state=$seed"
        )

        $patched = $patched.Replace(
            "seed=11",
            "seed=$seed"
        )

        $patched = $patched.Replace(
            '"seed": 11',
            ('"seed": ' + $seed)
        )

        if ($patched -eq $originalTrainer) {
            Refuse "trainer patch produced no changes for $name"
        }

        [IO.File]::WriteAllText(
            $patchedTrainer,
            $patched,
            [Text.UTF8Encoding]::new($false)
        )

        Invoke-Python `
            -Arguments @($patchedTrainer) `
            -LogPath (Join-Path $runDirectory "training.log")

        if (-not (Test-Path $receiptPath)) {
            Refuse "$name did not produce training_receipt.json"
        }

        if (-not (Test-Path $adapterFile)) {
            Refuse "$name did not produce adapter_model.safetensors"
        }

        $receipt = Get-Content $receiptPath -Raw | ConvertFrom-Json

        if ($receipt.state -ne "MEASURED") {
            Refuse "$name state is $($receipt.state), expected MEASURED"
        }

        if ($receipt.binding_check -ne "PASS") {
            Refuse "$name binding check failed: $($receipt.binding_check)"
        }

        if ([int]$receipt.hyperparameters.seed -ne $seed) {
            Refuse "$name receipt recorded the wrong seed"
        }
    }

    Test-CorpusHash

    Write-Host "=== EVALUATE $name ===" -ForegroundColor Cyan

    if (-not (Test-Path $metricsPath)) {
        Invoke-Python `
            -Arguments @(
                $Evaluator,
                "--study-root", $Study,
                "--name", $name,
                "--adapter", $adapterPath
            ) `
            -LogPath (Join-Path $Study "evaluation-$name.log")
    }
    else {
        Write-Host "$name evaluation already exists; preserving it." -ForegroundColor Yellow
    }
}

Write-Host "=== AGGREGATE FIVE-SEED STUDY ===" -ForegroundColor Cyan

Invoke-Python `
    -Arguments @(
        $Evaluator,
        "--study-root", $Study,
        "--aggregate"
    ) `
    -LogPath (Join-Path $Study "aggregate.log")

# -----------------------------------------------------------------------------
# BUILD COMMITTABLE EVIDENCE PACKAGE â€” NO MODEL WEIGHTS
# -----------------------------------------------------------------------------

Write-Host "=== BUILD EVIDENCE PACKAGE ===" -ForegroundColor Cyan

if (Test-Path $Evidence) {
    Remove-Item $Evidence -Recurse -Force
}
New-Item -ItemType Directory -Force $Evidence | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Evidence "training") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Evidence "evaluation") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Evidence "frozen") | Out-Null

Copy-Item `
    (Join-Path $Study "frozen\*") `
    (Join-Path $Evidence "frozen") `
    -Recurse -Force

Copy-Item `
    (Join-Path $Study "evaluation\*") `
    (Join-Path $Evidence "evaluation") `
    -Recurse -Force

Copy-Item `
    "out\train\training_receipt.json" `
    (Join-Path $Evidence "training\training_receipt-seed-011.json") `
    -Force

$adapterIndex = @()

$run1Hash = (
    Get-FileHash "out\train\adapter\adapter_model.safetensors" -Algorithm SHA256
).Hash

$adapterIndex += [ordered]@{
    seed = 11
    tag = "triage-lora-run1"
    commit = "427a70eb0804d814bf32d2cfc2713e230e468691"
    local_path = "out/train/adapter"
    adapter_sha256 = $run1Hash
    promotion_status = "NOT_PROMOTABLE"
}

foreach ($seed in $Seeds) {
    $name = "seed-{0:d3}" -f $seed
    $sourceReceipt = Join-Path $Study "$name\training_receipt.json"
    $targetReceipt = Join-Path $Evidence "training\training_receipt-$name.json"
    $adapterFile = Join-Path $Study "$name\adapter\adapter_model.safetensors"

    Copy-Item $sourceReceipt $targetReceipt -Force

    $receipt = Get-Content $sourceReceipt -Raw | ConvertFrom-Json
    $adapterHash = (Get-FileHash $adapterFile -Algorithm SHA256).Hash

    $adapterIndex += [ordered]@{
        seed = $seed
        local_path = "out/train/study/$name/adapter"
        adapter_sha256 = $adapterHash
        final_training_loss = $receipt.final_training_loss
        seconds = $receipt.seconds
        binding_check = $receipt.binding_check
        promotion_status = $receipt.promotion_status
    }
}

$adapterIndex | ConvertTo-Json -Depth 10 |
    Set-Content `
        (Join-Path $Evidence "adapter-index.json") `
        -Encoding utf8NoBOM

$environmentReceipt = [ordered]@{
    schema = "szl.five-seed-environment/v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    repository_commit = (git rev-parse HEAD).Trim()
    branch = (git branch --show-current).Trim()
    python = (& $Python --version 2>&1 | Out-String).Trim()
    pip_freeze = @(& $Python -m pip freeze)
    nvidia_smi = @(nvidia-smi)
    release_status = "BLOCKED"
    promotion_status = "NOT_PROMOTABLE"
}

$environmentReceipt | ConvertTo-Json -Depth 10 |
    Set-Content `
        (Join-Path $Evidence "environment-receipt.json") `
        -Encoding utf8NoBOM

$studyReadme = @"
# TypeSafe Triage five-seed measured study

Seeds: 11, 23, 37, 53, 71.

The corpus split was frozen by template family before the additional runs.
The untouched base model and every adapter were evaluated on the identical
113-row held-family manifest using greedy decoding and no malformed-JSON repair.

This directory contains:

- frozen train and held manifests;
- all five training receipts;
- base and adapter evaluation receipts;
- complete raw predictions;
- complete failure files;
- aggregate metrics and CSV export;
- adapter hashes without publishing gated model weights;
- environment and package evidence.

Training and evaluation are measured. The existing contamination verdict
remains attached. Release remains BLOCKED and promotion remains
NOT_PROMOTABLE unless separate release gates establish otherwise.
"@

[IO.File]::WriteAllText(
    (Join-Path $Evidence "README.md"),
    $studyReadme,
    [Text.UTF8Encoding]::new($false)
)

# -----------------------------------------------------------------------------
# VALIDATE EVIDENCE BEFORE GIT COMMIT
# -----------------------------------------------------------------------------

Write-Host "=== VALIDATE EVIDENCE ===" -ForegroundColor Cyan

$aggregatePath = Join-Path $Evidence "evaluation\aggregate_metrics.json"
if (-not (Test-Path $aggregatePath)) {
    Refuse "aggregate metrics are missing"
}

$aggregate = Get-Content $aggregatePath -Raw | ConvertFrom-Json

if ($aggregate.held_rows -ne 113) {
    Refuse "aggregate held-row count is not 113"
}

if ($aggregate.targets.Count -ne 6) {
    Refuse "expected base plus five adapter evaluation targets"
}

if ($aggregate.promotion_status -ne "NOT_PROMOTABLE") {
    Refuse "promotion boundary changed unexpectedly"
}

# Ensure no individual file would violate GitHub's ordinary 100 MB file limit.
Get-ChildItem $Evidence -Recurse -File | ForEach-Object {
    if ($_.Length -ge 95MB) {
        Refuse "evidence file is too large for ordinary Git: $($_.FullName)"
    }
}

# -----------------------------------------------------------------------------
# COMMIT AND PUSH CODE + EVIDENCE
# -----------------------------------------------------------------------------

Write-Host "=== COMMIT AND PUSH MEASURED STUDY ===" -ForegroundColor Cyan

git add `
    scripts/five_seed_eval.py `
    evidence/five-seed-study

if ($LASTEXITCODE -ne 0) {
    Refuse "git add failed"
}

git diff --cached --check
if ($LASTEXITCODE -ne 0) {
    Refuse "staged diff validation failed"
}

$staged = git diff --cached --name-only

if ($staged) {
    git commit -m "Measure five-seed triage study on frozen family holdout"
    if ($LASTEXITCODE -ne 0) {
        Refuse "git commit failed"
    }
}
else {
    Write-Host "No new study changes to commit." -ForegroundColor Yellow
}

$branch = (git branch --show-current).Trim()
if (-not $branch) {
    Refuse "branch became detached"
}

git push estate $branch
if ($LASTEXITCODE -ne 0) {
    Refuse "branch push failed; local evidence remains intact"
}

$studyTag = "triage-lora-study5-measured"
$existingTag = git tag --list $studyTag

if (-not $existingTag) {
    git tag -a $studyTag -m "Five-seed training and frozen held-family evaluation measured; promotion not established"
    if ($LASTEXITCODE -ne 0) {
        Refuse "study tag creation failed"
    }
}
else {
    $tagTarget = (git rev-list -n 1 $studyTag).Trim()
    $headTarget = (git rev-parse HEAD).Trim()

    if ($tagTarget -ne $headTarget) {
        Refuse "$studyTag already exists on a different commit"
    }
}

git push estate $studyTag
if ($LASTEXITCODE -ne 0) {
    Refuse "study tag push failed; do not move the tag"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "FIVE-SEED TRAINING AND FROZEN EVALUATION COMPLETE" -ForegroundColor Green
Write-Host "Evidence: evidence\five-seed-study" -ForegroundColor Green
Write-Host "Tag: triage-lora-study5-measured" -ForegroundColor Green
Write-Host "Release: BLOCKED" -ForegroundColor Yellow
Write-Host "Promotion: NOT_PROMOTABLE" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green