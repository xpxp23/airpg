# AI 叙事跑团游戏

**代号：Neverwinter Nights Async**

一款 AI 驱动的多人异步叙事跑团游戏。玩家上传故事文本，AI 担任主持人，多人在碎片化时间里协作冒险。

## 核心玩法

```
上传故事 → AI 解析场景/角色 → 邀请好友 → 轮流输入行动 → AI 生成叙事 → 协作推进 → 达成结局
```

- **异步游玩**：无需同时在线，有空就行动，推送通知提醒
- **AI 主持**：自动解析故事、评估行动、生成叙事、控制节奏
- **协作机制**：帮助队友缩短等待时间，强调团队合作
- **自由输入**：像跑团一样描述任何行动，AI 理解自然语言

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Next.js 14 + React + Tailwind CSS |
| 后端 | FastAPI + SQLAlchemy + Alembic |
| 数据库 | PostgreSQL 15 + Redis 7 |
| AI | OpenAI 兼容接口（支持任意模型/中转站） |

## 快速开始

### 1. 环境准备

- Docker & Docker Compose
- Node.js 18+
- Python 3.11+
- 一个 AI API Key（OpenAI / DeepSeek / 通义千问等均可）

### 2. 启动数据库

```bash
docker compose up -d
```

### 3. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env      # 编辑 .env 填入 AI API Key
uvicorn app.main:app --reload
```

后端运行在 `http://localhost:8000`，API 文档：`http://localhost:8000/docs`

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:3000`

## AI 模型配置

在 `.env` 中配置，支持任意 OpenAI 兼容 API：

```bash
AI_PROVIDER=openai
AI_API_KEY=your-api-key
AI_BASE_URL=https://api.openai.com/v1    # 替换为你的 API 地址
AI_MODEL_DEFAULT=gpt-4o-mini              # 低成本任务
AI_MODEL_PREMIUM=gpt-4o                   # 叙事生成
```

常见配置：

| 服务 | AI_BASE_URL | AI_MODEL_DEFAULT |
|------|-------------|------------------|
| OpenAI 官方 | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:7b` |

## 项目结构

```
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 入口
│   │   ├── config.py           # 配置
│   │   ├── models/             # 数据库模型
│   │   ├── schemas/            # 请求/响应模型
│   │   ├── routers/            # API 路由
│   │   └── services/           # 业务逻辑
│   └── workers/                # 延迟任务处理
├── frontend/                   # Next.js 前端
│   └── src/
│       ├── app/                # 页面
│       ├── components/         # 组件
│       ├── hooks/              # 状态管理
│       └── lib/                # API 客户端
├── docker-compose.yml          # 开发环境
└── .env.example                # 环境变量模板
```

## 核心 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/games` | 创建游戏 |
| POST | `/api/v1/games/{id}/join` | 加入游戏 |
| POST | `/api/v1/games/{id}/start` | 开始游戏 |
| POST | `/api/v1/games/{id}/actions` | 提交行动 |
| POST | `/api/v1/games/{id}/cooperation` | 发起协作 |
| GET | `/api/v1/games/{id}/events` | 获取事件流 |

## 部署

详见 [部署教程.md](部署教程.md)

## 许可证

MIT
