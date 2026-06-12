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

如果 `8000` 被旧进程占用，可以改用其他端口，例如：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

并在启动前端前设置：

```bash
$env:BACKEND_HOSTPORT="localhost:8001"
$env:SERVER_API_BASE_URL="http://localhost:8001"
```

4. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:3000`。

也可以用本仓库的本地脚本启动：

```powershell
.\scripts\start-local.ps1
```

当 8000 端口异常时：

```powershell
.\scripts\start-local.ps1 -BackendPort 8001
```

## 已实现的 MVP 主路径

- 统一采集入口：链接、文本、PDF、Word、TXT/Markdown、视频文件
- 链接采集：尝试抓取网页标题、站点名、描述和正文片段，失败时仍可手动确认
- 文件采集：PDF/Word/TXT/Markdown 提取文本，视频保存并在详情页播放
- 录入确认卡：补标题、保存原因、标签、预计处理时间、优先级，并直接快判
- Dashboard：今日入库、今日处理、待处理、复习、积压统计和快捷入口
- Inbox：单卡快判，留下并处理、只作参考、先批注、删除
- 资源库：按类型、状态、关键词筛选，卡片显示保存原因、标签、预计处理时间
- 资源详情：桌面三栏，移动端内容/批注/信息/输出 tabs，可编辑资源信息和批注
- 处理台：锁定单任务，阅读/观看资源，保存处理输出，完成后生成复习项
- 输出草稿：本地 mock 摘要草稿、Anki 草稿，默认需要人工确认
- 项目空间：极简创建项目
- 复习页：主动复述与熟悉度记录
- 搜索页：关键词搜索标题、保存原因、标签、正文片段和批注
- 后端统一返回格式：`{success, data, message}`
- Alembic 迁移入口与 `.env.example`

## 后续接入点

- 把 `/resources/{id}/summarize` 从 mock 替换为 OpenAI API 调用
- 把 `/uploads/file` 接到 MinIO，并对 PDF/视频做后台解析
- 把搜索写入 Meilisearch，实现全文索引和定位跳转
- 给浏览器插件或 PWA 添加快速采集入口
