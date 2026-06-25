from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.routes.chat import chat_router
from app.routes.health import health_router
from app.utils.logger import get_logger

logger = get_logger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(title="BigQuery AI Assistant")

    # Serve /static/* from app/static/
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )

    app.include_router(chat_router)
    app.include_router(health_router)

    # Serve the frontend at /
    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(Path(__file__).parent / "templates" / "index.html")

    logger.info("FastAPI app created")
    return app
