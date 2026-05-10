import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api import api_router
from src.configs import c
from src.logger import logger_factory
from src.utils import start_tunnel


lg = logger_factory(
    name=c.APP_NAME,
    log_file=c.BASE_DIR / "logs" / "app.log",
    logger_level=logging.DEBUG if c.APP_ENV == "dev" else logging.INFO,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
)
app.include_router(api_router, prefix=c.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    reload = c.APP_ENV == "dev"
    uvicorn.run("main:app", host=c.FASTAPI_HOST, port=c.FASTAPI_PORT, reload=reload)
