# DataPilot 安全边界

DataPilot 只应用于获授权的 PostgreSQL 数据库。建议创建独立的 `analytics_reader` 账户，仅授予目标 Schema 的 `CONNECT`、`USAGE` 和 `SELECT` 权限，并启用 `default_transaction_read_only`。

程序会使用 SQLGlot 解析每一条候选 SQL，只接受单条只读查询，再以只读事务、语句超时、行数限制和结果大小限制执行。模型永远不能直接访问数据库连接或运行任意代码。

API Key 和数据库密码仅来自 `.env` 或当前后端进程内存，不写入 SQLite、审计日志或浏览器持久化存储。发送给模型的数据可能离开本机；配置第三方供应商前，应确认数据分类和供应商的数据处理条款。

该 MVP 不提供认证和多租户隔离，只应绑定本机或可信网络，不应直接暴露到公网。
