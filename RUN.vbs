Option Explicit

Dim shell, fso, projectFolder, pythonw, appFile, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectFolder = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = projectFolder & "\.venv\Scripts\pythonw.exe"
appFile = projectFolder & "\app.py"

If Not fso.FileExists(pythonw) Then
    MsgBox "YT-DLP non è ancora installato." & vbCrLf & _
           "Esegui prima INSTALL.bat per creare l'ambiente locale .venv.", 16, "YT-DLP"
    WScript.Quit 1
End If

If Not fso.FileExists(appFile) Then
    MsgBox "Il file app.py non è stato trovato.", 16, "YT-DLP"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectFolder
command = Chr(34) & pythonw & Chr(34) & " " & Chr(34) & appFile & Chr(34)
shell.Run command, 0, False
