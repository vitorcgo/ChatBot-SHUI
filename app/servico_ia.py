import asyncio
import json
import logging
import re
import time

import httpx
from google import genai
from google.genai import errors, types

from app import config
from app.prompt import INSTRUCAO_SISTEMA, montar_prompt_usuario
from app.schemas import RespostaIA

logger = logging.getLogger("sac.ia")

_cliente = None


class ErroIA(Exception):
    def __init__(self, status_http, codigo, mensagem):
        super().__init__(mensagem)
        self.status_http = status_http
        self.codigo = codigo
        self.mensagem = mensagem


def obter_cliente():
    global _cliente
    if not config.GEMINI_API_KEY:
        raise ErroIA(500, "chave_nao_configurada", "A chave da API do Gemini não está configurada no servidor.")
    if _cliente is None:
        _cliente = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
        )
    return _cliente


def extrair_json(texto):
    if not texto:
        raise ValueError("a IA retornou uma resposta vazia")

    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip()).strip()
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio == -1 or fim <= inicio:
        raise ValueError("nenhum JSON encontrado na resposta da IA")

    return json.loads(texto[inicio:fim + 1])


async def simular_falha(falha, limite_tempo):
    if falha == "timeout":
        await asyncio.sleep(limite_tempo + 5)
    elif falha == "limite":
        raise errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Simulação de rate limit"}})
    elif falha == "fora_do_ar":
        raise errors.ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "Simulação de serviço fora do ar"}})
    elif falha == "json_invalido":
        return "Claro! Aqui está a resposta que você pediu, mas sem JSON nenhum :)"
    return None


async def chamar_gemini(prompt_usuario, modelo, falha=None, limite_tempo=None):
    if falha:
        texto_simulado = await simular_falha(falha, limite_tempo)
        if texto_simulado is not None:
            return texto_simulado

    cliente = obter_cliente()
    resposta = await cliente.aio.models.generate_content(
        model=modelo,
        contents=prompt_usuario,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCAO_SISTEMA,
            response_mime_type="application/json",
            response_json_schema=RespostaIA.model_json_schema(),
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            max_output_tokens=4096,
        ),
    )
    return resposta.text


async def gerar_resposta(mensagem, historico, simular=None):
    prompt_usuario = montar_prompt_usuario(mensagem, historico)
    falha = simular or config.SIMULAR_FALHA
    limite_total = config.TIMEOUT_SIMULACAO if simular == "timeout" else config.GEMINI_TIMEOUT
    erro_tempo = ErroIA(504, "tempo_esgotado", f"A IA demorou mais de {limite_total:g} segundos para responder. Tente novamente em alguns instantes.")

    # a segunda tentativa usa o modelo reserva, que tem cota e servidores separados
    modelos = [config.GEMINI_MODELO, config.GEMINI_MODELO_RESERVA or config.GEMINI_MODELO]
    inicio = time.monotonic()
    ultimo_erro = None

    for tentativa, modelo in enumerate(modelos, start=1):
        restante = limite_total - (time.monotonic() - inicio)
        if tentativa > 1 and restante < 1:
            break

        ultima = tentativa == len(modelos)
        # o principal tem um limite menor para sobrar tempo para o reserva
        limite_tentativa = restante if ultima else min(restante, config.GEMINI_TIMEOUT_PRINCIPAL)

        try:
            texto = await asyncio.wait_for(chamar_gemini(prompt_usuario, modelo, falha, limite_total), timeout=limite_tentativa)
            dados = extrair_json(texto)
            return RespostaIA.model_validate(dados), modelo

        except (TimeoutError, httpx.TimeoutException):
            logger.warning("Timeout com %s depois de %.0fs (tentativa %s)", modelo, limite_tentativa, tentativa)
            ultimo_erro = erro_tempo

        except errors.APIError as erro:
            logger.warning("Erro da API do Gemini com %s (tentativa %s): %s", modelo, tentativa, erro)
            if erro.code == 429:
                ultimo_erro = ErroIA(429, "limite_ia_excedido", "O limite de uso da IA foi atingido. Aguarde alguns segundos e tente novamente.")
            elif erro.code in (400, 401, 403, 404):
                raise ErroIA(500, "erro_configuracao_ia", "O servidor não conseguiu usar a IA por um problema de configuração (chave ou modelo inválido).")
            else:
                ultimo_erro = ErroIA(503, "ia_indisponivel", "O serviço de IA está fora do ar no momento. Tente novamente em alguns minutos.")

        except httpx.HTTPError as erro:
            logger.warning("Falha de conexão com o Gemini (tentativa %s): %s", tentativa, erro)
            ultimo_erro = ErroIA(503, "ia_indisponivel", "Não foi possível se conectar ao serviço de IA. Tente novamente em alguns minutos.")

        except ValueError as erro:
            logger.warning("Resposta da IA fora do formato com %s (tentativa %s): %s", modelo, tentativa, erro)
            ultimo_erro = ErroIA(502, "resposta_invalida_ia", "A IA retornou uma resposta em formato inesperado. Tente enviar a mensagem novamente.")

        if not ultima:
            await asyncio.sleep(0.5)

    raise ultimo_erro or erro_tempo
