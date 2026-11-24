"""API de classificação de mensagens de clientes."""
import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

from app.classificador import Classificacao, classificar_mensagem  # noqa: E402

logger = logging.getLogger("classificador")
PASTA_ESTATICA = Path(__file__).parent / "static"

app = FastAPI(
    title="Classificador de Mensagens de Clientes",
    description="Classifica mensagens em dúvida, reclamação, solicitação, elogio ou outro usando IA.",
    version="1.0.0",
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


@app.post("/classificar", response_model=RespostaClassificacao, dependencies=[Depends(exigir_token)])
def classificar(entrada: MensagemEntrada):
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
