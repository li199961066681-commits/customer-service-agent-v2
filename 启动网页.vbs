Option Explicit

' Double-click: check key -> start Streamlit in background -> open browser
Dim fso, shell, dir, envPath, examplePath, content, stream, pythonExe, cmd

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = dir

envPath = dir & "\.env"
examplePath = dir & "\.env.example"

' Create .env if missing, then ask the user to fill the key
If Not fso.FileExists(envPath) Then
    fso.CopyFile examplePath, envPath
    MsgBox "Created .env. Please fill LLM_API_KEY (starts with sk-), save, then double-click again.", 48, "API Key Required"
    shell.Run "notepad " & envPath, 1, False
    WScript.Quit
End If

' Check whether LLM_API_KEY is filled
Set stream = fso.OpenTextFile(envPath, 1, False)
content = stream.ReadAll
stream.Close

If InStr(1, content, "LLM_API_KEY=sk-", vbTextCompare) = 0 Then
    MsgBox "Please fill LLM_API_KEY (starts with sk-) in .env, save, then double-click again.", 48, "API Key Required"
    shell.Run "notepad " & envPath, 1, False
    WScript.Quit
End If

' Start Streamlit with no console window
pythonExe = dir & "\venv\Scripts\python.exe"
cmd = "cmd /c " & Chr(34) & Chr(34) & pythonExe & Chr(34) & " -m streamlit run streamlit_app.py --server.headless=true --server.port=8501 > data\streamlit.log 2>&1" & Chr(34)
shell.Run cmd, 0, False

' Wait for the server, then open the browser
WScript.Sleep 8000
shell.Run "http://localhost:8501", 1, False
