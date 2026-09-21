$ErrorActionPreference = "Continue"
cd C:\Users\steph\szl-typesafe-triage
$vpy = ".\.venv\Scripts\python.exe"
$stamp = Get-Date -Format yyyyMMdd_HHmmss
$CorpusPath = "output/triage_distill_v0.5.0.jsonl"
$SplitPath  = "output/triage_distill_split_v0.4.0.jsonl"
$Manifest = [ordered]@{ started = (Get-Date).ToString("o"); stages = [ordered]@{} }

function Invoke-Stage([string]$StageName, [scriptblock]$Body) {
  Write-Host "=== $StageName ===" -ForegroundColor Cyan
  & $Body
  $rc = $LASTEXITCODE
  $Manifest.stages[$StageName] = $rc
  if ($rc -ne 0) {
    Write-Host "HALT AT $StageName (exit $rc)" -ForegroundColor Red
    $Manifest.halted_at = $StageName
    $Manifest | ConvertTo-Json -Depth 6 | Set-Content ".\out\manifest_$stamp.json" -Encoding utf8
    throw "HALT:$StageName"
  }
  Write-Host "$StageName OK" -ForegroundColor Green
}

try {
  Invoke-Stage "S2_GENERATE" { & $vpy scripts\build_corpus_typed.py --out $CorpusPath 2>&1 | Tee-Object ".\out\gen_$stamp.log" }
  Invoke-Stage "S3_CORPUS_GATE" { & $vpy scripts\corpus_gate.py $CorpusPath 2>&1 | Tee-Object ".\out\gate_$stamp.log" }
  $shaBefore = (Get-FileHash $SplitPath -Algorithm SHA256).Hash
  Invoke-Stage "S4_GATE_RERUN" { & $vpy scripts\corpus_gate.py $CorpusPath 2>&1 | Tee-Object ".\out\gate2_$stamp.log" }
  $shaAfter = (Get-FileHash $SplitPath -Algorithm SHA256).Hash
  if ($shaBefore -ne $shaAfter) {
    Write-Host "HALT - nondeterministic split $($shaBefore.Substring(0,16)) -> $($shaAfter.Substring(0,16))" -ForegroundColor Red
    throw "HALT:DETERMINISM"
  }
  Write-Host "SPLIT REPRODUCED BYTE-IDENTICAL $($shaAfter.Substring(0,16))" -ForegroundColor Green
  $Manifest.split_sha = $shaAfter.Substring(0,16)
  $Manifest.stages["S5_DETERMINISM"] = 0

  Invoke-Stage "S6_VERIFY_SPLIT" { & $vpy scripts\verify_split.py $SplitPath $CorpusPath 2>&1 | Tee-Object ".\out\verify_$stamp.log" }
  Invoke-Stage "S6B_LEXICAL_LEAKAGE" { & $vpy scripts\leakage.py $SplitPath 2>&1 | Tee-Object ".\out\leakage_$stamp.log" }
  Invoke-Stage "S7_PREFLIGHT" { & $vpy scripts\preflight.py 2>&1 | Tee-Object ".\out\pre_$stamp.log" }

  $plan = Get-Content .\out\invocation_plan.json -Raw | ConvertFrom-Json
  $trainArgs = @(); if ($plan.train_args) { $trainArgs = @($plan.train_args) }
  $gateArgs  = @(); if ($plan.gate_args)  { $gateArgs  = @($plan.gate_args) }
  Write-Host "TRAIN: $($plan.train_script) $($trainArgs -join ' ')" -ForegroundColor Yellow
  Write-Host "GATE:  $($plan.gate_script) $($gateArgs -join ' ')" -ForegroundColor Yellow
  $Manifest.train_invocation = "$($plan.train_script) $($trainArgs -join ' ')"

  Invoke-Stage "S8_TRAIN" { & $vpy $plan.train_script @trainArgs 2>&1 | Tee-Object ".\out\train_$stamp.log" }
  Invoke-Stage "S9_BEHAVIORAL_GATE" { & $vpy $plan.gate_script @gateArgs 2>&1 | Tee-Object ".\out\behav_$stamp.log" }

  $Manifest.verdict = "ALL STAGES PASSED"
  $Manifest.finished = (Get-Date).ToString("o")
  $Manifest | ConvertTo-Json -Depth 6 | Set-Content ".\out\manifest_$stamp.json" -Encoding utf8
  Write-Host "=== ALL STAGES PASSED - out\manifest_$stamp.json ===" -ForegroundColor Green
}
catch { Write-Host "RUN HALTED: $($_.Exception.Message)" -ForegroundColor Red }