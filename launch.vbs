Option Explicit
Dim shell, projectDir, python, script

Set shell = CreateObject("WScript.Shell")
projectDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' Find Python in the pipenv virtualenv
python = shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.pyenv\pyenv-win\shims\python.exe"

' Fall back to python on PATH if pyenv shim not found
Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(python) Then
    python = "python"
End If

script = projectDir & "launcher.py"

' Run without console window (0 = hidden, False = don't wait)
shell.Run """" & python & """ """ & script & """", 0, False

Set shell = Nothing
Set fso = Nothing
