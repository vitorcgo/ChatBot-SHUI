<div align="center">

<img src="static/assets/shui-logo.webp" alt="Logo SHUI" width="110">

# SHUI · Atendimento com IA

**Chatbot de SAC que responde o cliente e analisa o atendimento em tempo real, integrado ao Google Gemini.**

![Python](https://img.shields.io/badge/Python-3.12+-111111?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-111111?style=flat-square&logo=fastapi&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-3.8_Flash-111111?style=flat-square&logo=googlegemini&logoColor=white)
![Categoria](https://img.shields.io/badge/categoria-Chatbot_+_Classificação-b3261e?style=flat-square)
![Licença](https://img.shields.io/badge/licença-MIT-111111?style=flat-square)

<img src="docs/prints/02-conversa-analise.png" alt="Chat com o painel de análise do atendimento" width="920">

</div>

> **Aviso:** projeto acadêmico **inspirado** na marca SHUI, sem nenhum vínculo com a empresa. As políticas usadas pela IA (`app/base_conhecimento.md`) são fictícias e foram criadas para a demonstração.

---

## Sumário

1. [Sobre o projeto](#sobre-o-projeto)
2. [Telas](#telas)
3. [Como funciona](#como-funciona)
4. [Tecnologias](#tecnologias)
5. [Como rodar](#como-rodar)
6. [Variáveis de ambiente](#variáveis-de-ambiente)
7. [Rotas da API](#rotas-da-api)
8. [Erros e códigos HTTP](#erros-e-códigos-http)
9. [Resiliência](#resiliência)
10. [Engenharia de prompt](#engenharia-de-prompt)
11. [Segurança](#segurança)
12. [Estrutura de pastas](#estrutura-de-pastas)
13. [Integrantes](#integrantes)
14. [Licença](#licença)

---

## Sobre o projeto

### O problema

O SAC de uma loja online de roupas recebe todos os dias as mesmas dúvidas (prazo de entrega, troca, tamanho, pagamento) misturadas com clientes irritados que precisam de atenção imediata. Responder tudo manualmente é lento, e fica difícil saber **quem precisa de um atendente humano primeiro**.

### A solução

Um assistente virtual que, **em uma única chamada à IA**, faz duas coisas:

1. **Responde o cliente** usando somente as políticas da loja, sem inventar informações.
2. **Analisa o atendimento** para a equipe: sentimento, categoria, urgência, número do pedido, peça citada, se precisa de atendimento humano e se houve tentativa de manipulação da IA.

**Categorias do trabalho:** Chatbot / Assistente Virtual **+** Classificação / Análise.

### Principais funcionalidades

| Funcionalidade | Descrição |
|---|---|
| **Chat com histórico** | A IA lembra do que foi falado nas últimas 20 mensagens |
| **Análise em tempo real** | Sentimento (e sua evolução), categoria, urgência e encaminhamento |
| **Sem alucinação** | A IA só usa a base de conhecimento e não inventa pedidos, prazos ou cupons |
| **Proteção contra prompt injection** | Tentativas de manipular a IA são recusadas e sinalizadas |
| **Dados sensíveis ocultados** | Números de cartão e CPF são removidos antes de chegar na IA |
| **Modelo reserva** | Se o modelo principal cair ou demorar, outro modelo assume |
| **Testes de erro na interface** | Botões que disparam timeout, rate limit, IA fora do ar e mais |

---

## Telas

<table>
  <tr>
    <td width="50%"><img src="docs/prints/01-inicio.png" alt="Tela inicial"></td>
    <td width="50%"><img src="docs/prints/03-carregamento.png" alt="Feedback de carregamento"></td>
  </tr>
  <tr>
    <td><b>Tela inicial</b> com atalhos para as dúvidas mais comuns</td>
    <td><b>Carregamento:</b> balão "digitando", cronômetro e etapas da requisição</td>
  </tr>
  <tr>
    <td><img src="docs/prints/04-api-json.png" alt="Painel da API"></td>
    <td><img src="docs/prints/05-resiliencia-erro.png" alt="Painel de resiliência"></td>
  </tr>
  <tr>
    <td><b>Painel API:</b> rotas, status do servidor e o último JSON retornado</td>
    <td><b>Resiliência:</b> erro tratado no chat e botões para testar cada falha</td>
  </tr>
  <tr>
    <td><img src="docs/prints/07-swagger.png" alt="Swagger"></td>
    <td align="center"><img src="docs/prints/06-mobile.png" alt="Versão mobile" width="260"></td>
  </tr>
  <tr>
    <td><b>Swagger:</b> documentação interativa gerada pelo FastAPI</td>
    <td><b>Mobile:</b> layout responsivo</td>
  </tr>
</table>

### Painéis da gaveta lateral

À direita da tela há uma coluna de ícones redondos. Cada um abre um painel:

| Ícone | Painel | O que mostra |
|---|---|---|
| Atividade | **Análise** | Sentimento, categoria, urgência, encaminhamento, dados extraídos e alertas |
| Velocímetro | **Carregamento** | Cronômetro, etapas da requisição, tempo médio e gráfico das últimas chamadas |
| `< >` | **API** | Rotas, links do Swagger/ReDoc, status do servidor, último JSON e exemplo `curl` |
| Escudo | **Resiliência** | Proteções ativas, botões de teste de erro e registro de eventos |

---

## Como funciona

```mermaid
flowchart LR
    A[Cliente no navegador] -->|POST /api/chat| B[FastAPI]
    B --> C{Validação}
    C -->|dados inválidos| X[400 com mensagem legível]
    C --> D[Rate limit e ocultação<br>de cartão e CPF]
    D --> E[Monta o prompt<br>políticas + histórico + mensagem]
    E --> F[Gemini principal]
    F -->|503, 429, lento<br>ou JSON inválido| G[Gemini reserva]
    F --> H[Extrai e valida o JSON]
    G --> H
    H --> I[Regras de negócio]
    I --> J[Resposta + análise]
    J --> A
```

1. O navegador envia a mensagem e o histórico da conversa (a API não guarda estado).
2. A API valida os dados, aplica o limite de requisições e oculta dados sensíveis.
3. O prompt é montado com as políticas da loja, o histórico e a mensagem, cada um delimitado por tags.
4. O Gemini responde em **JSON seguindo um schema obrigatório**.
5. O JSON é validado campo a campo e passa pelas regras de negócio.
6. A interface mostra a resposta no chat e a análise no painel.

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| API | Python 3.12+ e FastAPI |
| Inteligência Artificial | Google Gemini (SDK `google-genai`) — `gemini-3.8-flash` e `gemini-3.1-flash-lite` como reserva |
| Validação | Pydantic |
| Frontend | HTML, CSS e JavaScript puro, com ícones SVG baseados no [Lucide](https://lucide.dev) |
| Documentação | Swagger e ReDoc gerados automaticamente pelo FastAPI |

---

## Como rodar

### Pré-requisitos

- [Python 3.12 ou superior](https://www.python.org/downloads/)
- Uma chave da API do Gemini, gerada gratuitamente em [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### 1. Baixar o projeto

```bash
git clone <url-do-repositorio>
cd <pasta-do-projeto>
```

### 2. Configurar a chave

Copie o arquivo de exemplo e coloque sua chave no `.env`:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

```env
GEMINI_API_KEY=cole_sua_chave_aqui
```

### 3. Iniciar

**Opção A: Windows com dois cliques**

Dê dois cliques no **`iniciar.bat`**. Ele cria o ambiente virtual (na primeira vez), instala as dependências, sobe a API e abre o navegador.

**Opção B: pelo terminal (qualquer sistema)**

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Acessar

| Endereço | O que é |
|---|---|
| http://localhost:8000 | Interface do chat |
| http://localhost:8000/docs | Swagger (documentação interativa) |
| http://localhost:8000/redoc | ReDoc (documentação em leitura) |

> **Atenção:** não abra o `index.html` pelo Live Server ou direto do arquivo.** A página precisa ser servida pela própria API, senão as rotas `/api/...` não existem e aparece "API offline". Deixe a janela do servidor aberta enquanto usa.

---

## Variáveis de ambiente

Todas ficam no arquivo `.env` (use o `.env.example` como modelo).

| Variável | Obrigatória | Padrão | Descrição |
|---|:---:|---|---|
| `GEMINI_API_KEY` | Sim | — | Chave da API do Google Gemini |
| `GEMINI_MODELO` | | `gemini-3.8-flash` | Modelo principal |
| `GEMINI_MODELO_RESERVA` | | `gemini-3.1-flash-lite` | Modelo usado na segunda tentativa quando o principal falha |
| `GEMINI_TIMEOUT` | | `25` | Tempo máximo total de espera pela IA, em segundos |
| `GEMINI_TIMEOUT_PRINCIPAL` | | `15` | Tempo máximo do modelo principal antes de passar para o reserva |
| `NOME_EMPRESA` | | `SHUI` | Nome exibido na interface e usado no prompt |
| `LIMITE_REQUISICOES_POR_MINUTO` | | `15` | Mensagens permitidas por IP a cada minuto |
| `MODO_DEMONSTRACAO` | | `false` | Libera o parâmetro `?simular=` e os botões de teste de erro |
| `SIMULAR_FALHA` | | vazio | Força uma falha em todas as mensagens: `timeout`, `limite`, `fora_do_ar` ou `json_invalido` |

> Depois de alterar o `.env`, reinicie o servidor.

---

## Rotas da API

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/chat` | Envia a mensagem do cliente e recebe a resposta e a análise da IA |
| `GET` | `/api/saude` | Verifica se a API está no ar e como a IA está configurada |
| `GET` | `/api/empresa` | Dados usados pela interface (nome, limite de caracteres e atalhos) |
| `GET` | `/docs` | Swagger |

### `POST /api/chat`

**Corpo da requisição**

```json
{
  "mensagem": "Meu pedido 58213907 ainda não chegou e já passou do prazo",
  "historico": [
    { "papel": "cliente", "texto": "Oi, tudo bem?" },
    { "papel": "atendente", "texto": "Olá! Como posso ajudar?" }
  ]
}
```

| Campo | Tipo | Regras |
|---|---|---|
| `mensagem` | texto | Obrigatório. De 1 a 1000 caracteres, não pode ser só espaços |
| `historico` | lista | Opcional. Até 50 itens (as 20 últimas mensagens são usadas). `papel` deve ser `cliente` ou `atendente` |
| `?simular=` | query | Opcional: `timeout`, `limite`, `fora_do_ar` ou `json_invalido`. Só funciona com `MODO_DEMONSTRACAO=true` |

**Resposta de sucesso (200)**

```json
{
  "resposta": "Sinto muito pelo atraso! Vou encaminhar seu pedido **58213907** para a equipe abrir um chamado com a transportadora...",
  "analise": {
    "sentimento": "frustrado",
    "categoria": "pedido_entrega",
    "urgencia": "alta",
    "escalar_humano": true,
    "motivo_escalonamento": "Pedido fora do prazo de entrega",
    "numero_pedido": "58213907",
    "produto": "",
    "tentativa_manipulacao": false
  },
  "dados_mascarados": false,
  "tempo_ms": 3240,
  "modelo": "gemini-3.8-flash"
}
```

| Campo da análise | Valores possíveis |
|---|---|
| `sentimento` | `satisfeito`, `neutro`, `confuso`, `frustrado`, `irritado` |
| `categoria` | `pedido_entrega`, `troca_devolucao`, `tamanho_modelagem`, `defeito_qualidade`, `pagamento_reembolso`, `cancelamento`, `duvida_produto`, `elogio`, `fora_do_escopo`, `outros` |
| `urgencia` | `baixa`, `media`, `alta` |
| `escalar_humano` | `true` quando o caso precisa de um atendente |
| `tentativa_manipulacao` | `true` quando o cliente tentou burlar as regras da IA |

**Exemplo com `curl`**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Quero trocar uma peça por outro tamanho", "historico": []}'
```

### `GET /api/saude`

```json
{
  "status": "ok",
  "ia_configurada": true,
  "modelo": "gemini-3.8-flash",
  "modelo_reserva": "gemini-3.1-flash-lite",
  "simulacao_falha": null,
  "modo_demonstracao": false,
  "timeout_segundos": 25,
  "timeout_principal_segundos": 15,
  "limite_por_minuto": 15
}
```

### `GET /api/empresa`

Retorna o nome da empresa, o limite de caracteres e os atalhos exibidos na tela inicial.

---

## Erros e códigos HTTP

O servidor **nunca "quebra"**: todo erro volta no mesmo formato, com uma mensagem legível em português.

```json
{
  "erro": "dados_invalidos",
  "mensagem": "Requisição inválida. mensagem: a mensagem não pode estar vazia",
  "detalhes": ["mensagem: a mensagem não pode estar vazia"]
}
```

| HTTP | `erro` | Quando acontece |
|---|---|---|
| 400 | `dados_invalidos` | Mensagem vazia, longa demais, tipo errado ou JSON malformado |
| 403 | `simulacao_desativada` | Uso de `?simular=` sem `MODO_DEMONSTRACAO=true` |
| 404 | `rota_nao_encontrada` | Rota inexistente |
| 405 | `metodo_nao_permitido` | Método HTTP errado (ex.: `GET /api/chat`) |
| 413 | `requisicao_muito_grande` | Corpo da requisição maior que 64 KB |
| 429 | `muitas_requisicoes` | O mesmo IP passou do limite de mensagens por minuto |
| 429 | `limite_ia_excedido` | O Gemini atingiu o limite de uso (nos dois modelos) |
| 500 | `chave_nao_configurada` | `GEMINI_API_KEY` não foi definida |
| 500 | `erro_configuracao_ia` | Chave ou nome de modelo inválido |
| 500 | `erro_interno` | Qualquer erro inesperado |
| 502 | `resposta_invalida_ia` | A IA respondeu fora do formato JSON (nos dois modelos) |
| 503 | `ia_indisponivel` | Gemini fora do ar ou sem conexão (nos dois modelos) |
| 504 | `tempo_esgotado` | Nenhum modelo respondeu dentro de `GEMINI_TIMEOUT` |

---

## Resiliência

| Situação | O que o sistema faz |
|---|---|
| **IA demora demais** | O modelo principal tem até 15 s. Depois disso o modelo reserva assume com o tempo restante. Se estourar 25 s no total, retorna **504**. |
| **IA fora do ar (503)** | Tenta de novo com o modelo reserva, que tem servidores separados. Se ele também falhar, retorna **503**. |
| **Rate limit da IA (429)** | Tenta com o modelo reserva, que tem cota separada. Se não der, retorna **429** com o cabeçalho `Retry-After`. |
| **Resposta sem JSON (502)** | Tenta com o modelo reserva. Se continuar inválida, retorna **502**. |
| **Excesso de mensagens** | Limite de 15 mensagens por minuto por IP, retorna **429**. |
| **Queda de conexão no navegador** | A interface mostra o erro no chat com o botão "Tentar novamente" e atualiza o status da API sozinha. |

### Como testar as falhas na prática

1. Coloque `MODO_DEMONSTRACAO=true` no `.env` e reinicie o servidor.
2. Abra o painel **Resiliência** (ícone do escudo).
3. Clique em qualquer botão: **504**, **429**, **503**, **502**, mensagem vazia, mensagem gigante, rota inexistente ou prompt injection.

O erro aparece no chat exatamente como o cliente veria. Na simulação de timeout o limite cai para 8 segundos para não travar a apresentação.

---

## Engenharia de prompt

O prompt fica em [`app/prompt.py`](app/prompt.py) e é dividido em blocos:

| Bloco | Função |
|---|---|
| **Papel** | Assistente de SAC de uma marca de streetwear, com a tarefa de responder e classificar |
| **Base de conhecimento** | As políticas de [`base_conhecimento.md`](app/base_conhecimento.md), entre `<base_conhecimento>`, como **única fonte de verdade** |
| **Regras de resposta** | Não inventar prazos, valores ou status de pedido; não prometer benefícios; tom, tamanho e formatação |
| **Anti-alucinação** | Se a informação não está na base, dizer que não tem essa informação. Informação ausente não vira "não fazemos" |
| **Segurança** | O conteúdo de `<historico>` e `<mensagem_cliente>` é tratado como dado, nunca como instrução |
| **Encaminhamento** | Critérios objetivos para chamar um humano (Procon, cobrança indevida, pedido atrasado...) |
| **Classificação** | Definição de cada sentimento, categoria e nível de urgência |
| **Formato de saída** | JSON com campos fixos |

### Como a resposta da IA é tratada

1. A chamada usa `response_mime_type="application/json"` e um **JSON Schema** gerado a partir do modelo Pydantic `RespostaIA`, então a IA é obrigada a seguir o formato.
2. A função `extrair_json` remove blocos de markdown e recorta apenas o objeto JSON do texto.
3. O Pydantic valida cada campo e os valores permitidos. Se algo vier errado, a chamada é repetida com o modelo reserva.
4. As **regras de negócio** ([`app/regras_negocio.py`](app/regras_negocio.py)) corrigem a IA quando necessário:
   - um número de pedido que o cliente não escreveu é descartado;
   - cliente irritado com urgência alta sempre vai para um humano.

---

## Segurança

- **Chave protegida:** a chave da API fica apenas no `.env`, que está no `.gitignore` e nunca vai para o repositório.
- **Validação de entrada:** tipo e tamanho de todos os campos, com limite de 64 KB por requisição.
- **Rate limit:** 15 mensagens por minuto por IP.
- **Dados sensíveis:** números de cartão e CPF são ocultados antes de serem enviados para a IA.
- **Prompt injection:** delimitadores e regras no prompt; tentativas são recusadas e marcadas na análise.
- **Erros sem detalhes internos:** o cliente recebe mensagens legíveis e os detalhes técnicos ficam só no log do servidor.

---

## Estrutura de pastas

```
├── app/
│   ├── main.py               # rotas, tratamento de erros, rate limit e limite de tamanho
│   ├── servico_ia.py         # chamada ao Gemini, timeout, modelo reserva e leitura do JSON
│   ├── prompt.py             # instrução de sistema e montagem do prompt
│   ├── base_conhecimento.md  # políticas da loja (única fonte de verdade da IA)
│   ├── regras_negocio.py     # ocultação de dados sensíveis e regras aplicadas depois da IA
│   ├── schemas.py            # modelos de entrada e saída (Pydantic)
│   └── config.py             # leitura das variáveis de ambiente
├── static/
│   ├── index.html            # interface
│   ├── style.css             # visual
│   ├── script.js             # lógica do chat e dos painéis
│   └── assets/               # logo e imagem de fundo
├── docs/prints/              # prints usados neste README
├── .env.example              # modelo das variáveis de ambiente
├── iniciar.bat               # inicia o projeto no Windows com dois cliques
├── LICENSE                   # licença MIT
└── requirements.txt          # dependências
```

---

## Integrantes

| Nome |
|---|
| Vitor Cavalcante Gomes |

---

## Licença

O código deste projeto está sob a licença [MIT](LICENSE).

A logo e a imagem de fundo em `static/assets/` pertencem à marca SHUI e **não** estão incluídas nessa licença. Elas foram usadas apenas para fins acadêmicos.

---

<div align="center">

<img src="static/assets/shui-logo.webp" alt="" width="40">

**Be like water.**

</div>
