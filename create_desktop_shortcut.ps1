# Создание ярлыка SemTool на рабочем столе

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "SemTool.lnk"

# Путь к pythonw.exe (запуск без окна терминала)
# Используем venv из C:\AI\.venv
$PythonPath = "C:\AI\.venv\Scripts\pythonw.exe"

# Проверяем что pythonw.exe существует
if (-not (Test-Path $PythonPath)) {
    Write-Host "❌ Ошибка: pythonw.exe не найден по пути: $PythonPath" -ForegroundColor Red
    exit 1
}

# Путь к .pyw файлу
$TargetPath = "C:\AI\yandex\semtool\run_semtool.pyw"

# Рабочая директория
$WorkingDir = "C:\AI\yandex"

# Создаем объект WScript.Shell
$WshShell = New-Object -ComObject WScript.Shell

# Создаем ярлык
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PythonPath
$Shortcut.Arguments = "`"$TargetPath`""
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.Description = "SemTool - Парсер Yandex Wordstat"
$Shortcut.WindowStyle = 7  # Minimized (скрыто)

# Используем стандартную иконку Python или системную
if (Test-Path "C:\Python313\DLLs\py.ico") {
    $Shortcut.IconLocation = "C:\Python313\DLLs\py.ico"
} elseif (Test-Path "C:\Program Files\Python313\DLLs\py.ico") {
    $Shortcut.IconLocation = "C:\Program Files\Python313\DLLs\py.ico"
} else {
    # Используем иконку Chrome (зеленая иконка)
    $Shortcut.IconLocation = "C:\Program Files\Google\Chrome\Application\chrome.exe, 0"
}

# Сохраняем ярлык
$Shortcut.Save()

Write-Host "✅ Ярлык SemTool создан на рабочем столе!" -ForegroundColor Green
Write-Host "Путь: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ярлык будет запускать SemTool БЕЗ окна терминала" -ForegroundColor Yellow
