import logging
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config
from app.regras_negocio import aplicar_regras_negocio, mascarar_dados_sensiveis
from app.schemas import Analise, FalhaSimulada, MensagemHistorico, RequisicaoChat, RespostaChat, RespostaErro
from app.servico_ia import ErroIA, gerar_resposta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sac")

PASTA_STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="API de Atendimento com IA",
    description=(
        "Chatbot de SAC integrado ao Google Gemini. A cada mensagem, a IA responde ao cliente "
        "e classifica o atendimento (sentimento, categoria, urgência e necessidade de atendimento humano)."
    ),
    version="1.0.0",
)

ERROS_DOCUMENTADOS = {
    400: {"model": RespostaErro, "description": "Dados inválidos"},
    403: {"model": RespostaErro, "description": "Simulação de falhas desativada"},
    413: {"model": RespostaErro, "description": "Requisição grande demais"},
    429: {"model": RespostaErro, "description": "Limite de requisições atingido"},
    500: {"model": RespostaErro, "description": "Erro interno ou de configuração"},
    502: {"model": RespostaErro, "description": "A IA respondeu em formato inválido"},
    503: {"model": RespostaErro, "description": "IA fora do ar"},
    504: {"model": RespostaErro, "description": "A IA demorou demais"},
}

TRADUCOES_VALIDACAO = {
    "missing": "campo obrigatório não enviado",
    "string_too_short": "não pode estar vazio",
    "string_too_long": "texto muito longo (máximo de {max_length} caracteres)",
    "too_long": "lista muito longa (máximo de {max_length} itens)",
    "string_type": "deve ser um texto",
    "list_type": "deve ser uma lista",
    "literal_error": "valor inválido (permitidos: {expected})",
    "json_invalid": "o corpo da requisição não é um JSON válido",
    "model_attributes_type": "deve ser um objeto JSON",
}

acessos_por_ip = defaultdict(deque)


def resposta_erro(status, codigo, mensagem, detalhes=None, headers=None):
    return JSONResponse(
        status_code=status,
        content={"erro": codigo, "mensagem": mensagem, "detalhes": detalhes or []},
        headers=headers,
    )


def traduzir_erro_validacao(erro):
    campo = ".".join(str(parte) for parte in erro["loc"] if parte not in ("body", "query")) or "corpo"
    if erro["type"] == "json_invalid":
        campo = "corpo"
    contexto = erro.get("ctx", {})

    if erro["type"] == "value_error":
        texto = str(contexto.get("error", erro["msg"]))
    else:
        modelo = TRADUCOES_VALIDACAO.get(erro["type"], erro["msg"])
        try:
            texto = modelo.format(**contexto)
        except (KeyError, IndexError):
            texto = modelo

    return f"{campo}: {texto.replace(' or ', ' ou ')}"


def segundos_para_liberar(ip):
    agora = time.monotonic()
    acessos = acessos_por_ip[ip]

    while acessos and agora - acessos[0] > 60:
        acessos.popleft()

    if len(acessos) >= config.LIMITE_REQUISICOES_POR_MINUTO:
        return int(60 - (agora - acessos[0])) + 1

    acessos.append(agora)
    return 0


@app.middleware("http")
async def limitar_tamanho_requisicao(request: Request, call_next):
    tamanho = request.headers.get("content-length", "")
    if tamanho.isdigit() and int(tamanho) > config.LIMITE_TAMANHO_REQUISICAO:
        return resposta_erro(413, "requisicao_muito_grande", "A requisição enviada é grande demais.")
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def tratar_erro_validacao(request: Request, exc: RequestValidationError):
    detalhes = [traduzir_erro_validacao(erro) for erro in exc.errors()]
    return resposta_erro(400, "dados_invalidos", "Requisição inválida. " + "; ".join(detalhes), detalhes)


@app.exception_handler(StarletteHTTPException)
async def tratar_erro_http(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return resposta_erro(404, "rota_nao_encontrada", f"A rota {request.url.path} não existe. Veja as rotas disponíveis em /docs.")
    if exc.status_code == 405:
        return resposta_erro(405, "metodo_nao_permitido", f"O método {request.method} não é aceito em {request.url.path}.")
    return resposta_erro(exc.status_code, "erro_http", str(exc.detail))


@app.exception_handler(ErroIA)
async def tratar_erro_ia(request: Request, exc: ErroIA):
    headers = {"Retry-After": "30"} if exc.status_http == 429 else None
    return resposta_erro(exc.status_http, exc.codigo, exc.mensagem, headers=headers)


@app.exception_handler(Exception)
async def tratar_erro_inesperado(request: Request, exc: Exception):
    logger.exception("Erro inesperado em %s", request.url.path)
    return resposta_erro(500, "erro_interno", "Ocorreu um erro inesperado no servidor. Tente novamente.")


@app.get("/", include_in_schema=False)
async def pagina_inicial():
    return FileResponse(PASTA_STATIC / "index.html")


@app.get("/api/saude", tags=["Sistema"], summary="Verifica se a API está funcionando")
async def saude():
    return {
        "status": "ok",
        "ia_configurada": bool(config.GEMINI_API_KEY),
        "modelo": config.GEMINI_MODELO,
        "modelo_reserva": config.GEMINI_MODELO_RESERVA,
        "simulacao_falha": config.SIMULAR_FALHA or None,
        "modo_demonstracao": config.MODO_DEMONSTRACAO,
        "timeout_segundos": config.GEMINI_TIMEOUT,
        "timeout_principal_segundos": config.GEMINI_TIMEOUT_PRINCIPAL,
        "limite_por_minuto": config.LIMITE_REQUISICOES_POR_MINUTO,
    }


@app.get("/api/empresa", tags=["Atendimento"], summary="Informações da empresa usadas pela interface")
async def empresa():
    return {
        "nome": config.NOME_EMPRESA,
        "limite_caracteres": config.LIMITE_CARACTERES_MENSAGEM,
        "sugestoes": [
            {
                "titulo": "Rastrear pedido",
                "descricao": "Prazos, frete e entrega",
                "icone": "caminhao",
                "mensagem": "Meu pedido ainda não chegou, o que eu faço?",
            },
            {
                "titulo": "Trocas e devoluções",
                "descricao": "Prazos e como solicitar",
                "icone": "troca",
                "mensagem": "Quero trocar uma peça por outro tamanho",
            },
            {
                "titulo": "Guia de tamanhos",
                "descricao": "Modelagem boxy e oversized",
                "icone": "regua",
                "mensagem": "Como funciona o tamanho das peças oversized?",
            },
            {
                "titulo": "Pagamentos",
                "descricao": "Pix, cartão e reembolso",
                "icone": "cartao",
                "mensagem": "Quais são as formas de pagamento?",
            },
        ],
    }


@app.post(
    "/api/chat",
    response_model=RespostaChat,
    responses=ERROS_DOCUMENTADOS,
    tags=["Atendimento"],
    summary="Envia uma mensagem do cliente e recebe a resposta e a análise da IA",
)
async def chat(
    requisicao: RequisicaoChat,
    request: Request,
    simular: FalhaSimulada | None = Query(
        default=None,
        description="Simula uma falha da IA para demonstração. Só funciona com MODO_DEMONSTRACAO=true.",
    ),
):
    if simular and not config.MODO_DEMONSTRACAO:
        return resposta_erro(403, "simulacao_desativada", "A simulação de falhas está desativada neste servidor.")

    ip = request.client.host if request.client else "desconhecido"
    espera = segundos_para_liberar(ip)
    if espera:
        return resposta_erro(
            429,
            "muitas_requisicoes",
            f"Você enviou muitas mensagens em pouco tempo. Aguarde {espera} segundos.",
            headers={"Retry-After": str(espera)},
        )

    mensagem, dados_mascarados = mascarar_dados_sensiveis(requisicao.mensagem)
    historico = [
        MensagemHistorico(papel=item.papel, texto=mascarar_dados_sensiveis(item.texto)[0])
        for item in requisicao.historico[-config.LIMITE_MENSAGENS_HISTORICO:]
    ]

    inicio = time.perf_counter()
    resultado, modelo_usado = await gerar_resposta(mensagem, historico, simular)
    tempo_ms = int((time.perf_counter() - inicio) * 1000)

    textos_cliente = [item.texto for item in historico if item.papel == "cliente"] + [mensagem]
    resultado = aplicar_regras_negocio(resultado, textos_cliente)

    logger.info("Atendimento: categoria=%s sentimento=%s urgencia=%s tempo=%sms",
                resultado.categoria, resultado.sentimento, resultado.urgencia, tempo_ms)

    return RespostaChat(
        resposta=resultado.resposta,
        analise=Analise(**resultado.model_dump(exclude={"resposta"})),
        dados_mascarados=dados_mascarados,
        tempo_ms=tempo_ms,
        modelo=modelo_usado,
    )


app.mount("/static", StaticFiles(directory=PASTA_STATIC), name="static")
