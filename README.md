# 个人内容消化平台 MVP

这是一个本地运行的动态 Web App，不是官网页。它围绕“资源采集 → Inbox 单卡快判 → 任务化处理 → AI 草稿确认 → 复习/Anki/项目沉淀”的主流程搭建。

## 技术栈

- 前端：Next.js 14 App Router、Tailwind CSS、React Query、Zustand、lucide-react
- 后端：FastAPI、SQLAlchemy、Alembic
- 数据库：PostgreSQL
- 队列：Redis + Celery
- 文件存储：MinIO 本地服务预留
- 搜索：Meilisearch 服务预留，当前实现关键词搜索
- AI：OpenAI API 配置预留，MVP 内置本地 mock 摘要

## 快速启动

1. 复制环境变量：

```bash
cp .env.example .env
```

2. 启动基础设施：

```bash
docker compose up -d postgres redis minio meilisearch
```

3. 启动后端：

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:3000`。

## 已实现的 MVP 主路径

- 顶部全局采集栏：链接、文章片段、资源标题快速入库
- Dashboard：今日能量状态、任务统计、快捷入口
- Inbox：单卡三步快判，留下/删除、用途选择、处理时长确认
- 资源总库：按状态边线显示资源
- 处理台：锁定单任务，生成 AI 摘要草稿、生成 Anki 草稿、完成任务
- 项目空间：极简创建项目
- 复习页：主动复述与熟悉度记录
- 搜索页：关键词搜索资源和内容片段
- 后端统一返回格式：`{success, data, message}`
- Alembic 迁移入口与 `.env.example`

## 后续接入点

- 把 `/resources/{id}/summarize` 从 mock 替换为 OpenAI API 调用
- 把 `/uploads/file` 接到 MinIO，并对 PDF/视频做后台解析
- 把搜索写入 Meilisearch，实现全文索引和定位跳转
- 给浏览器插件或 PWA 添加快速采集入口
