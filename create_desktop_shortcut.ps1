# Создание ярлыка KeySet на рабочем столе

 = [Environment]::GetFolderPath('Desktop')
 = Join-Path  'KeySet.lnk'

 = 'C:\AI\.venv\Scripts\pythonw.exe'
if (-not (Test-Path )) {
    Write-Host '✖ Ошибка: pythonw.exe не найден по пути:'  -ForegroundColor Red
    exit 1
}

 = 'C:\AI\yandex\keyset\run_keyset.pyw'
 = 'C:\AI\yandex\keyset'
 = 'C:\AI\yandex\keyset\keyset_icon.ico'

 = New-Object -ComObject WScript.Shell
 = .CreateShortcut()
.TargetPath = 
.Arguments = ' "' +  + '"'
.WorkingDirectory = 
.Description = 'KeySet — парсер Yandex Wordstat'
.WindowStyle = 7
if (Test-Path ) {
    .IconLocation = 
}
.Save()

Write-Host '✓ Ярлык KeySet создан на рабочем столе!' -ForegroundColor Green
Write-Host 'Путь: '  -ForegroundColor Cyan
Write-Host 'Запуск происходит без окна терминала.' -ForegroundColor Yellow
