# K8s Agent Server

基于 agno + FastAPI 的 Kubernetes 智能运维服务。

## 功能

- 多 Agent K8s 诊断（总协调员 + 侦察员 + 分析师 + 操作方案顾问）
- 独立专家线程、共享证据转交、流式输出与 Markdown 渲染
- 定时巡检（集群健康检查 + 异常 Pod 日志分析，默认每 30 分钟）
- Web UI（侧栏多会话 + 巡检视图）
- SQLite 持久化巡检记录
- 15 个 kubectl 工具（get/describe/logs/top/scale/exec/health 分析等）

## 快速开始

```bash
cp .env.example .env
uv sync
uv run uvicorn k8s_agent.main:app --host 0.0.0.0 --port 7777
```

浏览器打开 http://localhost:7777

## 配置

见 `.env.example`，主要配置项：

| 配置项 | 说明 |
|--------|------|
| `LITELLM_MODEL_ID` | LiteLLM 模型 ID |
| `LITELLM_API_BASE` | LiteLLM 代理地址 |
| `INSPECTION_INTERVAL_MINUTES` | 巡检间隔（分钟） |
| `SQLITE_PATH` | SQLite 文件路径 |
| `LOG_LEVEL` | 日志级别 |
| `AGENT_DB_PATH` | agno 会话 DB 路径 |
| `AGENT_USER_ID` | 对话用的 user_id |
| `AGENT_HISTORY_MESSAGES` | 注入上下文的历史消息数 |
| `UPSTREAM_API_BASE_URL` | 前端代理连接的后端地址 |

## Docker

```bash
docker build -t k8s-agent-server .
docker run -p 7777:7777 -v $(pwd)/data:/app/data k8s-agent-server
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web UI |
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

```
src/k8s_agent/
├── main.py          # FastAPI 入口
├── core/            # 配置 + 日志
├── tools/           # K8s 工具（15 个 kubectl 工具）
├── agent.py         # Agent 定义
├── models/          # SQLite 巡检记录
├── services/        # 对话 + 巡检服务
├── api/             # HTTP 路由
└── scheduler.py     # 定时调度
```
