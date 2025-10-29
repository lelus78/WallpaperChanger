Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
pidPath = fso.BuildPath(base, "..\wallpaperchanger.pid")
absPidPath = fso.GetAbsolutePathName(pidPath)

If Not fso.FileExists(absPidPath) Then
    MsgBox "Nessun processo attivo trovato (PID mancante).", vbInformation, "Wallpaper Changer"
    WScript.Quit 0
End If

Set pidFile = fso.OpenTextFile(absPidPath, 1)
pid = Trim(pidFile.ReadAll)
pidFile.Close

If pid = "" Then
    fso.DeleteFile absPidPath, True
    MsgBox "Il file PID è vuoto. L'app potrebbe non essere in esecuzione.", vbInformation, "Wallpaper Changer"
    WScript.Quit 0
End If

Set shell = CreateObject("WScript.Shell")
On Error Resume Next
shell.Run "taskkill /PID " & pid & " /F", 0, True
result = Err.Number
Err.Clear

If result = 0 Then
    If fso.FileExists(absPidPath) Then
        fso.DeleteFile absPidPath, True
    End If
    MsgBox "Wallpaper Changer è stato arrestato.", vbInformation, "Wallpaper Changer"
Else
    MsgBox "Impossibile terminare il processo (PID: " & pid & ").", vbCritical, "Wallpaper Changer"
End If
