from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph

from analytics_app.agents.nodes import (
    AnalysisAgent,
    CoordinatorAgent,
    SchemaAgent,
    SqlAgent,
    SqlReviewerAgent,
    VisualizationAgent,
)
from analytics_app.agents.state import AgentState
from analytics_app.db.executor import execute_readonly
from analytics_app.domain.models import DatabaseConfigInput
from analytics_app.llm.base import LLMProvider
from analytics_app.sql.validator import SqlSafetyError, validate_readonly_sql

ProgressCallback = Callable[[str, str, dict[str, Any]], Awaitable[None]]


class AnalyticsWorkflow:
    def __init__(
        self,
        llm: LLMProvider,
        database: DatabaseConfigInput,
        progress: ProgressCallback,
    ) -> None:
        self.database = database
        self.progress = progress
        self.coordinator = CoordinatorAgent(llm)
        self.schema_agent = SchemaAgent(database)
        self.sql_agent = SqlAgent(llm)
        self.reviewer = SqlReviewerAgent(llm)
        self.analysis_agent = AnalysisAgent(llm)
        self.visualization_agent = VisualizationAgent(llm)
        self.graph = self._build()

    async def _run_node(
        self,
        state: AgentState,
        name: str,
        operation: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        await self.progress("agent_started", name, {})
        started = time.perf_counter()
        try:
            result = await operation()
        except Exception as exc:
            await self.progress("agent_failed", name, {"error": str(exc)})
            raise
        await self.progress(
            "agent_completed",
            name,
            {"duration_ms": round((time.perf_counter() - started) * 1000)},
        )
        return result

    def _build(self) -> Any:
        builder = StateGraph(AgentState)

        async def coordinator(state: AgentState) -> dict[str, Any]:
            async def operation() -> dict[str, Any]:
                plan = await self.coordinator.run(state["question"], state.get("history", []))
                return {"plan": plan, "status": plan.intent}

            return await self._run_node(state, "coordinator", operation)

        async def schema(state: AgentState) -> dict[str, Any]:
            async def operation() -> dict[str, Any]:
                relevant = await self.schema_agent.run(state["question"])
                if not relevant:
                    raise RuntimeError("未找到可用于回答问题的数据表")
                return {"schema": relevant}

            return await self._run_node(state, "schema", operation)

        async def sql(state: AgentState) -> dict[str, Any]:
            async def operation() -> dict[str, Any]:
                feedback = state.get("validation_error") or state.get("execution_error")
                candidate = await self.sql_agent.run(
                    state["question"], state["plan"], state["schema"], feedback
                )
                return {
                    "sql_candidate": candidate,
                    "validation_error": None,
                    "execution_error": None,
                }

            return await self._run_node(state, "sql", operation)

        async def review(state: AgentState) -> dict[str, Any]:
            async def operation() -> dict[str, Any]:
                result = await self.reviewer.run(
                    state["question"], state["plan"], state["schema"], state["sql_candidate"]
                )
                if not result.approved:
                    return {"review": result, "validation_error": result.reason}
                try:
                    validate_readonly_sql(
                        state["sql_candidate"].sql,
                        allowed_schemas=set(self.database.allowed_schemas),
                        allowed_tables=set(self.database.allowed_tables) or None,
                    )
                    return {"review": result, "validation_error": None}
                except SqlSafetyError as exc:
                    return {"review": result, "validation_error": str(exc)}

            return await self._run_node(state, "review", operation)

        async def repair(state: AgentState) -> dict[str, Any]:
            count = state.get("repair_count", 0) + 1
            await self.progress("agent_completed", "repair", {"repair_count": count})
            return {"repair_count": count}

        async def execute(state: AgentState) -> dict[str, Any]:
            async def operation() -> dict[str, Any]:
                try:
                    result = await execute_readonly(self.database, state["sql_candidate"].sql)
                    return {
                        "columns": result.columns,
                        "rows": result.rows,
                        "truncated": result.truncated,
                        "execution_error": None,
                    }
                except Exception as exc:
                    return {"execution_error": str(exc)}

            return await self._run_node(state, "execute", operation)

        async def analyze(state: AgentState) -> dict[str, Any]:
            async def operation() -> dict[str, Any]:
                result = await self.analysis_agent.run(
                    state["question"],
                    state["columns"],
                    state["rows"],
                    state.get("truncated", False),
                )
                return {"analysis": result}

            return await self._run_node(state, "analysis", operation)

        async def visualize(state: AgentState) -> dict[str, Any]:
            async def operation() -> dict[str, Any]:
                chart = await self.visualization_agent.run(
                    state["question"], state["columns"], state["rows"], state["analysis"]
                )
                return {"chart": chart}

            return await self._run_node(state, "visualization", operation)

        async def waiting(state: AgentState) -> dict[str, Any]:
            question = state["plan"].clarification_question or "请补充分析口径。"
            await self.progress("waiting_for_clarification", "coordinator", {"question": question})
            return {
                "status": "waiting_for_clarification",
                "result": {"answer": question, "status": "waiting_for_clarification"},
            }

        async def failed(state: AgentState) -> dict[str, Any]:
            error = state.get("execution_error") or state.get("validation_error") or "查询无法完成"
            await self.progress("workflow_failed", "workflow", {"error": error})
            return {
                "status": "failed",
                "error": error,
                "result": {"status": "failed", "error": error},
            }

        async def finalize(state: AgentState) -> dict[str, Any]:
            result = {
                "status": "completed",
                "answer": state["analysis"].answer,
                "sql": state["sql_candidate"].sql,
                "columns": state["columns"],
                "rows": state["rows"],
                "chart": state.get("chart"),
                "truncated": state.get("truncated", False),
            }
            await self.progress("workflow_completed", "workflow", {})
            return {"status": "completed", "result": result}

        def after_coordinator(state: AgentState) -> Literal["schema", "waiting", "failed"]:
            if state["plan"].intent == "clarify":
                return "waiting"
            if state["plan"].intent == "unsupported":
                return "failed"
            return "schema"

        def after_review(state: AgentState) -> Literal["execute", "repair", "failed"]:
            if not state.get("validation_error"):
                return "execute"
            return "repair" if state.get("repair_count", 0) < 2 else "failed"

        def after_execute(state: AgentState) -> Literal["analyze", "repair", "failed"]:
            if not state.get("execution_error"):
                return "analyze"
            return "repair" if state.get("repair_count", 0) < 2 else "failed"

        for name, node in {
            "coordinator": coordinator,
            "schema": schema,
            "sql": sql,
            "review": review,
            "repair": repair,
            "execute": execute,
            "analyze": analyze,
            "visualize": visualize,
            "waiting": waiting,
            "failed": failed,
            "finalize": finalize,
        }.items():
            builder.add_node(name, node)

        builder.add_edge(START, "coordinator")
        builder.add_conditional_edges("coordinator", after_coordinator)
        builder.add_edge("schema", "sql")
        builder.add_edge("sql", "review")
        builder.add_conditional_edges("review", after_review)
        builder.add_edge("repair", "sql")
        builder.add_conditional_edges("execute", after_execute)
        builder.add_edge("analyze", "visualize")
        builder.add_edge("visualize", "finalize")
        builder.add_edge("waiting", END)
        builder.add_edge("failed", END)
        builder.add_edge("finalize", END)
        return builder.compile()

    async def run(
        self,
        *,
        query_id: str,
        session_id: str,
        question: str,
        history: list[dict[str, str]],
    ) -> AgentState:
        return cast(
            AgentState,
            await self.graph.ainvoke(
                {
                    "query_id": query_id,
                    "session_id": session_id,
                    "question": question,
                    "history": history,
                    "repair_count": 0,
                    "status": "running",
                }
            ),
        )
