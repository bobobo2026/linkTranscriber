from fastapi import FastAPI
from app.utils.logger import get_logger

logger = get_logger(__name__)



def create_app(lifespan) -> FastAPI:
    from .routers import note, provider, model, config, service_api

    app = FastAPI(title="linkTranscriber",lifespan=lifespan)
    app.include_router(note.router, prefix="/api")
    app.include_router(provider.router, prefix="/api")
    app.include_router(model.router,prefix="/api")
    app.include_router(config.router,  prefix="/api")
    app.include_router(service_api.router, prefix="/api")

    try:
        from .routers import chat
        app.include_router(chat.router, prefix="/api")
    except ImportError as exc:
        logger.warning(f"聊天路由未加载：{exc}")

    return app
