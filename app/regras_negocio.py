import re

PADRAO_CARTAO = re.compile(r"\b(?:\d[ .-]?){13,19}\b")
PADRAO_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


def mascarar_dados_sensiveis(texto):
    novo_texto = PADRAO_CARTAO.sub("[CARTÃO OCULTADO]", texto)
    novo_texto = PADRAO_CPF.sub("[CPF OCULTADO]", novo_texto)
    return novo_texto, novo_texto != texto


def somente_digitos(texto):
    return re.sub(r"\D", "", texto)


def aplicar_regras_negocio(resultado, textos_cliente):
    # a IA não pode "inventar" um número de pedido que o cliente não escreveu
    pedido = somente_digitos(resultado.numero_pedido)
    if pedido and not any(pedido in somente_digitos(texto) for texto in textos_cliente):
        pedido = ""
    resultado.numero_pedido = pedido

    if resultado.sentimento == "irritado" and resultado.urgencia == "alta":
        resultado.escalar_humano = True

    if resultado.escalar_humano and not resultado.motivo_escalonamento.strip():
        resultado.motivo_escalonamento = "Atendimento precisa de acompanhamento humano"

    if not resultado.escalar_humano:
        resultado.motivo_escalonamento = ""

    return resultado
