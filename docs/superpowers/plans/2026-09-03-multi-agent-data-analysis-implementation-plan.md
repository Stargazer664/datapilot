# 多 Agent PostgreSQL 数据分析 Web 应用实施计划

> **执行约束：** 严格按任务顺序实施。每个行为变更先写失败测试，再写最小实现，通过后重构并提交。不得跳过 PostgreSQL 只读权限和 SQL AST 安全检查。

**目标：** 交付一个本地单用户 Web MVP，使用户可连接 PostgreSQL，用自然语言查询数据，并通过多个 LangGraph Agent 获得 SQL、表格、分析结论和 Plotly 图表。

**架构：** React 前端通过 REST 与 SSE 调用 FastAPI；LangGraph 以结构化共享状态编排 Coordinator、Schema、SQL、Reviewer、Analysis、Visualization 六个 Agent；模型适配层统一接入 OpenAI、DeepSeek 和 Qwen；所有数据库查询必须经过 SQLGlot AST 校验和 PostgreSQL 只读事务。

**技术栈：** Python 3.12、FastAPI、Pydantic、LangGraph、SQLAlchemy、psycopg、SQLGlot、SQLite、React、TypeScript、Vite、Plotly.js、pytest、Vitest、Playwright、Docker Compose。

**设计依据：** `docs/superpowers/specs/2026-09-03-multi-agent-data-analysis-design.md`

---

## 任务 1：建立项目骨架和质量基线

**新增文件：**

- `backend/pyproject.toml`
- `backend/src/analytics_app/__init__.py`
- `backend/src/analytics_app/main.py`
- `backend/tests/test_health.py`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `.gitignore`
- `.env.example`

**步骤：**

1. 创建后端健康检查测试，断言 `GET /api/health` 返回 `{"status": "ok"}`。
2. 运行 `pytest backend/tests/test_health.py -q`，确认测试因应用尚不存在而失败。
3. 实现最小 FastAPI 应用和健康检查接口。
4. 再次运行测试并确认通过。
5. 创建前端测试，断言应用标题和聊天入口存在。
6. 运行 `npm test -- --run`，确认失败后实现最小 React 页面。
7. 配置 Ruff、mypy、ESLint、TypeScript 和 Vitest 基线。
8. 运行后端与前端静态检查及测试。
9. 提交：`chore: scaffold backend and frontend`

**验收命令：**

```text
cd backend && pytest -q && ruff check . && mypy src
cd frontend && npm test -- --run && npm run lint && npm run typecheck
```

## 任务 2：定义配置、领域模型和本地存储

**新增文件：**

- `backend/src/analytics_app/config.py`
- `backend/src/analytics_app/domain/models.py`
- `backend/src/analytics_app/storage/database.py`
- `backend/src/analytics_app/storage/repositories.py`
- `backend/tests/config/test_settings.py`
- `backend/tests/storage/test_repositories.py`

**步骤：**

1. 为 PostgreSQL 配置、三家模型配置、查询限制和密钥脱敏编写失败测试。
2. 定义 Pydantic 配置模型，禁止 API 返回完整密钥。
3. 为会话、消息、请求轨迹和审计记录编写仓储测试。
4. 实现 SQLite 表结构与仓储接口。
5. 明确 SQLite 不保存数据库密码、API Key 和完整查询结果。
6. 运行迁移初始化、仓储测试和类型检查。
7. 提交：`feat: add configuration and local storage models`

## 任务 3：实现统一模型适配层

**新增文件：**

- `backend/src/analytics_app/llm/base.py`
- `backend/src/analytics_app/llm/openai_compatible.py`
- `backend/src/analytics_app/llm/providers.py`
- `backend/src/analytics_app/llm/errors.py`
- `backend/tests/llm/test_provider_contract.py`
- `backend/tests/llm/test_openai.py`
- `backend/tests/llm/test_deepseek.py`
- `backend/tests/llm/test_qwen.py`

**步骤：**

1. 先定义 `LLMProvider` 契约测试：普通调用、流式调用、结构化输出、超时和错误归一化。
2. 使用 HTTP Mock 编写三家供应商的失败测试，不调用真实付费 API。
3. 实现 OpenAI 兼容基础客户端。
4. 实现 OpenAI、DeepSeek、Qwen 的默认地址、认证、模型参数和能力声明。
5. 对结构化输出执行 Pydantic 校验；不支持原生结构化输出时使用 JSON 文本降级路径。
6. 实现限流和临时网络错误的有限指数退避；禁止无提示地跨供应商切换。
7. 验证日志中不存在认证头或密钥。
8. 提交：`feat: add multi-provider llm adapter`

## 任务 4：实现 PostgreSQL 连接和 Schema 检索

**新增文件：**

- `backend/src/analytics_app/db/connection.py`
- `backend/src/analytics_app/db/schema_reader.py`
- `backend/src/analytics_app/db/schema_ranker.py`
- `backend/tests/db/test_connection.py`
- `backend/tests/db/test_schema_reader.py`
- `backend/tests/db/test_schema_ranker.py`
- `infra/postgres/init/001_schema.sql`
- `infra/postgres/init/002_seed.sql`

**步骤：**

1. 启动测试 PostgreSQL，创建客户、订单、订单明细、产品和区域示例表。
2. 编写连接测试和只读账户权限测试。
3. 实现连接池、连接测试和安全的错误脱敏。
4. 编写元数据读取测试，覆盖表、字段、类型、注释、主键和外键。
5. 实现允许访问的 Schema、表和字段过滤。
6. 编写关键词相关性排序测试并实现确定性 Schema 筛选。
7. 确认默认不读取或返回原始样本行。
8. 提交：`feat: add postgres schema discovery`

## 任务 5：实现 SQL 确定性安全检查器

**新增文件：**

- `backend/src/analytics_app/sql/policy.py`
- `backend/src/analytics_app/sql/validator.py`
- `backend/src/analytics_app/sql/rewriter.py`
- `backend/tests/sql/test_validator_allowed.py`
- `backend/tests/sql/test_validator_blocked.py`
- `backend/tests/sql/test_rewriter.py`

**步骤：**

1. 编写允许用例：单条 `SELECT`、只读 CTE、聚合、连接和子查询。
2. 编写拒绝用例：INSERT、UPDATE、DELETE、DDL、COPY、CALL、权限语句、事务语句、多语句和无法分类的 SQL。
3. 编写允许列表测试，覆盖 Schema、表和字段引用。
4. 使用 SQLGlot 解析 PostgreSQL 方言 AST，默认拒绝解析失败或未知节点。
5. 实现安全的外层行数限制包装，不修改查询语义。
6. 增加结果字节数限制配置。
7. 对绕过样例进行参数化回归测试。
8. 提交：`feat: enforce deterministic sql safety policy`

## 任务 6：实现只读查询执行器

**新增文件：**

- `backend/src/analytics_app/db/executor.py`
- `backend/src/analytics_app/domain/results.py`
- `backend/tests/db/test_executor.py`
- `backend/tests/db/test_executor_cancellation.py`

**步骤：**

1. 编写只读事务、`statement_timeout`、行数限制和结果大小限制测试。
2. 编写写入语句即使绕过上层仍因账户权限失败的集成测试。
3. 实现参数化只读执行器和稳定的结果模型。
4. 实现取消信号、连接清理和超时错误映射。
5. 确保数据库错误在进入模型或 API 响应前脱敏。
6. 提交：`feat: add cancellable readonly query executor`

## 任务 7：定义 Agent 状态和结构化输出

**新增文件：**

- `backend/src/analytics_app/agents/state.py`
- `backend/src/analytics_app/agents/contracts.py`
- `backend/src/analytics_app/agents/prompts.py`
- `backend/tests/agents/test_contracts.py`

**步骤：**

1. 为共享状态、分析计划、候选 SQL、审查结果、分析结果和图表建议编写 Schema 测试。
2. 定义所有节点输入输出，禁止使用无结构的任意字典跨节点传递。
3. 把提示词与节点逻辑分离，并为提示词建立版本标识。
4. 规定状态只保存原始数据和结构化产物，展示文本在输出阶段生成。
5. 提交：`feat: define agent state and contracts`

## 任务 8：实现 Coordinator 与 Schema Agent

**新增文件：**

- `backend/src/analytics_app/agents/coordinator.py`
- `backend/src/analytics_app/agents/schema_agent.py`
- `backend/tests/agents/test_coordinator.py`
- `backend/tests/agents/test_schema_agent.py`

**步骤：**

1. 使用固定模型响应编写意图分类、分析计划和澄清问题测试。
2. 实现 Coordinator，区分新查询、追问、非数据问题和歧义问题。
3. 编写相关 Schema 选择、允许列表和无匹配结果测试。
4. 实现 Schema Agent，只向模型提供筛选后的元数据。
5. 验证两个 Agent 均不能直接执行 SQL。
6. 提交：`feat: add coordinator and schema agents`

## 任务 9：实现 SQL Agent、Reviewer 和修复循环

**新增文件：**

- `backend/src/analytics_app/agents/sql_agent.py`
- `backend/src/analytics_app/agents/sql_reviewer.py`
- `backend/tests/agents/test_sql_agent.py`
- `backend/tests/agents/test_sql_reviewer.py`
- `backend/tests/agents/test_sql_repair.py`

**步骤：**

1. 编写候选 SQL 结构化输出测试。
2. 编写 Reviewer 对连接错误、聚合错误、遗漏过滤和时间粒度错误的测试。
3. 实现 SQL Agent 和 Reviewer。
4. 编写统一修复计数测试，确认所有失败类型合计最多修复两次。
5. 实现脱敏错误反馈，不向模型发送连接凭证或不相关 Schema。
6. 提交：`feat: add sql generation review and repair`

## 任务 10：实现分析与可视化 Agent

**新增文件：**

- `backend/src/analytics_app/agents/analysis_agent.py`
- `backend/src/analytics_app/agents/visualization_agent.py`
- `backend/src/analytics_app/charts/validator.py`
- `backend/tests/agents/test_analysis_agent.py`
- `backend/tests/agents/test_visualization_agent.py`
- `backend/tests/charts/test_validator.py`

**步骤：**

1. 编写事实、推断、数据不足和截断标记测试。
2. 实现结果摘要器，只向模型发送受限数据和程序统计。
3. 编写折线图、柱状图、散点图、指标卡和“不制图”选择测试。
4. 定义 Plotly 白名单 Schema，拒绝任意脚本、远程资源和未知属性。
5. 实现 Analysis 与 Visualization Agent。
6. 提交：`feat: add analysis and visualization agents`

## 任务 11：组装 LangGraph 工作流

**新增文件：**

- `backend/src/analytics_app/workflow/graph.py`
- `backend/src/analytics_app/workflow/routing.py`
- `backend/src/analytics_app/workflow/events.py`
- `backend/tests/workflow/test_happy_path.py`
- `backend/tests/workflow/test_clarification.py`
- `backend/tests/workflow/test_repair_limit.py`
- `backend/tests/workflow/test_provider_failure.py`

**步骤：**

1. 为正常流程编写端到端节点测试，确认节点顺序和最终状态。
2. 为歧义暂停、澄清后恢复编写测试。
3. 为 Reviewer 拒绝、AST 拒绝、数据库错误和两次修复上限编写测试。
4. 为模型错误、用户取消和数据不足编写测试。
5. 用 LangGraph 显式连接节点和条件边。
6. 为每个节点发出开始、完成、耗时和错误进度事件。
7. 验证不存在无上限循环。
8. 提交：`feat: orchestrate analytics workflow with langgraph`

## 任务 12：实现 FastAPI REST 与 SSE 接口

**新增文件：**

- `backend/src/analytics_app/api/settings.py`
- `backend/src/analytics_app/api/queries.py`
- `backend/src/analytics_app/api/sessions.py`
- `backend/src/analytics_app/api/exports.py`
- `backend/src/analytics_app/api/dependencies.py`
- `backend/tests/api/test_settings.py`
- `backend/tests/api/test_queries.py`
- `backend/tests/api/test_sse.py`
- `backend/tests/api/test_cancel.py`
- `backend/tests/api/test_export.py`

**步骤：**

1. 先为连接测试、模型配置验证、创建查询、取消、历史和 CSV 导出编写 API 测试。
2. 定义统一 Pydantic 请求、响应和错误格式。
3. 实现查询任务管理器和请求状态持久化。
4. 实现 SSE 进度流，定义事件类型和终止事件。
5. 实现取消接口并贯通 LangGraph 与 psycopg 取消逻辑。
6. 验证 API 响应和 SSE 事件均无密钥与未脱敏错误。
7. 提交：`feat: expose workflow through rest and sse`

## 任务 13：实现前端设置页

**新增文件：**

- `frontend/src/api/client.ts`
- `frontend/src/types/api.ts`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/components/settings/DatabaseForm.tsx`
- `frontend/src/components/settings/ProviderForm.tsx`
- `frontend/src/components/settings/SafetyLimitsForm.tsx`
- `frontend/src/pages/SettingsPage.test.tsx`

**步骤：**

1. 编写数据库连接配置、三家模型配置和安全限制的组件测试。
2. 实现表单校验、保存状态和连接测试反馈。
3. 密钥字段只展示“已配置”，不得从后端回显完整值。
4. 实现默认供应商和模型选择。
5. 运行可访问性基础检查和键盘操作测试。
6. 提交：`feat: add local connection settings ui`

## 任务 14：实现聊天、结果与执行轨迹界面

**新增文件：**

- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/hooks/useQueryStream.ts`
- `frontend/src/components/chat/Composer.tsx`
- `frontend/src/components/chat/AgentProgress.tsx`
- `frontend/src/components/results/AnswerCard.tsx`
- `frontend/src/components/results/SqlPanel.tsx`
- `frontend/src/components/results/ResultTable.tsx`
- `frontend/src/components/results/PlotlyChart.tsx`
- `frontend/src/components/results/TracePanel.tsx`
- `frontend/src/pages/ChatPage.test.tsx`

**步骤：**

1. 编写提问、SSE 进度、停止任务和错误显示测试。
2. 实现聊天输入、模型选择和多轮消息。
3. 实现逐 Agent 状态、耗时和可展开轨迹。
4. 实现结论卡、可折叠 SQL、复制按钮和分页表格。
5. 实现经过 Schema 验证的 Plotly 图表渲染。
6. 实现 CSV 导出、重新运行和切换模型重新分析。
7. 提交：`feat: add conversational analytics interface`

## 任务 15：建立示例评测与真实供应商冒烟测试

**新增文件：**

- `backend/evals/cases.yaml`
- `backend/evals/run_eval.py`
- `backend/evals/scorers.py`
- `backend/tests/evals/test_scorers.py`
- `scripts/smoke_providers.ps1`

**步骤：**

1. 编写评测评分器测试：执行成功、结果值正确、修复次数、调用次数和耗时。
2. 创建覆盖筛选、聚合、连接、趋势、Top N、同比环比、空值、歧义和恶意请求的固定问题集。
3. 实现离线 Mock 评测，确保 CI 不依赖付费 API。
4. 实现显式启用的真实 API 冒烟脚本；缺少密钥时跳过，不失败。
5. 对 OpenAI、DeepSeek、Qwen 各运行至少一个结构化输出和一个完整查询流程冒烟测试。
6. 生成机器可读 JSON 与人类可读 Markdown 评测摘要。
7. 提交：`test: add analytics evaluation suite`

## 任务 16：容器化、文档和最终端到端验收

**新增文件：**

- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `README.md`
- `docs/security.md`
- `frontend/e2e/query-flow.spec.ts`

**步骤：**

1. 编写 Playwright 测试：配置连接、提问、观察 Agent 进度、查看 SQL/表格/图表、导出 CSV、停止请求。
2. 实现 Docker Compose，包含后端、前端和可选示例 PostgreSQL。
3. 编写本地非容器启动说明和 Docker 启动说明。
4. 编写只读数据库账户创建指南、数据外发说明和威胁边界。
5. 运行完整后端、前端、集成和端到端测试。
6. 检查 `.env`、日志、测试快照和 Git 历史中不存在密钥。
7. 从全新目录按 README 完成一次冷启动验收。
8. 提交：`docs: add deployment security and usage guide`

---

## 最终验证清单

按顺序执行并保存结果：

```text
cd backend
pytest -q
ruff check .
mypy src

cd ../frontend
npm test -- --run
npm run lint
npm run typecheck
npm run build
npx playwright test

cd ..
docker compose config
docker compose up --build
```

手动验证：

1. 分别配置 OpenAI、DeepSeek 和 Qwen，完成同一条查询。
2. 请求删除或更新数据，确认在执行前被拒绝。
3. 运行一个故意超时的查询，确认连接被释放且界面显示安全错误。
4. 发起查询后点击停止，确认后端和 PostgreSQL 查询均被取消。
5. 连续追问“按月份拆分”和“只看华东地区”，确认上下文正确继承。
6. 检查最终结果中包含结论、SQL、表格和适用图表。
7. 检查日志和 SQLite，确认无 API Key、数据库密码或完整敏感结果。

## 完成定义

- 设计规格中的九项成功标准全部有自动化或明确的手动验收证据。
- 所有测试和静态检查通过。
- 三家模型供应商均通过显式启用的冒烟测试。
- PostgreSQL 只读权限与程序侧安全检查均独立生效。
- README 能指导新用户在本地成功启动并完成首次查询。
- 工作区无密钥、构建产物或不必要的大型数据文件被提交。
