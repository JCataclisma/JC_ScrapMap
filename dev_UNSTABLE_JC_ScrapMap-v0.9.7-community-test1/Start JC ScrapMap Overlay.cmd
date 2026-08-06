@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" -Overlay
if errorlevel 1 (
  echo.
  echo JC ScrapMap overlay stopped with an error.
  pause
)
