from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, Resource, ResourceChunk, ReviewItem, User, UserSettings

LOCAL_USER_EMAIL = "local@content-digest.app"


def get_or_create_local_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == LOCAL_USER_EMAIL))
    if user:
        return user

    user = User(email=LOCAL_USER_EMAIL, username="我的内容工作台")
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id))
    db.add_all(
        [
            Project(user_id=user.id, name="理论物理期末复习", description="课程、视频、PDF 和 Anki 的沉淀空间"),
            Project(user_id=user.id, name="智能护膜答辩", description="论文、竞品、数据证据与答辩素材"),
        ]
    )

    resources = [
        Resource(
            user_id=user.id,
            title="非线性光学导论第 3 讲：二阶效应",
            type="video",
            source_platform="Bilibili",
            original_url="https://www.bilibili.com/video/example",
            summary="待判断的视频资源，适合拆成章节笔记、关键片段和 Anki。",
            duration=3600,
            heat_score=3.4,
        ),
        Resource(
            user_id=user.id,
            title="表面等离激元增强材料综述",
            type="pdf",
            source_platform="arXiv",
            original_url="https://arxiv.org/example",
            summary="科研文献，适合提取研究问题、方法、结论与证据等级。",
            word_count=8200,
            heat_score=4.1,
        ),
        Resource(
            user_id=user.id,
            title="ChatGPT 式学习工作流复盘",
            type="article",
            source_platform="网页",
            original_url="https://example.com/workflow",
            summary="文章资源，适合用七问模板整理成项目笔记。",
            word_count=2200,
            heat_score=2.1,
        ),
    ]
    db.add_all(resources)
    db.flush()
    for resource in resources:
        db.add(
            ResourceChunk(
                resource_id=resource.id,
                chunk_index=0,
                chunk_type="summary",
                content=resource.summary or resource.title,
                heading="初步摘要",
            )
        )
    db.commit()
    db.refresh(user)
    return user
