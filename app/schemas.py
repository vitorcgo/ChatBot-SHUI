from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.config import LIMITE_CARACTERES_MENSAGEM

Sentimento = Literal["satisfeito", "neutro", "confuso", "frustrado", "irritado"]

Categoria = Literal[
    "pedido_entrega",
    "troca_devolucao",
    "tamanho_modelagem",
    "defeito_qualidade",
    "pagamento_reembolso",
    "cancelamento",
    "duvida_produto",
    "elogio",
    "fora_do_escopo",
    "outros",
]

Urgencia = Literal["baixa", "media", "alta"]

FalhaSimulada = Literal["timeout", "limite", "fora_do_ar", "json_invalido"]


class MensagemHistorico(BaseModel):
    papel: Literal["cliente", "atendente"]
    texto: str = Field(min_length=1, max_length=4000)


class RequisicaoChat(BaseModel):
    mensagem: str = Field(
        min_length=1,
        max_length=LIMITE_CARACTERES_MENSAGEM,
        description="Mensagem atual do cliente",
        examples=["Meu pedido 48213907 ainda não chegou e já faz 12 dias!"],
    )
    historico: list[MensagemHistorico] = Field(
        default_factory=list,
        max_length=50,
        description="Mensagens anteriores da conversa, da mais antiga para a mais recente",
    )

    @field_validator("mensagem")
    @classmethod
    def validar_mensagem(cls, valor):
        valor = valor.strip()
        if not valor:
            raise ValueError("a mensagem não pode estar vazia")
        return valor


class Analise(BaseModel):
    sentimento: Sentimento
    categoria: Categoria
    urgencia: Urgencia
    escalar_humano: bool
    motivo_escalonamento: str = Field(description="Frase curta com o motivo do encaminhamento, ou vazio")
    numero_pedido: str = Field(description="Número do pedido informado pelo cliente (só dígitos), ou vazio")
    produto: str = Field(description="Produto citado pelo cliente, ou vazio")
    tentativa_manipulacao: bool


class RespostaIA(Analise):
    resposta: str = Field(description="Texto que será mostrado ao cliente no chat")


class RespostaChat(BaseModel):
    resposta: str
    analise: Analise
    dados_mascarados: bool
    tempo_ms: int
    modelo: str


class RespostaErro(BaseModel):
    erro: str
    mensagem: str
    detalhes: list[str] = []
