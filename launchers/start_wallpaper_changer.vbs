Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = fso.BuildPath(base, "..\main.py")
absScript = fso.GetAbsolutePathName(scriptPath)

If Not fso.FileExists(absScript) Then
    MsgBox "Impossibile trovare main.py. Controlla che i file siano nella cartella corretta.", vbExclamation, "Wallpaper Changer"
    WScript.Quit 1
End If

command = "py -3w """ & absScript & """"

Set shell = CreateObject("WScript.Shell")
On Error Resume Next
shell.Run command, 0
If Err.Number <> 0 Then
    MsgBox "Errore durante l'avvio: " & Err.Description, vbCritical, "Wallpaper Changer"
End If
