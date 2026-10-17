@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" Main.py %*
set "DIO_EXIT=%ERRORLEVEL%"
echo Codigo de saida: %DIO_EXIT%
pause
exit /b %DIO_EXIT%
:missing
echo Ambiente nao instalado. Execute instalar.bat primeiro.
pause
exit /b 2
