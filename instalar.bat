@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
py -3.14 -c "import sys; raise SystemExit(sys.version_info[:2] != (3,14))" >nul 2>&1
if errorlevel 1 goto no_python
if not exist ".venv\Scripts\python.exe" py -3.14 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import sys; raise SystemExit(sys.version_info[:2] != (3,14))"
if errorlevel 1 goto wrong_venv
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist ".env" copy /y ".env.example" ".env" >nul
".venv\Scripts\python.exe" check_environment.py
if errorlevel 1 goto partial
echo Instalacao concluida. Configure PASTA_CERTIFICADOS no .env.
pause
exit /b 0
:partial
echo Python instalado. Configuracao OCR incompleta: consulte as instrucoes acima e README.md.
pause
exit /b 1
:no_python
echo Instale Python 3.14 para Windows com o launcher py: https://www.python.org/downloads/windows/
pause
exit /b 2
:wrong_venv
echo A pasta .venv usa outra versao do Python. Renomeie-a e execute instalar.bat novamente.
pause
exit /b 2
:failed
echo Falha na instalacao. Verifique internet, permissoes e as mensagens acima.
pause
exit /b 2
