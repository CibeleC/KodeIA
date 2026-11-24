# Classificador de Mensagens de Clientes com IA

Solução que recebe mensagens de clientes, usa um modelo de IA para classificá-las (dúvida, reclamação, solicitação, elogio ou outro) e roteia cada uma para o setor certo por meio de um fluxo de automação no **n8n**.

## Arquitetura

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

## Estrutura

| Caminho | Descrição |
|---|---|
| `app/main.py` | API FastAPI (`/classificar`, `/health`) |
| `app/static/index.html` | Interface web simples (HTML/CSS/JS puro) |
| `app/static/index.html` | Interface web simples (HTML/CSS/JS puro) |
| `app/classificador.py` | Prompt estruturado, chamada ao modelo e validação do JSON |
| `n8n/workflow.json` | Fluxo do n8n para importar |
| `docker-compose.yml` | Sobe o n8n localmente |
| `docs/prints/` | Capturas de tela do fluxo |

## Como executar

### 1. API

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # preencha LLM_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Interface web: http://localhost:8000/ (formulário para classificar mensagens e ver o resultado)

Interface web: http://localhost:8000/ (formulário para classificar mensagens e ver o resultado).

Documentação interativa: http://localhost:8000/docs

O código usa o SDK da OpenAI, então funciona com qualquer endpoint compatível. Configure no `.env`:

| Provedor | `LLM_BASE_URL` | `LLM_MODEL` (exemplo) |
|---|---|---|
| OpenAI | *(vazio)* | `gpt-4o-mini` |
| Groq | `https://api.groq.com/openai/v1` | `openai/gpt-oss-20b` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.0-flash` |

Teste direto na API:

```powershell
curl.exe -X POST http://localhost:8000/classificar -H "Content-Type: application/json" -d '{\"mensagem\": \"Meu pedido atrasou 10 dias e ninguem responde!\", \"cliente\": \"Maria\"}'
```

Resposta esperada:

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

### 2. n8n

```powershell
docker compose up -d
```

1. Abra http://localhost:5678 e crie a conta local.
2. Menu **Workflows > Import from file** e selecione `n8n/workflow.json`.
3. Ative o workflow (**Active**) ou use **Execute workflow** e o *Test URL*.
4. Envie uma mensagem ao webhook:

```powershell
curl.exe -X POST http://localhost:5678/webhook/mensagem-cliente -H "Content-Type: application/json" -d '{\"mensagem\": \"Quero cancelar meu plano\", \"cliente\": \"Joao\"}'
```

O n8n roda em Docker e acessa a API do seu computador por `host.docker.internal:8000`. Se o n8n rodar fora do Docker, troque a URL no nó **Classificar na API (IA)** por `http://localhost:8000/classificar`.

Resposta do fluxo (exemplo):

```json
{
  "categoria": "solicitacao",
  "prioridade": "media",
  "confianca": 0.93,
  "resumo": "Cliente pede cancelamento do plano.",
  "justificativa": "Há um pedido explícito de ação (cancelamento).",
  "cliente": "Joao",
  "mensagem": "Quero cancelar meu plano",
  "setor_destino": "operacoes",
  "acao": "Criar chamado de solicitacao e confirmar recebimento ao cliente"
}
```

## Execução na nuvem (sem instalar nada): Render + n8n Cloud

O n8n Cloud não enxerga o `localhost`, então a API é publicada no Render.

1. **GitHub:** publique este repositório.
2. **Render** (https://render.com): *New > Blueprint*, escolha o repositório. O arquivo `render.yaml` cria o serviço. Preencha `LLM_API_KEY` quando pedido. O `API_TOKEN` é gerado automaticamente (veja em *Environment*).
3. Teste `https://SEU-APP.onrender.com/health`. No plano gratuito, a primeira chamada após inatividade pode levar cerca de 1 minuto.
4. **n8n Cloud** (https://n8n.io): crie a conta, importe `n8n/workflow.json` e, no nó **Classificar na API (IA)**, troque a URL pelo endereço do Render e o valor de `X-API-Key` pelo `API_TOKEN`.
5. Ative o workflow e envie a requisição para a *Production URL* do webhook, exibida no nó **Webhook Mensagem**.

Com `API_TOKEN` definido, `/classificar` exige o cabeçalho `X-API-Key`. Sem ele, a API retorna 401. A interface web esconde o campo de token e o exibe apenas quando a API responde 401.

## Prompt

O prompt de sistema (em `app/classificador.py`) define:

- o papel (triagem de atendimento);
- categorias e prioridades com critérios claros;
- regra de segurança: a mensagem do cliente é tratada como dado, não como instrução (mitiga *prompt injection*);
- formato de saída JSON fixo.

A chamada usa `temperature=0` e `response_format=json_object`. A resposta é validada com Pydantic (categorias e prioridades restritas, `confianca` entre 0 e 1). Respostas inválidas geram erro HTTP 502.

## Tratamento de erros

| Código | Causa |
|---|---|
| 422 | Corpo inválido (ex.: mensagem vazia) |
| 500 | `LLM_API_KEY` não configurada |
| 502 | Falha no modelo ou resposta fora do formato |

## Evidências do fluxo

Capturas de tela em `docs/prints/`:

1. `01-workflow.png`: fluxo completo no editor do n8n
2. `02-execucao.png`: execução bem-sucedida, com os nós em verde
3. `03-requisicao-resposta.png`: requisição e resposta JSON via curl/Postman
4. `04-swagger.png`: API em `/docs`

![Workflow](docs/prints/01-workflow.png)
![Execução](docs/prints/02-execucao.png)
![Requisição e resposta](docs/prints/03-requisicao-resposta.png)
![Swagger](docs/prints/04-swagger.png)

## Segurança

- A chave da IA fica no `.env` (ignorado pelo Git).
- Entrada limitada a 4000 caracteres.
