@echo off
chcp 65001 >nul
echo ========================================
echo   KeySet - Создание ярлыка
console output

echo.

echo Создаю ярлык KeySet.lnk на рабочем столе...

powershell -ExecutionPolicy Bypass -Command "
     = [Environment]::GetFolderPath('Desktop');
     = Join-Path  'KeySet.lnk';
     = New-Object -ComObject WScript.Shell;
     = .CreateShortcut();
    .TargetPath = 'C:\AI\.venv\Scripts\pythonw.exe';
    .Arguments = ' "C:\AI\yandex\keyset\run_keyset.pyw"';
    .WorkingDirectory = 'C:\AI\yandex\keyset';
    if (Test-Path 'C:\AI\yandex\keyset\keyset_icon.ico') { .IconLocation = 'C:\AI\yandex\keyset\keyset_icon.ico'; }
    .Description = 'KeySet — парсер Yandex Wordstat';
    .WindowStyle = 7;
    .Save();
    Write-Host '[OK] Ярлык создан на рабочем столе'
"

echo.
echo ========================================
echo   Готово!
echo ========================================
echo   Ярлык KeySet создан на рабочем столе
echo ========================================
pause
