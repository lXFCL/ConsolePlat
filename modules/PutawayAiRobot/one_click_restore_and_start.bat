@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "VENV_DIR=%ROOT%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "APPDATA_LOCAL=%ROOT%\runtime_data\AppData\Roaming"
if not exist "%APPDATA_LOCAL%" mkdir "%APPDATA_LOCAL%"
set "APPDATA=%APPDATA_LOCAL%"
if not exist "%ROOT%\requirements.txt" (
  echo 缺少 requirements.txt，请确认已完整解压交付包。
  exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
  echo 未检测到 Python，请先安装 Python 3.11.x 并勾选 Add python.exe to PATH。
  exit /b 1
)
if not exist "%VENV_PY%" (
  python -m venv "%VENV_DIR%"
)
if not exist "%VENV_PY%" (
  echo 虚拟环境创建失败，系统找不到 Python 虚拟环境路径。
  exit /b 1
)
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%VENV_PY%" -m pip install -r "%ROOT%\requirements.txt"
if errorlevel 1 exit /b 1
"%VENV_PY%" -m playwright install chromium
if errorlevel 1 exit /b 1
"%VENV_PY%" "%ROOT%\verify_startup.py"
if errorlevel 1 exit /b 1
"%VENV_PY%" "%ROOT%\browser_dom_automation.py"
endlocal
