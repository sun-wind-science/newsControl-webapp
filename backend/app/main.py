from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.session import Base, engine
from app.models import *  # noqa: F401,F403

app = FastAPI(title="个人内容消化平台 API", version="0.1.0")

settings = get_settings()
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    # 本地 MVP 自动建表，正式环境仍使用 Alembic 管理迁移。
    Base.metadata.create_all(bind=engine)


app.include_router(router)
