Set WshShell = WScript.CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut(WshShell.SpecialFolders("Desktop") & "\SemTool.lnk")
Shortcut.TargetPath = "C:\AI\yandex\RUN_SEMTOOL.bat"
Shortcut.WorkingDirectory = "C:\AI\yandex"
Shortcut.Description = "SemTool - Wordstat Parser (Рабочий)"
Shortcut.Save
