# K8s Agent Server

基于 Vue 3、Vite、agno 和 FastAPI 的 Kubernetes 智能运维服务。前端与后端
独立安装、启动和构建。

## 功能

- 多 Agent K8s 诊断（总协调员 + 侦察员 + 分析师 + 操作方案顾问）
- 独立专家线程、共享证据转交、流式输出与 Markdown 渲染
- 定时巡检（集群健康检查 + 异常 Pod 日志分析，默认每 30 分钟）
- Vue 3 Web 控制台（侧栏多会话 + 多 Agent 工作区 + 巡检视图）
- SQLite 持久化巡检记录
- 15 个 kubectl 工具（get/describe/logs/top/scale/exec/health 分析等）

## 快速开始

### 1. 启动后端

在项目根目录执行：

```bash
cp .env.example .env
uv sync
uv run uvicorn k8s_agent.main:app --host 0.0.0.0 --port 7777
```

后端 API：http://127.0.0.1:7777

接口文档：http://127.0.0.1:7777/docs

### 2. 启动 Vue 前端

打开另一个终端，在项目根目录执行：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:7778 。Vite 会将 `/backend` 请求代理到本地
FastAPI `7777` 端口。

两个启动命令都需要保持运行。若从手机或其他电脑访问，请将 `127.0.0.1`
替换为运行前端这台机器的局域网 IP。

### 前端构建

```bash
cd frontend
npm run build
```

构建产物位于 `frontend/dist/`。独立部署时，可通过反向代理把 `/backend`
转发到 FastAPI，或在构建前设置 `VITE_API_BASE_URL` 为后端完整地址。

## 配置

见 `.env.example`，主要配置项：

| 配置项 | 说明 |
|--------|------|
| `LITELLM_MODEL_ID` | LiteLLM 模型 ID |
| `LITELLM_API_BASE` | LiteLLM 代理地址 |
| `CORS_ORIGINS` | 允许访问后端的前端 Origin，多个值用逗号分隔 |
| `INSPECTION_INTERVAL_MINUTES` | 巡检间隔（分钟） |
| `SQLITE_PATH` | SQLite 文件路径 |
| `LOG_LEVEL` | 日志级别 |
| `AGENT_DB_PATH` | agno 会话 DB 路径 |
| `AGENT_USER_ID` | 对话用的 user_id |
| `AGENT_HISTORY_MESSAGES` | 注入上下文的历史消息数 |
| `UPSTREAM_API_BASE_URL` | 前端代理连接的后端地址 |

前端配置见 `frontend/.env.example`：

| 配置项 | 说明 |
|--------|------|
| `VITE_API_BASE_URL` | 浏览器请求使用的 API 前缀或完整地址 |
| `VITE_DEV_BACKEND_URL` | Vite 开发代理连接的本地 FastAPI 地址 |

## Docker

```bash
docker build -t k8s-agent-server .
docker run -p 7777:7777 -v $(pwd)/data:/app/data k8s-agent-server
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 后端服务信息 |
| GET | `/health` | 健康检查 |
| POST | `/api/chat` | 流式对话（SSE） |
| GET | `/api/agents` | Agent 列表与权限 |
| POST | `/api/agents/{id}/chat` | 指定 Agent 的独立流式对话 |
| GET | `/api/conversations` | 会话历史列表 |
| GET | `/api/conversations/{id}` | 单个会话消息历史 |
| DELETE | `/api/conversations/{id}` | 删除会话 |
| GET | `/api/inspections` | 巡检历史列表 |
| GET | `/api/inspections/{id}` | 单条巡检详情 |
| POST | `/api/inspect` | 手动触发巡检 |

## 项目结构

```text
frontend/               # 独立 Vue 3 + Vite 前端
├── src/
│   ├── components/     # Vue UI 组件
│   ├── composables/    # 工作区状态与交互逻辑
│   ├── App.vue
│   └── main.js
├── package.json
└── vite.config.js

src/k8s_agent/          # 独立 FastAPI 后端
├── main.py             # FastAPI 入口
├── core/               # 配置 + 日志
├── tools/              # Kubernetes 工具
├── models/             # SQLite 巡检记录
├── services/           # 对话 + 巡检服务
├── api/                # HTTP 路由
└── scheduler.py        # 定时调度
```
