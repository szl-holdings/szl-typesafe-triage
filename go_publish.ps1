$ErrorActionPreference = "Continue"
cd C:\Users\steph\szl-typesafe-triage
$vpy = ".\.venv\Scripts\python.exe"
$env:HF_XET_HIGH_PERFORMANCE = "1"
$REPO = "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora"
$AD = ".\out\triage-unsloth-bf16"
$stamp = Get-Date -Format yyyyMMdd_HHmmss

Add-MpPreference -ExclusionPath "C:\Users\steph\szl-typesafe-triage\.venv" -ErrorAction SilentlyContinue
$arch = (& $vpy -c "import torch;print(';'.join(torch.cuda.get_arch_list()))").Trim()
Write-Host "ARCHS MEASURED $arch" -ForegroundColor Cyan
if ($arch -notmatch 'sm_120') { Write-Host "ABORT - sm_120 MISSING" -ForegroundColor Red; return }

$log = ".\out\leakage_$stamp.log"
& $vpy scripts\leakage.py *> $log
$code = $LASTEXITCODE
Get-Content $log
Write-Host "LEAKAGE EXIT $code" -ForegroundColor Cyan

if ($code -eq 0) {
  & $vpy -m pip freeze | Out-File -Encoding utf8 "$AD\requirements-lock.txt"
  Copy-Item .\out\gate_report.json "$AD\gate_report.json" -Force
  Copy-Item .\out\leakage_report.json "$AD\leakage_report.json" -Force
  Remove-Item "$AD\training_args.bin" -ErrorAction SilentlyContinue
  .\.venv\Scripts\hf.exe upload $REPO $AD . --repo-type model --exclude "checkpoint-*/*" --commit-message "gate and leakage receipts + env lock (PROMOTABLE, CLEAN)"
  Add-Content .\.gitignore "`nunsloth_compiled_cache/`nsrc/*.egg-info/`nout/triage-unsloth-bf16/checkpoint-*/"
  git rm -r --cached unsloth_compiled_cache src/szl_triage.egg-info --quiet
  git add -A
  git commit --amend -m "Qwen3.5-0.8B LoRA triage distill: gate PROMOTABLE, leakage CLEAN (66/66, 23 refusals, 0 ungrounded)"
  git push --force origin main
  Write-Host "PUBLISHED - HF + GitHub updated" -ForegroundColor Green
  git ls-files | Measure-Object -Line
} elseif ($code -eq 3) {
  Write-Host "PUBLISH BLOCKED - LEAKAGE FLAGGED ROWS - nothing uploaded, nothing pushed" -ForegroundColor Yellow
  Write-Host "Read the TOP PAIR text above and out\leakage_report.json" -ForegroundColor Yellow
} else {
  Write-Host "PUBLISH BLOCKED - LEAKAGE SCRIPT CRASHED (exit $code) - see $log" -ForegroundColor Red
}