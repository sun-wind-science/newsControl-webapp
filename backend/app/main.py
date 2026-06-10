from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.session import Base, engine
from app.models import *  # noqa: F401,F403

app = FastAPI(title="个人内容消化平台 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    # 本地 MVP 自动建表，正式环境仍使用 Alembic 管理迁移。
    Base.metadata.create_all(bind=engine)


app.include_router(router)
