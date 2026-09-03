from __future__ import annotations

from typing import Any
from uuid import uuid4

from analytics_app.domain.models import SessionRecord
from analytics_app.storage.database import LocalDatabase, utc_now


class SessionRepository:
    def __init__(self, database: LocalDatabase) -> None:
        self.database = database

    def create(self, title: str) -> SessionRecord:
        session_id = str(uuid4())
        now = utc_now()
        self.database.execute(
            "INSERT INTO sessions(id,title,created_at,updated_at) VALUES(?,?,?,?)",
            (session_id, title, now, now),
        )
        return SessionRecord(id=session_id, title=title, created_at=now, updated_at=now)

    def get(self, session_id: str) -> dict[str, Any] | None:
        session = self.database.fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if not session:
            return None
        session["messages"] = self.database.fetch_all(
            "SELECT role,content,created_at FROM messages WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        )
        return session

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self.database.execute(
            "INSERT INTO messages(id,session_id,role,content,created_at) VALUES(?,?,?,?,?)",
            (str(uuid4()), session_id, role, content, utc_now()),
        )


class AuditRepository:
    def __init__(self, database: LocalDatabase) -> None:
        self.database = database

    def start(
        self, query_id: str, session_id: str, provider: str, model: str, question: str
    ) -> None:
        now = utc_now()
        self.database.execute(
            """INSERT INTO query_audit(
                id,session_id,provider,model,question,status,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (query_id, session_id, provider, model, question, "running", now, now),
        )

    def finish(
        self,
        query_id: str,
        *,
        status: str,
        sql: str | None,
        row_count: int,
        repair_count: int,
        duration_ms: int,
        error_code: str | None = None,
    ) -> None:
        self.database.execute(
            """UPDATE query_audit SET status=?,sql_text=?,row_count=?,repair_count=?,
            duration_ms=?,error_code=?,updated_at=? WHERE id=?""",
            (status, sql, row_count, repair_count, duration_ms, error_code, utc_now(), query_id),
        )
