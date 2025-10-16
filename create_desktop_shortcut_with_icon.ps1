# Создание ярлыка KeySet с собственной иконкой

 = [Environment]::GetFolderPath('Desktop')
 = Join-Path  'KeySet.lnk'
 = 'C:\AI\.venv\Scripts\pythonw.exe'
 = 'C:\AI\yandex\keyset\run_keyset.pyw'
 = 'C:\AI\yandex\keyset\keyset_icon.ico'
 = 'C:\AI\yandex\keyset'

if (-not (Test-Path )) {
    Write-Host '✖ pythonw.exe не найден:'  -ForegroundColor Red
    exit 1
}

if (-not (Test-Path )) {
    Write-Host '⚠ Иконка не найдена:'  -ForegroundColor Yellow
}

 = New-Object -ComObject WScript.Shell
 = .CreateShortcut()
.TargetPath = 
.Arguments = ' "' +  + '"'
.WorkingDirectory = 
.Description = 'KeySet — парсер Yandex Wordstat'
if (Test-Path ) {
    .IconLocation = 
}
.Save()

Write-Host '✓ Готово! Ярлык KeySet создан на рабочем столе.' -ForegroundColor Green
