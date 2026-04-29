# AI 叙事跑团游戏

**代号：Neverwinter Nights Async**

一款 AI 驱动的多人异步叙事跑团游戏。玩家上传故事文本，AI 担任主持人，多人在碎片化时间里协作冒险。

仓库地址：https://github.com/xpxp23/airpg

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

### 方式一：云服务器部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/xpxp23/airpg.git /opt/airpg
cd /opt/airpg

# 2. 配置环境变量
cp .env.example .env
vim .env   # 填入 AI API Key、数据库密码等

# 3. 一键部署
chmod +x deploy.sh
./deploy.sh
```

部署完成后访问 `http://你的服务器IP` 即可。

> 详细部署指南见 [部署教程.md](部署教程.md)

### 方式二：本地开发

**前置条件：** Docker、Node.js 18+、Python 3.11+

```bash
# 1. 克隆项目
git clone https://github.com/xpxp23/airpg.git
cd airpg

# 2. 启动数据库
docker compose up -d

# 3. 启动后端
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env      # 编辑 .env 填入 AI API Key
uvicorn app.main:app --reload
```

后端运行在 `http://localhost:8000`，API 文档：`http://localhost:8000/docs`

```bash
# 4. 启动前端
cd ../frontend
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

| 服务 | AI_BASE_URL | AI_MODEL_DEFAULT | AI_MODEL_PREMIUM |
|------|-------------|------------------|------------------|
| OpenAI 官方 | `https://api.openai.com/v1` | `gpt-4o-mini` | `gpt-4o` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | `deepseek-chat` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` | `qwen-plus` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | `moonshot-v1-32k` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | `glm-4` |
| 零一万物 | `https://api.lingyiwanwu.com/v1` | `yi-lightning` | `yi-large` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:7b` | `qwen2.5:14b` |
| 本地 vLLM | `http://localhost:8000/v1` | 自选模型 | 自选模型 |

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
├── nginx/                      # Nginx 配置
├── docker-compose.yml          # 开发环境
├── docker-compose.prod.yml     # 生产环境
├── deploy.sh                   # 一键部署脚本
├── 部署教程.md                  # 完整部署指南
└── .env.example                # 环境变量模板
```

## 核心 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 登录 |
| GET  | `/api/v1/auth/me` | 当前用户信息 |
| POST | `/api/v1/games` | 创建游戏 |
| GET  | `/api/v1/games` | 游戏列表 |
| GET  | `/api/v1/games/{id}` | 游戏详情 |
| POST | `/api/v1/games/{id}/join` | 加入游戏 |
| POST | `/api/v1/games/{id}/start` | 开始游戏 |
| POST | `/api/v1/games/{id}/actions` | 提交行动 |
| POST | `/api/v1/games/{id}/cooperation` | 发起协作 |
| GET  | `/api/v1/games/{id}/events` | 获取事件流 |
| GET  | `/api/v1/games/{id}/characters` | 获取角色列表 |

## 部署

- **一键部署**：`chmod +x deploy.sh && ./deploy.sh`
- **完整指南**：[部署教程.md](部署教程.md)（含手动部署、HTTPS 配置、运维命令、常见问题）

## 许可证

MIT
