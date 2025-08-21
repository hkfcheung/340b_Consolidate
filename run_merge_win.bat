@echo off
REM --- Adjust this path to your new project root ---
set PROJ=C:\Users\hkfch\OneDrive\Documents\PythonProjs\340b_Consolidate

set PYEXE=%PROJ%\.venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=python

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$proj='%PROJ%'; $py='%PYEXE%'; cd $proj; if(-not (Test-Path 'logs')){New-Item -ItemType Directory logs|Out-Null};" ^
  "$ts=(Get-Date -Format 'yyyy-MM-dd_HHmmss'); $log=Join-Path 'logs' ('merge_'+$ts+'.log');" ^
  "Add-Type -AssemblyName PresentationFramework;" ^
  "[System.Windows.MessageBox]::Show('Starting 340B merge...','340B Merger','OK','Information') | Out-Null;" ^
  "& $py 'merge_340b.py' --input-dir '.\input' --output '.\output\cleaned_340B_list.xlsx' *>&1 | Tee-Object $log;" ^
  "[System.Windows.MessageBox]::Show('Merge complete. Log: '+$log,'340B Merger','OK','Information') | Out-Null;"
  