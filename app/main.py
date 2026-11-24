"""API de classificação de mensagens de clientes."""
import logging
import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

from app.classificador import Classificacao, classificar_mensagem  # noqa: E402

logger = logging.getLogger("classificador")
PASTA_ESTATICA = Path(__file__).parent / "static"

app = FastAPI(
    title="Classificador de Mensagens de Clientes",
    description="Classifica mensagens em dúvida, reclamação, solicitação, elogio ou outro usando IA.",
    version="1.0.0",
    docs_url=None,  # /docs é definido abaixo, com arquivos locais (sem depender de CDN)
    redoc_url=None,
)

app.mount("/swagger-static", StaticFiles(directory=PASTA_ESTATICA / "swagger"), name="swagger-static")


@app.get("/docs", include_in_schema=False)
def documentacao_interativa():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Documentação",
        swagger_js_url="/swagger-static/swagger-ui-bundle.js",
        swagger_css_url="/swagger-static/swagger-ui.css",
        swagger_favicon_url="data:,",
    )


class MensagemEntrada(BaseModel):
    mensagem: str = Field(min_length=3, max_length=4000, examples=["Meu pedido atrasou e ninguém responde!"])
    cliente: str | None = Field(default=None, examples=["Maria Silva"])


class RespostaClassificacao(Classificacao):
    cliente: str | None = None
    mensagem: str


def exigir_token(x_api_key: str | None = Header(default=None)):
    """Se API_TOKEN estiver definido, exige o mesmo valor no cabeçalho X-API-Key."""
    esperado = os.getenv("API_TOKEN")
    if not esperado:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, esperado):
        raise HTTPException(status_code=401, detail="Token inválido ou ausente (cabeçalho X-API-Key).")


@app.get("/", include_in_schema=False)
def pagina_inicial():
    return FileResponse(PASTA_ESTATICA / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


LIMITE_POR_IP = 10  # requisições por minuto, por IP (página web)
LIMITE_GLOBAL = 60  # requisições por minuto, somando todos (página web)
_janela_ip: dict[str, deque] = defaultdict(deque)
_janela_global: deque = deque()


def _limpar(janela: deque, agora: float) -> None:
    while janela and agora - janela[0] > 60:
        janela.popleft()


def limitar_pagina_web(request: Request):
    """Limite simples em memória para o endpoint público usado pela página web."""
    agora = time.monotonic()
    encaminhado = request.headers.get("x-forwarded-for", "")
    ip = encaminhado.split(",")[0].strip() or (request.client.host if request.client else "desconhecido")
    janela = _janela_ip[ip]
    _limpar(janela, agora)
    _limpar(_janela_global, agora)
    if len(janela) >= LIMITE_POR_IP or len(_janela_global) >= LIMITE_GLOBAL:
        raise HTTPException(status_code=429, detail="Muitas solicitações. Aguarde um minuto e tente de novo.")
    janela.append(agora)
    _janela_global.append(agora)


def _executar_classificacao(entrada: MensagemEntrada) -> RespostaClassificacao:
    try:
        resultado = classificar_mensagem(entrada.mensagem)
    except RuntimeError as erro:
        raise HTTPException(status_code=500, detail=str(erro))
    except (ValueError, ValidationError) as erro:
        logger.exception("Resposta inválida da IA")
        raise HTTPException(status_code=502, detail="A IA retornou uma resposta fora do formato esperado.") from erro
    except Exception as erro:
        logger.exception("Falha ao chamar a IA")
        raise HTTPException(status_code=502, detail="Falha ao consultar o modelo de IA.") from erro

    return RespostaClassificacao(**resultado.model_dump(), cliente=entrada.cliente, mensagem=entrada.mensagem)


@app.post("/classificar", response_model=RespostaClassificacao, dependencies=[Depends(exigir_token)])
def classificar(entrada: MensagemEntrada):
    """Endpoint para integrações (n8n). Exige X-API-Key quando API_TOKEN está definido."""
    return _executar_classificacao(entrada)


@app.post(
    "/classificar-web",
    response_model=RespostaClassificacao,
    dependencies=[Depends(limitar_pagina_web)],
    include_in_schema=False,
)
def classificar_web(entrada: MensagemEntrada):
    """Endpoint usado pela página web: sem token, com limite de requisições por minuto."""
    return _executar_classificacao(entrada)
