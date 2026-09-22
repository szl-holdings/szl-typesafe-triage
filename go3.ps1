$ErrorActionPreference = "Continue"
cd C:\Users\steph\szl-typesafe-triage
$vpy = ".\.venv\Scripts\python.exe"
New-Item -ItemType Directory -Force -Path .\out | Out-Null

Add-MpPreference -ExclusionPath "C:\Users\steph\szl-typesafe-triage\.venv" -ErrorAction SilentlyContinue
Write-Host "DEFENDER EXCLUSION ASSERTED" -ForegroundColor Green

$arch = (& $vpy -c "import torch;print(';'.join(torch.cuda.get_arch_list()))").Trim()
Write-Host "ARCHS MEASURED $arch" -ForegroundColor Cyan
if ($arch -notmatch 'sm_120') { & $vpy -m pip install --no-cache-dir --force-reinstall --no-deps ".\wheels\torch-2.14.0+cu130-cp311-cp311-win_amd64.whl" }

if (-not (Test-Path .\scripts\eval_receipts.py.bak)) { Copy-Item .\scripts\eval_receipts.py .\scripts\eval_receipts.py.bak }
$src = Get-Content .\scripts\eval_receipts.py.bak -Raw
$new = $src -replace 'is_grounded\(span, row\["input"\]\)', 'is_grounded(span if isinstance(span, str) else str(span.get("text", "")), row["input"])'
if ($new -eq $src) { Write-Host "PATCH FAILED - callsite not found" -ForegroundColor Yellow } else { Set-Content .\scripts\eval_receipts.py -Value $new -NoNewline; Write-Host "PATCH APPLIED" -ForegroundColor Green }

$log = ".\out\eval_$(Get-Date -Format yyyyMMdd_HHmmss).log"
& $vpy scripts\eval_receipts.py --adapter "out\triage-unsloth-bf16" --base "Qwen/Qwen3.5-0.8B" 2>&1 | Tee-Object -FilePath $log

Write-Host "===== VERDICT =====" -ForegroundColor Cyan
Select-String -Path $log -Pattern 'REFUSAL|GROUNDED|ACCURACY|MEASURED|PASS|FAIL|Traceback|Error' | ForEach-Object { $_.Line }
Write-Host "LOG $log"