# Создание ярлыка SemTool на рабочем столе с зеленой иконкой

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "SemTool.lnk"
$TargetPath = "C:\AI\yandex\semtool\run_semtool.pyw"
$IconPath = "C:\AI\yandex\semtool\semtool_icon.ico"
$WorkingDirectory = "C:\AI\yandex\semtool"

# Создаем COM объект для создания ярлыка
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)

# Настройки ярлыка
$Shortcut.TargetPath = "pythonw.exe"  # Запуск через pythonw (без консоли)
$Shortcut.Arguments = "`"$TargetPath`""
$Shortcut.WorkingDirectory = $WorkingDirectory
$Shortcut.Description = "SemTool - Wordstat Parser and SEO Tools"
$Shortcut.IconLocation = $IconPath

# Сохраняем ярлык
$Shortcut.Save()

Write-Host "[OK] Ярлык создан: $ShortcutPath" -ForegroundColor Green
Write-Host "[OK] Иконка: $IconPath" -ForegroundColor Green
Write-Host "[OK] Рабочий стол обновлен!" -ForegroundColor Green
