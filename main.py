import logging

from fastapi import FastAPI

from src.api import api_router
from src.configs import c


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

app = FastAPI(
    title=c.APP_NAME,
    version=c.APP_VERSION,
    description=c.APP_DESCRIPTION,
)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    reload = c.APP_ENV == "dev"
    uvicorn.run("main:app", host=c.FASTAPI_HOST, port=c.FASTAPI_PORT, reload=reload)
