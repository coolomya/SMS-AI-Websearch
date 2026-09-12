from fastapi import FastAPI
from api.routes import router as api_router
from config.logging_config import setup_logging
from config.settings import settings

# Initialize logging before initializing app layers
setup_logging()

app = FastAPI(title=settings.APP_TITLE)

# Register high-level functional API routers cleanly
app.include_router(api_router, prefix="/api/v1")
