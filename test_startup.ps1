Write-Host "===================================" -ForegroundColor Cyan
Write-Host "   SEMTOOL STARTUP CHECK" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

cd C:\AI\yandex

Write-Host "[1/3] Checking imports..." -ForegroundColor Yellow
python -c "from keyset.app.main import main; print('[OK] Import main')"
if ($LASTEXITCODE -ne 0) { 
    Write-Host "[FAIL] Import failed" -ForegroundColor Red
    exit 1 
}

Write-Host "[2/3] Checking ProxyStore..." -ForegroundColor Yellow
python -c "from keyset.core import proxy_store; px = proxy_store.get_all_proxies(); print(f'[OK] ProxyStore: {len(px)} proxies')"
if ($LASTEXITCODE -ne 0) { 
    Write-Host "[FAIL] ProxyStore failed" -ForegroundColor Red
    exit 1 
}

Write-Host "[3/3] Checking ProxyManager..." -ForegroundColor Yellow
python -c "from keyset.app.proxy_manager import ProxyManagerDialog; print('[OK] ProxyManager import')"
if ($LASTEXITCODE -ne 0) { 
    Write-Host "[FAIL] ProxyManager failed" -ForegroundColor Red
    exit 1 
}

Write-Host ""
Write-Host "===================================" -ForegroundColor Green
Write-Host "   ALL CHECKS PASSED!" -ForegroundColor Green
Write-Host "   Software ready to launch" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
