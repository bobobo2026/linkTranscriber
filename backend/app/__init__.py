from fastapi import FastAPI
from app.utils.logger import get_logger

logger = get_logger(__name__)

OPENAPI_TAGS = [
    {
        "name": "Service API",
        "description": "面向 linkTranscriber 服务化调用的核心接口，覆盖链接转写任务和大模型总结。",
    }
]

OPENAPI_SERVERS = [
    {"url": "http://127.0.0.1:8483", "description": "本地开发环境"},
    {"url": "/", "description": "部署环境基址（示例，请按实际部署环境替换）"},
]


def create_app(lifespan) -> FastAPI:
    from .routers import note, provider, model, config, service_api

    app = FastAPI(
        title="linkTranscriber",
        description=(
            "linkTranscriber 是一个基于 BiliNote 迭代的服务化后端，"
            "当前聚焦于短链接内容转写和大模型总结能力。"
        ),
        version="1.0.0",
        contact={
            "name": "linkTranscriber",
            "url": "https://github.com/bobobo2026/linkTranscriber",
        },
        openapi_tags=OPENAPI_TAGS,
        servers=OPENAPI_SERVERS,
        lifespan=lifespan,
    )
    app.include_router(note.router, prefix="/api")
    app.include_router(provider.router, prefix="/api")
    app.include_router(model.router, prefix="/api")
    app.include_router(config.router, prefix="/api")
    app.include_router(service_api.router, prefix="/api")

    try:
        from .routers import chat
        app.include_router(chat.router, prefix="/api")
    except ImportError as exc:
        logger.warning(f"聊天路由未加载：{exc}")

    return app
