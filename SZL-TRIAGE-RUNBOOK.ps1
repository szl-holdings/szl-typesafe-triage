param([switch]$PreflightOnly,[int]$Runs=5)
$ErrorActionPreference='Continue'
$Repo=$PSScriptRoot
$Py=Join-Path $Repo '.venv\Scripts\python.exe'
$S=Join-Path $Repo 'scripts\train_eval_publish.py'
$L=Join-Path $Repo 'reports'; New-Item -ItemType Directory -Force $L|Out-Null
function Stage($lbl,$a,$log){
  Write-Host "`n=== $lbl ===" -ForegroundColor Cyan
  $o = & $Py -u $S @a 2>&1
  $o | Tee-Object -FilePath $log | ForEach-Object { Write-Host $_ }
  if($LASTEXITCODE -ne 0){ throw "$lbl failed (exit $LASTEXITCODE). Log: $log" }
}
$t=Get-Date -Format yyyyMMdd-HHmmss
Stage 'PREFLIGHT' @('--diagnostic','--split','nonheldout','--no-train','--no-publish') (Join-Path $L "pre-$t.log")
if($PreflightOnly){ return }
for($i=1;$i -le $Runs;$i++){
  $seed=1000+$i
  Stage "RUN $i EVAL-BASE" @('--eval-only','--split','heldout','--no-publish','--seed',"$seed") (Join-Path $L "r$i-base-$t.log")
  Stage "RUN $i TRAIN"     @('--train','--no-publish','--seed',"$seed")                         (Join-Path $L "r$i-train-$t.log")
  Stage "RUN $i EVAL-POST" @('--eval-only','--split','heldout','--no-publish','--seed',"$seed") (Join-Path $L "r$i-post-$t.log")
}
Write-Host "`nRuns complete. Publishing was never attempted." -ForegroundColor Green
