import os

from dotenv import load_dotenv

load_dotenv()


def ler_numero(nome, padrao):
    try:
        return float(os.getenv(nome, padrao))
    except ValueError:
        return float(padrao)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODELO = os.getenv("GEMINI_MODELO", "gemini-3.8-flash").strip()
GEMINI_MODELO_RESERVA = os.getenv("GEMINI_MODELO_RESERVA", "gemini-3.1-flash-lite").strip()
GEMINI_TIMEOUT = ler_numero("GEMINI_TIMEOUT", 25)
GEMINI_TIMEOUT_PRINCIPAL = ler_numero("GEMINI_TIMEOUT_PRINCIPAL", 15)

NOME_EMPRESA = os.getenv("NOME_EMPRESA", "SHUI").strip()

# valores aceitos: timeout, limite, fora_do_ar, json_invalido
SIMULAR_FALHA = os.getenv("SIMULAR_FALHA", "").strip().lower()

# libera o parametro ?simular= na rota /api/chat (usado nos testes da interface)
MODO_DEMONSTRACAO = os.getenv("MODO_DEMONSTRACAO", "false").strip().lower() in ("1", "true", "sim")
TIMEOUT_SIMULACAO = 8

LIMITE_REQUISICOES_POR_MINUTO = int(ler_numero("LIMITE_REQUISICOES_POR_MINUTO", 15))
LIMITE_CARACTERES_MENSAGEM = 1000
LIMITE_MENSAGENS_HISTORICO = 20
LIMITE_TAMANHO_REQUISICAO = 64 * 1024
