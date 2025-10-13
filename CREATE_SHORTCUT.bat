@echo off
chcp 65001 >nul
echo ========================================
echo   SemTool - Создание ярлыка
echo ========================================
echo.

powershell -ExecutionPolicy Bypass -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut(\"$env:USERPROFILE\OneDrive\Desktop\SemTool.lnk\"); $Shortcut.TargetPath = \"C:\AI\.venv\Scripts\pythonw.exe\"; $Shortcut.Arguments = \"C:\AI\yandex\semtool\run_semtool.pyw\"; $Shortcut.WorkingDirectory = \"C:\AI\yandex\semtool\"; $Shortcut.IconLocation = \"C:\Python313\DLLs\py.ico\"; $Shortcut.Description = \"SemTool - Yandex Wordstat Parser\"; $Shortcut.Save(); Write-Host \"[OK] Ярлык создан на рабочем столе\""

echo.
echo ========================================
echo   Готово!
echo ========================================
echo   Ярлык SemTool создан на рабочем столе
echo   Можно закрыть это окно
echo ========================================
pause
