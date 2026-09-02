Option Explicit

Dim shell, fso, projectFolder, pythonw, appFile, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectFolder = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python312\pythonw.exe"
appFile = projectFolder & "\app.py"

If Not fso.FileExists(pythonw) Then
    MsgBox "Python non è stato trovato in:" & vbCrLf & pythonw, 16, "YT-DLP"
    WScript.Quit 1
End If

If Not fso.FileExists(appFile) Then
    MsgBox "Il file app.py non è stato trovato.", 16, "YT-DLP"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectFolder
command = Chr(34) & pythonw & Chr(34) & " " & Chr(34) & appFile & Chr(34)
shell.Run command, 0, False
