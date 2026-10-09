@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

rem Optional: override the venv location, e.g.
rem   set CM_VENV=C:\cm_venv
if not defined CM_VENV set "CM_VENV=%~dp0.venv"

echo ============================================
echo  CaptureMonitor - one-click EXE build
echo  venv: %CM_VENV%
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] "python" not found in PATH. Install Python 3.9+ ^(check "Add to PATH"^) and retry.
    goto :error
)

if not exist "%CM_VENV%" (
    echo [1/6] Creating virtual environment...
    python -m venv "%CM_VENV%"
    if errorlevel 1 goto :error
) else (
    echo [1/6] Reusing existing venv: %CM_VENV%
)

echo [2/6] Activating virtual environment...
call "%CM_VENV%\Scripts\activate.bat"
if errorlevel 1 goto :error

echo [3/6] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [4/6] Installing dependencies and PyInstaller...
rem Antivirus can lock a DLL (e.g. PyQt5\Qt5\bin\d3dcompiler_47.dll) during
rem extraction -> retry a few times before giving up.
set /a ATTEMPT=0
:install
set /a ATTEMPT+=1
pip install --no-cache-dir -r requirements-build.txt
if not errorlevel 1 goto :installed
if !ATTEMPT! GEQ 3 goto :error
echo [WARN] pip failed ^(attempt !ATTEMPT!/3^). Retrying in 3 seconds...
timeout /t 3 /nobreak >nul
goto :install
:installed

echo [5/6] Building with PyInstaller...
pyinstaller --clean --noconfirm CaptureMonitor.spec
if errorlevel 1 goto :error

echo [6/6] Copying DEMO.png next to the EXE (optional, replaceable)...
if exist "DEMO.png" copy /y "DEMO.png" "dist\DEMO.png" >nul

echo.
echo Build succeeded. Output: dist\CaptureMonitor.exe
echo.
pause
exit /b 0

:error
echo.
echo ============================================
echo  Build FAILED.
echo ============================================
echo "Permission denied" / Errno 13 on a .dll is almost always:
echo   A. Antivirus (Windows Defender / 360 / Huorong) locking the DLL.
echo      - Add this folder AND %%LOCALAPPDATA%%\Temp to the AV exclusion list,
echo        or temporarily disable real-time protection.
echo   B. Folder ACL / read-only on the current drive (e.g. D:\AI_View).
echo      - Try building from a plain local path, or move only the venv:
echo          rmdir /s /q .venv
echo          set CM_VENV=C:\cm_venv
echo          build.bat
echo   C. Leftover locked .venv:
echo          rmdir /s /q .venv
echo      then right-click build.bat -^> "Run as administrator".
echo.
pause
exit /b 1
