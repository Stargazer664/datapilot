# DataPilot

DataPilot 是一个本地运行的多 Agent PostgreSQL 数据分析 Web 应用。它把自然语言问题转换为经过双重审查的只读 SQL，并展示结论、结果表格和 Plotly 图表。

## 核心能力

- LangGraph 编排 Coordinator、Schema、SQL、Reviewer、Analysis、Visualization 六个 Agent
- OpenAI、DeepSeek、Qwen API 统一适配与界面切换
- SQLGlot AST 安全校验、PostgreSQL 只读事务、超时和结果限制
- Agent 执行进度 SSE、连续会话、任务取消和 CSV 导出
- API Key 和数据库密码不写入 SQLite 或浏览器持久化存储

## Docker 启动

```powershell
Copy-Item .env.example .env
docker compose up --build
```

浏览器访问 `http://localhost:18080`。示例 PostgreSQL 配置：

- 主机：`postgres`（从 Docker 前端访问）
- 端口：`5432`
- 数据库：`analytics_demo`
- 用户名：`analytics_reader`
- 密码：`reader_password`
- Schema：`public`

如果从主机上的本地前端连接，数据库主机填写 `localhost`。

## 本地开发

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn analytics_app.main:app --reload
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`，在设置页填写 PostgreSQL 连接和至少一家模型供应商。界面输入的密钥仅保存在当前后端进程内存；需要重启后保留时，请写入本地 `.env`，不要提交该文件。

## 测试

```powershell
cd backend
pytest -q
ruff check .
mypy src

cd ..\frontend
npm test -- --run
npm run typecheck
npm run build
npx playwright test
```

真实模型冒烟测试默认不会运行。先在应用中配置密钥并启动后端，再执行：

```powershell
.\scripts\smoke_providers.ps1
```

## API

FastAPI 文档位于 `http://localhost:8000/docs`。主要接口包括设置与连接测试、会话、异步查询、SSE 进度、取消和 CSV 导出。

## 安全说明

详细边界见 `docs/security.md`。本项目是单用户本地 MVP，不包含登录、多租户、云部署或写数据库能力，请勿直接暴露到公网。
