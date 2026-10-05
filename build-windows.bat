@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Please install Python 3.11 x64 from python.org and enable the py launcher.
  pause
  exit /b 1
)

py -3.11 -m venv .venv
if errorlevel 1 goto fail
call .venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto fail
call .venv\Scripts\python.exe -m pip install -r requirements-windows.txt
if errorlevel 1 goto fail
call .venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name SonyFocusViewer --collect-all rawpy --collect-all pillow_heif app.py
if errorlevel 1 goto fail

echo.
echo Built: %CD%\dist\SonyFocusViewer.exe
echo Run install-for-user.ps1 from PowerShell to add the app to Open with / Default apps.
pause
exit /b 0

:fail
echo Build failed. See the error above.
pause
exit /b 1
