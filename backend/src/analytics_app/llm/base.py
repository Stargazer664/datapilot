from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LlmError(RuntimeError):
    def __init__(self, message: str, *, code: str = "llm_error", retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict[str, str]]) -> str: ...

    @abstractmethod
    async def complete_json(self, messages: list[dict[str, str]], schema: type[T]) -> T: ...

    @abstractmethod
    def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...

    @property
    @abstractmethod
    def metadata(self) -> dict[str, Any]: ...
