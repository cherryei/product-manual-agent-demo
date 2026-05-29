@echo off
REM ==========================================================================
REM  Product Manual Agent - One-click deploy and run (Windows)
REM
REM  Usage:  double-click run.bat   OR   run.bat   in cmd / PowerShell
REM  First run auto-creates .venv + installs deps, then starts the server.
REM ==========================================================================
setlocal

cd /d "%~dp0"

set "HOST=127.0.0.1"
set "PORT=8000"
set "VENV_DIR=%~dp0.venv"

REM 1. Find Python
where python >nul 2>&1
if errorlevel 1 (
  echo [X] Python not found. Install Python 3.9+ from https://www.python.org/downloads/
  pause
  exit /b 1
)

REM 2. Create venv on first run
if not exist "%VENV_DIR%" (
  echo [*] First run: creating virtual environment .venv ...
  python -m venv "%VENV_DIR%"
)

REM 3. Activate
call "%VENV_DIR%\Scripts\activate.bat"

REM 4. Install deps (only first time or when requirements.txt changes)
if not exist "%VENV_DIR%\.deps-installed" (
  echo [*] Installing dependencies ...
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  echo done> "%VENV_DIR%\.deps-installed"
) else (
  echo [*] Dependencies ready, skipping install.
)

echo.
echo ============================================================
echo   Server starting. Open in browser:  http://%HOST%:%PORT%
echo   Health check: http://%HOST%:%PORT%/health
echo   Stop: Ctrl + C
echo ============================================================
echo.

uvicorn app.main:app --host %HOST% --port %PORT%

endlocal
