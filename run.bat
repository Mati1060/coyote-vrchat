@echo off
setlocal
cd /d "%~dp0"
title Coyote x VRChat

rem Find Python (the "py" launcher ships with the official installer)
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

if not exist ".venv\Scripts\python.exe" (
  echo Creating the program environment ^(first run only^)...
  %PY% -m venv .venv
  if errorlevel 1 goto failed
)

".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto failed

".venv\Scripts\python.exe" main.py %*
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo Something went wrong ^(see the message above^). Make sure Python 3.10+ is installed: https://www.python.org/downloads/
pause
exit /b 1
