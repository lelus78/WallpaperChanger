Set objShell = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the parent directory
parentDir = fso.GetParentFolderName(WScript.ScriptFullName) & "\.."

' Start the main wallpaper changer app in background
objShell.Run "pythonw """ & parentDir & "\main.py""", 0, False

' Wait a moment for the main app to initialize
WScript.Sleep 1000

' Start the modern GUI
objShell.Run "pythonw """ & parentDir & "\gui_modern.py""", 0, False
