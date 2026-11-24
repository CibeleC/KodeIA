# Classificador de Mensagens de Clientes com IA

Sistema que recebe mensagens de clientes, usa um modelo de IA para identificar o assunto (dúvida, reclamação, solicitação, elogio ou outro) e a prioridade, e encaminha cada mensagem ao setor responsável por meio de um fluxo de automação no **n8n**.

**Sumário**

1. [Apresentação da Ideia](#1-apresentação-da-ideia)
2. [Problema Escolhido](#2-problema-escolhido)
3. [Solução Proposta](#3-solução-proposta)
4. [Tecnologias Utilizadas](#4-tecnologias-utilizadas)
5. [Funcionamento do Sistema](#5-funcionamento-do-sistema)
6. [Como Executar](#6-como-executar)
7. [Documentação do Fluxo de Automação (n8n)](#7-documentação-do-fluxo-de-automação-n8n)

---

## 1. Apresentação da Ideia

A ideia surgiu de uma situação comum no atendimento ao cliente: as mensagens chegam misturadas (um pedido de cancelamento, uma reclamação de atraso, uma pergunta sobre prazo) e alguém precisa ler cada uma para decidir quem deve responder. Esse trabalho é repetitivo e depende da leitura humana de todas as mensagens.

Pensei em usar um modelo de linguagem para fazer essa leitura inicial. Ele entende o texto livre do cliente, que é difícil de tratar com regras fixas como palavras-chave. O resultado volta em JSON, um formato que outros sistemas conseguem usar. A partir dele, uma ferramenta de automação decide o destino de cada mensagem.

## 2. Problema Escolhido

**Cenário:** uma empresa recebe mensagens de clientes com diferentes tipos de solicitação, mas não tem um processo organizado para identificar o assunto de cada uma.

**Consequências desse cenário:**
- reclamações urgentes ficam misturadas com dúvidas simples e demoram a ser atendidas;
- a triagem manual consome tempo da equipe;
- o encaminhamento depende de quem lê a mensagem, e por isso varia de pessoa para pessoa;
- não há dados organizados sobre quais assuntos mais aparecem.

**Objetivo:** classificar automaticamente cada mensagem em uma categoria e uma prioridade, e encaminhá-la ao setor correto, sem leitura manual.

## 3. Solução Proposta

A solução tem três partes que trabalham juntas:

1. **API (FastAPI):** recebe a mensagem e a envia a um modelo de IA com um prompt estruturado.
2. **IA:** lê a mensagem e devolve um JSON com `categoria`, `prioridade`, `confianca`, `resumo` e `justificativa`.
3. **Automação (n8n):** recebe a mensagem por um webhook, chama a API, direciona o resultado conforme a categoria e devolve a resposta final.

**Como a IA participa:** ela é o componente que interpreta o texto livre do cliente. Cabe a ela decidir a categoria e a prioridade, resumir a mensagem e justificar a decisão. As regras de negócio que vêm depois (qual setor recebe cada categoria, qual ação tomar) ficam no n8n, onde são fáceis de alterar sem mexer no código da IA.

| Categoria | Setor de destino | Ação sugerida |
|---|---|---|
| `reclamacao` | `suporte_nivel_2` | Abrir ticket prioritário e notificar o supervisor |
| `solicitacao` | `operacoes` | Criar chamado e confirmar o recebimento ao cliente |
| `duvida` | `atendimento_geral` | Enviar resposta da base de conhecimento |
| `elogio` e `outro` | `triagem_manual` | Encaminhar para análise humana |

## 4. Tecnologias Utilizadas

| Camada | Tecnologia | Uso no projeto |
|---|---|---|
| Linguagem | Python 3.12 | Código da API |
| API | FastAPI e Uvicorn | Endpoints REST e servidor |
| Validação | Pydantic | Valida a entrada e o JSON devolvido pela IA |
| IA | Groq, modelo `openai/gpt-oss-20b`, acessado pelo SDK `openai` | Classificação das mensagens. Qualquer endpoint compatível com a API da OpenAI funciona |
| Automação | n8n (n8n Cloud) | Webhook, roteamento por categoria e resposta |
| Hospedagem da API | Render (plano gratuito) | Torna a API acessível ao n8n Cloud |
| Interface | HTML, CSS e JavaScript puros | Página simples para testar a classificação |
| Documentação da API | Swagger UI (servido localmente) | Página `/docs` |
| Versionamento | Git e GitHub | Repositório do projeto |
| Opcional | Docker | Executar o n8n localmente |

## 5. Funcionamento do Sistema

### Visão geral

```
Cliente / Sistema ──POST──> n8n (Webhook) ──POST──> API FastAPI ──> Modelo de IA
                                 │                        │
                                 │<──── JSON classificado─┘
                                 ├─ Switch por categoria
                                 │    ├─ reclamacao  -> suporte_nivel_2
                                 │    ├─ solicitacao -> operacoes
                                 │    ├─ duvida      -> atendimento_geral
                                 │    └─ outro       -> triagem_manual
                                 └─ Responde o JSON final ao chamador
```

### 5.1 Como a API recebe os dados

| Endpoint | Uso | Acesso |
|---|---|---|
| `POST /classificar` | Integração com o n8n | Exige o cabeçalho `X-API-Key` quando `API_TOKEN` está definido |
| `POST /classificar-web` | Usado pela página web | Aberto, com limite de 10 requisições por minuto por IP e 60 por minuto no total |
| `GET /health` | Verificação de funcionamento | Aberto |
| `GET /` | Interface web | Aberto |
| `GET /docs` | Documentação interativa (Swagger) | Aberto |

Corpo esperado:

```json
{ "mensagem": "Quero cancelar meu plano", "cliente": "Joao" }
```

A API valida a entrada: `mensagem` é obrigatória, com 3 a 4000 caracteres, e `cliente` é opcional. Entradas inválidas retornam 422.

### 5.2 Como a IA processa as informações

O prompt de sistema (em `app/classificador.py`) define:

- o papel da IA (triagem de atendimento);
- as categorias e as prioridades, com critérios claros para cada uma;
- uma regra de segurança: o texto do cliente é tratado como dado, nunca como instrução, o que reduz o risco de *prompt injection*;
- o formato de saída: um objeto JSON fixo, sem texto extra.

A chamada usa `temperature=0`, para respostas consistentes, e `response_format=json_object`. A resposta é validada com Pydantic: a categoria e a prioridade só aceitam valores permitidos, e `confianca` fica entre 0 e 1. Se a IA devolver algo fora do formato, a API responde 502 em vez de repassar dados inválidos.

Resposta da API:

```json
{
  "categoria": "reclamacao",
  "prioridade": "alta",
  "confianca": 0.95,
  "resumo": "Pedido atrasado há 10 dias sem retorno do atendimento.",
  "justificativa": "O cliente expressa insatisfação com atraso e falta de resposta.",
  "cliente": "Maria",
  "mensagem": "Meu pedido atrasou 10 dias e ninguem responde!"
}
```

### 5.3 Como a automação é executada

1. Um sistema ou pessoa envia `POST` com a mensagem ao **Webhook** do n8n.
2. O node **HTTP Request** repassa a mensagem à API (`/classificar`), com o token no cabeçalho.
3. A API consulta a IA e devolve o JSON classificado.
4. O node **Switch** lê o campo `categoria` e escolhe o ramo correspondente.
5. Um node **Edit Fields (Set)** acrescenta `setor_destino` e `acao`, mantendo os dados da classificação.
6. O node **Respond to Webhook** devolve o JSON final a quem enviou a mensagem.

Resposta final do fluxo:

```json
{
  "categoria": "solicitacao",
  "prioridade": "baixa",
  "confianca": 0.95,
  "resumo": "Cliente solicita cancelamento de plano",
  "justificativa": "O cliente pede a ação de cancelar o plano, sem urgência explícita.",
  "cliente": "Joao",
  "mensagem": "Quero cancelar meu plano",
  "setor_destino": "operacoes",
  "acao": "Criar chamado de solicitacao e confirmar recebimento ao cliente"
}
```

O detalhe de cada node e os prints estão na seção [7](#7-documentação-do-fluxo-de-automação-n8n).

### 5.4 Tratamento de erros

| Código | Causa |
|---|---|
| 401 | Token ausente ou inválido em `/classificar` |
| 422 | Corpo inválido (por exemplo, mensagem vazia) |
| 429 | Limite de requisições da página web excedido |
| 500 | `LLM_API_KEY` não configurada |
| 502 | Falha ao consultar a IA, ou resposta fora do formato esperado |

### 5.5 Estrutura do projeto

| Caminho | Descrição |
|---|---|
| `app/main.py` | API FastAPI: endpoints, token, limite de uso e `/docs` |
| `app/classificador.py` | Prompt estruturado, chamada à IA e validação do JSON |
| `app/static/index.html` | Interface web simples |
| `app/static/swagger/` | Arquivos do Swagger UI, para o `/docs` funcionar sem depender de CDN |
| `n8n/workflow.json` | Fluxo do n8n para importar |
| `render.yaml` | Configuração do deploy no Render |
| `docker-compose.yml` | Sobe o n8n localmente (opcional) |
| `requirements.txt` | Dependências Python |
| `.env.example` | Modelo das variáveis de ambiente |
| `docs/prints/` | Capturas de tela do fluxo (lista em `docs/prints/LEIA-ME.md`) |

## 6. Como Executar

### Pré-requisitos

- Python 3.12 ou superior
- Uma chave de API de um provedor de IA compatível com a API da OpenAI (Groq, OpenAI ou Gemini)
- Para a execução na nuvem: contas no GitHub, no Render e no n8n Cloud

### 6.1 Rodar a API localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # depois edite o .env e preencha LLM_API_KEY
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Variáveis do `.env`:

| Variável | Descrição |
|---|---|
| `LLM_API_KEY` | Chave do provedor de IA (obrigatória) |
| `LLM_BASE_URL` | Endpoint do provedor. Vazio usa a OpenAI |
| `LLM_MODEL` | Nome do modelo |
| `API_TOKEN` | Opcional. Se definido, `/classificar` exige o cabeçalho `X-API-Key` com este valor |

Exemplos de configuração:

| Provedor | `LLM_BASE_URL` | `LLM_MODEL` |
|---|---|---|
| Groq | `https://api.groq.com/openai/v1` | `openai/gpt-oss-20b` |
| OpenAI | *(vazio)* | `gpt-4o-mini` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.0-flash` |

Os nomes de modelo mudam com o tempo. Se der erro de modelo não encontrado, consulte a lista atual do provedor.

Depois de iniciar:

- Interface web: http://localhost:8000/
- Documentação interativa: http://localhost:8000/docs

Teste pela linha de comando:

```powershell
curl.exe -X POST http://localhost:8000/classificar -H "Content-Type: application/json" -d '{\"mensagem\": \"Meu pedido atrasou 10 dias e ninguem responde!\", \"cliente\": \"Maria\"}'
```

### 6.2 Rodar na nuvem (Render + n8n Cloud)

O n8n Cloud não enxerga o `localhost`, então a API precisa estar publicada. Esta forma não exige instalar nada.

1. **GitHub:** publique este repositório.
2. **Render** (https://render.com): *New > Blueprint* e escolha o repositório. O `render.yaml` cria o serviço. Preencha `LLM_API_KEY` quando pedido. O `API_TOKEN` é gerado automaticamente e fica em *Environment*.
3. Abra `https://SEU-APP.onrender.com/health` e confirme `{"status":"ok"}`. No plano gratuito, a primeira chamada após um período parado pode levar cerca de 1 minuto.
4. **n8n Cloud** (https://n8n.io): crie a conta e importe `n8n/workflow.json` em *Import from File*.
5. No node **Classificar na API (IA)**, troque a URL pelo endereço do Render e o valor de `X-API-Key` pelo `API_TOKEN`.
6. Ative o workflow (*Active*) e envie uma mensagem à *Production URL* do node **Webhook Mensagem**:

```powershell
curl.exe -X POST https://SEU-N8N.app.n8n.cloud/webhook/mensagem-cliente -H "Content-Type: application/json" -d '{\"mensagem\": \"Quero cancelar meu plano\", \"cliente\": \"Joao\"}'
```

Para testar sem ativar o workflow, clique em *Execute workflow* e use a *Test URL* (`/webhook-test/mensagem-cliente`).

### 6.3 Rodar o n8n localmente (opcional)

Alternativa ao n8n Cloud, com Docker:

```powershell
docker compose up -d
```

Abra http://localhost:5678, importe `n8n/workflow.json` e ajuste o node **Classificar na API (IA)**:

- URL `http://host.docker.internal:8000/classificar`, com a API rodando em `--host 0.0.0.0`;
- se a API estiver sem `API_TOKEN`, o cabeçalho `X-API-Key` pode ficar sem uso.

## Observações

- Nunca envie o `.env` ao GitHub. Ele está no `.gitignore`.
- O `API_TOKEN` e a `LLM_API_KEY` não devem aparecer em prints.

---

## 7. Documentação do Fluxo de Automação (n8n)

Os prints ficam em `docs/prints/`. Cada item abaixo indica o nome do arquivo esperado.

### 7.1 Fluxo completo

Visão geral dos 8 nodes conectados. A mensagem entra pelo Webhook, é classificada pela API com IA, roteada por categoria, enriquecida com setor e ação, e devolvida como resposta.

![Fluxo completo](docs/prints/01-fluxo-completo.png)

```
Webhook Mensagem -> Classificar na API (IA) -> Roteamento por Categoria
   |- reclamacao  -> Reclamacao - Suporte Nivel 2 --\
   |- solicitacao -> Solicitacao - Operacoes -------+-> Responder Webhook
   |- duvida      -> Duvida - Atendimento ----------|
   '- outro       -> Outro - Triagem Manual --------/
```

O arquivo `n8n/workflow.json` contém o fluxo exportado e pode ser importado em **Workflows > Import from File**.

### 7.2 Execução bem-sucedida

Execução concluída, com todos os nodes do caminho percorrido em verde. A aba **Executions** do n8n lista a execução com o status *Success*.

![Execução bem-sucedida](docs/prints/02-execucao-sucesso.png)

### 7.3 Configuração dos nodes

#### 7.3.1 Webhook Mensagem (`Webhook`)

Recebe a mensagem do cliente. É o ponto de entrada da automação.

| Campo | Valor |
|---|---|
| HTTP Method | `POST` |
| Path | `mensagem-cliente` |
| Respond | `Using 'Respond to Webhook' Node` |

Corpo esperado: `{"mensagem": "texto do cliente", "cliente": "Nome"}`.

![Node Webhook](docs/prints/03-node-webhook.png)

#### 7.3.2 Classificar na API (IA) (`HTTP Request`)

Integração entre o n8n e a API FastAPI. Envia a mensagem para o endpoint `/classificar`, que chama o modelo de IA (Groq) com o prompt estruturado e devolve o JSON classificado. Neste projeto a IA é consumida pela API, e o n8n a aciona por este node.

| Campo | Valor |
|---|---|
| Method | `POST` |
| URL | `https://SEU-APP.onrender.com/classificar` (endereço do Render) |
| Send Headers | ligado, `X-API-Key` = valor de `API_TOKEN` do Render |
| Send Body / Body Content Type | ligado, `JSON` |
| JSON Body | `{{ JSON.stringify({ mensagem: $json.body.mensagem, cliente: $json.body.cliente }) }}` |

![Node HTTP Request](docs/prints/04-node-http-request.png)

#### 7.3.3 Roteamento por Categoria (`Switch`)

Direciona a mensagem conforme o campo `categoria` retornado pela IA.

| Saída | Condição (`{{ $json.categoria }}` é igual a) |
|---|---|
| `reclamacao` | `reclamacao` |
| `solicitacao` | `solicitacao` |
| `duvida` | `duvida` |
| `outro` (fallback) | qualquer outro valor, inclusive `elogio` |

![Node Switch](docs/prints/05-node-switch.png)

#### 7.3.4 Nodes de destino (`Edit Fields / Set`)

Quatro nodes, um por saída do Switch. Cada um acrescenta `setor_destino` e `acao` e mantém os campos da classificação (*Include Other Input Fields* ligado).

| Node | `setor_destino` | `acao` |
|---|---|---|
| Reclamacao - Suporte Nivel 2 | `suporte_nivel_2` | Abrir ticket prioritario e notificar o supervisor |
| Solicitacao - Operacoes | `operacoes` | Criar chamado de solicitacao e confirmar recebimento ao cliente |
| Duvida - Atendimento | `atendimento_geral` | Enviar resposta da base de conhecimento |
| Outro - Triagem Manual | `triagem_manual` | Encaminhar para analise humana |

![Set - Reclamação](docs/prints/06-node-set-reclamacao.png)
![Set - Solicitação](docs/prints/07-node-set-solicitacao.png)
![Set - Dúvida](docs/prints/08-node-set-duvida.png)
![Set - Outro](docs/prints/09-node-set-outro.png)

#### 7.3.5 Responder Webhook (`Respond to Webhook`)

Devolve ao chamador o JSON final.

| Campo | Valor |
|---|---|
| Respond With | `JSON` |
| Response Body | `{{ $json }}` |

![Node Respond to Webhook](docs/prints/10-node-responder-webhook.png)

### 7.4 Resultados: dados em cada etapa

Exemplo com a mensagem `{"mensagem": "Quero cancelar meu plano", "cliente": "Joao"}`. Os prints mostram a aba **Output** de cada node, na execução.

**Saída do Webhook.** O n8n entrega a requisição com a mensagem em `body`.

```json
{ "body": { "mensagem": "Quero cancelar meu plano", "cliente": "Joao" } }
```
![Saída do Webhook](docs/prints/11-saida-webhook.png)

**Saída do HTTP Request.** Resposta da API com a classificação feita pela IA.

```json
{
  "categoria": "solicitacao",
  "prioridade": "baixa",
  "confianca": 0.95,
  "resumo": "Cliente solicita cancelamento de plano",
  "justificativa": "O cliente pede a ação de cancelar o plano, sem urgência explícita.",
  "cliente": "Joao",
  "mensagem": "Quero cancelar meu plano"
}
```
![Saída do HTTP Request](docs/prints/12-saida-http-request.png)

**Saída do Switch.** A mensagem sai pela ramificação `solicitacao`.

![Saída do Switch](docs/prints/13-saida-switch.png)

**Saída do node Set.** Os campos de destino foram acrescentados.

```json
{
  "categoria": "solicitacao",
  "prioridade": "baixa",
  "confianca": 0.95,
  "resumo": "Cliente solicita cancelamento de plano",
  "justificativa": "O cliente pede a ação de cancelar o plano, sem urgência explícita.",
  "cliente": "Joao",
  "mensagem": "Quero cancelar meu plano",
  "setor_destino": "operacoes",
  "acao": "Criar chamado de solicitacao e confirmar recebimento ao cliente"
}
```
![Saída do Set](docs/prints/14-saida-set.png)

**Resposta final ao chamador** (curl, Postman ou outro sistema):

![Resposta final](docs/prints/15-resposta-final.png)

### 7.5 Outras evidências

![Interface web](docs/prints/16-interface-web.png)
![Documentação interativa (Swagger)](docs/prints/17-swagger.png)
