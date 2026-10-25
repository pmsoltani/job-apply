import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api.v1 import router as v1_router
from src.configs import c
from src.logger import logger_factory
from src.services import AirtableService
from src.utils import start_tunnel


lg = logger_factory(
    name=c.APP_NAME,
    log_file=c.LOG_FILE,
    logger_level=logging.DEBUG if c.APP_ENV == "dev" else logging.INFO,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await AirtableService().check_schema()
    tunnel_name = c.CLOUDFLARE_TUNNEL
    proc = await start_tunnel(tunnel_name, lg) if tunnel_name else None
    yield
    if proc:
        proc.terminate()
        await asyncio.to_thread(proc.wait)
        lg.info("Cloudflare tunnel stopped: '%s'", tunnel_name)


app = FastAPI(
    title=c.APP_NAME,
    version=c.APP_VERSION,
    description=c.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
app.include_router(v1_router, prefix=c.API_PREFIX)
app.mount("/static", StaticFiles(directory=c.STATIC_DIR), name="static")


@app.get("/docs", include_in_schema=False)
async def swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title}",
        swagger_favicon_url=str(app.url_path_for("static", path="logo.svg")),
    )


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


def run():
    import uvicorn

    reload = c.APP_ENV == "dev"
    host, port = c.FASTAPI_HOST, c.FASTAPI_PORT
    uvicorn.run("src.api.server:app", host=host, port=port, reload=reload)
