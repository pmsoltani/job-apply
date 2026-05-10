import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api import api_router
from src.configs import c
from src.utils import start_tunnel


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tunnel_name = c.CLOUDFLARE_TUNNEL
    proc = await start_tunnel(tunnel_name, logger) if tunnel_name else None
    yield
    if proc:
        proc.terminate()
        await asyncio.to_thread(proc.wait)
        logger.info("Cloudflare tunnel stopped: '%s'", tunnel_name)


app = FastAPI(
    title=c.APP_NAME,
    version=c.APP_VERSION,
    description=c.APP_DESCRIPTION,
    lifespan=lifespan,
)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    reload = c.APP_ENV == "dev"
    uvicorn.run("main:app", host=c.FASTAPI_HOST, port=c.FASTAPI_PORT, reload=reload)
