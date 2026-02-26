from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging
from app.routers.health import router as health_router
from app.routers.models import router as models_router

configure_logging()

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(health_router)
app.include_router(models_router)
