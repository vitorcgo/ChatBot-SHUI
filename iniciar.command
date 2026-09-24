#!/bin/bash
cd "$(dirname "$0")"

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "A API ja esta rodando em outra janela. Abrindo o navegador..."
    open http://localhost:8000
    exit 0
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Criando ambiente virtual e instalando dependencias..."
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
fi

if [ ! -f ".env" ]; then
    echo
    echo "Arquivo .env nao encontrado."
    echo "Copie o .env.example para .env e coloque sua chave do Gemini."
    read -n 1 -s -r -p "Pressione qualquer tecla para sair..."
    exit 1
fi

echo
echo "Iniciando a API em http://localhost:8000"
echo "Deixe esta janela aberta. Para parar, aperte Ctrl + C."
echo

(sleep 3 && open http://localhost:8000) &
.venv/bin/python -m uvicorn app.main:app --reload
read -n 1 -s -r -p "Pressione qualquer tecla para sair..."
