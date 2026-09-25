' Runs run_email_agent.bat with no visible window (used by the scheduled task).
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run """" & here & "\run_email_agent.bat""", 0, True
