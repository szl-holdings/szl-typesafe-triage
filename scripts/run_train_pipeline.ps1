$ErrorActionPreference = "Continue"
cd C:\Users\steph\szl-typesafe-triage
$vpy = ".\.venv\Scripts\python.exe"
$stamp = Get-Date -Format yyyyMMdd_HHmmss
$AdapterDir = "out/triage-unsloth-bf16"
$Cfg = "$AdapterDir/adapter_config.json"

if (-not (Test-Path $Cfg)) { Write-Host "HALT - $Cfg not found" -ForegroundColor Red; return }
$Base = & $vpy -c "import json,sys;print(json.load(open(sys.argv[1]))['base_model_name_or_path'])" $Cfg
if (-not $Base) { Write-Host "HALT - base_model_name_or_path absent" -ForegroundColor Red; return }
Write-Host "BASE MODEL FROM ADAPTER PROVENANCE: $Base" -ForegroundColor Yellow
Write-Host "OUT DIR: $AdapterDir" -ForegroundColor Yellow

$Backup = "out/triage-unsloth-bf16.v0.3.0-corpus.bak"
if (-not (Test-Path $Backup)) {
  Copy-Item $AdapterDir $Backup -Recurse -Force
  Write-Host "PRESERVED v0.3.0-corpus adapter at $Backup" -ForegroundColor Green
}

Write-Host "=== S8_TRAIN ===" -ForegroundColor Cyan
& $vpy scripts\train_triage_unsloth.py $Base $AdapterDir 2>&1 | Tee-Object ".\out\train_$stamp.log"
if ($LASTEXITCODE -ne 0) { Write-Host "HALT AT TRAIN (exit $LASTEXITCODE)" -ForegroundColor Red; return }
Write-Host "TRAIN OK" -ForegroundColor Green

Write-Host "=== S9_BEHAVIORAL_GATE ===" -ForegroundColor Cyan
& $vpy scripts\gate.py 2>&1 | Tee-Object ".\out\behav_$stamp.log"
$gc = $LASTEXITCODE
Write-Host "BEHAVIORAL GATE EXIT $gc" -ForegroundColor Cyan
[ordered]@{ stamp=$stamp; base=$Base; adapter=$AdapterDir; backup=$Backup;
  split_sha="5dd99e6c05ff1fa3"; corpus_sha="c3fb8006e2a78848"; gate_exit=$gc;
  finished=(Get-Date).ToString("o") } | ConvertTo-Json | Set-Content ".\out\train_manifest_$stamp.json" -Encoding utf8
Write-Host "MANIFEST out\train_manifest_$stamp.json" -ForegroundColor Green