@echo off
title The Empty Shift
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 run_game.py
  goto check
)
where python >nul 2>&1
if %errorlevel% equ 0 (
  python run_game.py
  goto check
)

echo.
echo Python was not found in PATH.
echo Install Python from https://www.python.org/downloads/
echo During setup, enable "Add python.exe to PATH", then run this again.
echo.
pause
exit /b 1

:check
if errorlevel 1 (
  echo.
  echo The game exited with an error. Copy any message above if you need help.
  pause
)
