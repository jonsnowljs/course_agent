from fastapi import APIRouter, FastAPI

from app.api.routes import items, login, private, users, utils, converter, text_merger, documents, chat, notion
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(converter.router)
api_router.include_router(text_merger.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(notion.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)

def get_app() -> FastAPI:
    app = FastAPI()
    app.include_router(chat.router)
    app.include_router(documents.router)
    app.include_router(items.router)
    app.include_router(login.router)
    app.include_router(private.router)
    app.include_router(users.router)
    app.include_router(notion.router)
    return app
