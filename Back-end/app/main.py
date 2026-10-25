import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.routes import approvals, arts, images, projects
from app.services.erros import ErroNegocio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cria Mais API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ErroNegocio)
async def tratar_erro_negocio(_: Request, exc: ErroNegocio):
    return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})


app.include_router(projects.router)
app.include_router(arts.router)
app.include_router(images.router)
app.include_router(approvals.router)


@app.get("/api")
def raiz():
    return {"status": "ok"}


@app.get("/api/saude")
async def saude():
    """Diz quais serviços de apoio estão no ar (nenhum deles derruba a API)."""
    import httpx

    async def ping(url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=4) as c:
                return (await c.get(url)).status_code < 500
        except Exception:
            return False

    return {
        "api": True,
        "languagetool": await ping(f"{settings.languagetool_url.rstrip('/')}/v2/languages"),
        "outpainting_ativo": settings.outpainting_ativo,
        "iopaint": (await ping(f"{settings.iopaint_url.rstrip('/')}/api/v1/server-config")
                    if settings.outpainting_ativo else None),
        "ocr_motor": settings.ocr_motor,
    }