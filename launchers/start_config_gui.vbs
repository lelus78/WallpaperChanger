Set objShell = CreateObject("Wscript.Shell")
objShell.Run "pythonw """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\..\gui_config.py""", 0, False
