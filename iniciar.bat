@echo off
cd /d "%~dp0"

netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo A API ja esta rodando em outra janela. Abrindo o navegador...
    start "" http://localhost:8000
    exit /b
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual e instalando dependencias...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

if not exist ".env" (
    echo.
    echo Arquivo .env nao encontrado.
    echo Copie o .env.example para .env e coloque sua chave do Gemini.
    pause
    exit /b
)

echo.
echo Iniciando a API em http://localhost:8000
echo Deixe esta janela aberta. Para parar, aperte Ctrl + C.
echo.

start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://localhost:8000"
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
pause
