from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from analytics_app.domain.models import ProviderConfigInput, ProviderName
from analytics_app.llm.base import LlmError, LLMProvider

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ProviderDefaults:
    base_url: str
    model: str


def provider_defaults(provider: ProviderName) -> ProviderDefaults:
    values = {
        ProviderName.OPENAI: ProviderDefaults("https://api.openai.com/v1", "gpt-5-mini"),
        ProviderName.DEEPSEEK: ProviderDefaults("https://api.deepseek.com", "deepseek-chat"),
        ProviderName.QWEN: ProviderDefaults(
            "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"
        ),
    }
    return values[provider]


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, provider: ProviderName, config: ProviderConfigInput) -> None:
        defaults = provider_defaults(provider)
        if not config.api_key or not config.api_key.get_secret_value():
            raise LlmError(f"{provider.value} API Key 未配置", code="provider_not_configured")
        self.provider = provider
        self.model = config.model or defaults.model
        self.base_url = config.base_url or defaults.base_url
        self.client = AsyncOpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=self.base_url,
            timeout=config.timeout_seconds,
        )

    @property
    def metadata(self) -> dict[str, Any]:
        return {"provider": self.provider.value, "model": self.model, "base_url": self.base_url}

    async def _call(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        typed_messages = cast(list[ChatCompletionMessageParam], messages)
        for attempt in range(3):
            try:
                return await self.client.chat.completions.create(
                    model=self.model, messages=typed_messages, **kwargs
                )
            except RateLimitError as exc:
                if attempt == 2:
                    raise LlmError("模型服务限流", code="rate_limited", retryable=True) from exc
            except APIConnectionError as exc:
                if attempt == 2:
                    raise LlmError(
                        "无法连接模型服务", code="provider_unavailable", retryable=True
                    ) from exc
            except APIStatusError as exc:
                raise LlmError(
                    f"模型服务返回错误状态 {exc.status_code}",
                    code="provider_status_error",
                    retryable=exc.status_code >= 500,
                ) from exc
            await asyncio.sleep(0.5 * (2**attempt))
        raise LlmError("模型调用失败")

    async def complete(self, messages: list[dict[str, str]]) -> str:
        response = await self._call(messages)
        return response.choices[0].message.content or ""

    async def complete_json(self, messages: list[dict[str, str]], schema: type[T]) -> T:
        json_messages = [
            *messages,
            {
                "role": "system",
                "content": (
                    "只输出符合以下 JSON Schema 的 JSON 对象，不要使用 Markdown："
                    + json.dumps(schema.model_json_schema(), ensure_ascii=False)
                ),
            },
        ]
        for structured_attempt in range(2):
            try:
                response = await self._call(
                    json_messages,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                return schema.model_validate_json(content)
            except (ValidationError, json.JSONDecodeError) as exc:
                if structured_attempt == 1:
                    raise LlmError("模型未返回有效结构化结果", code="invalid_model_output") from exc
                json_messages.append(
                    {"role": "user", "content": "上次输出格式无效。请严格按 JSON Schema 重新输出。"}
                )
        raise LlmError("模型未返回有效结构化结果", code="invalid_model_output")

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        try:
            typed_messages = cast(list[ChatCompletionMessageParam], messages)
            response = await self.client.chat.completions.create(
                model=self.model, messages=typed_messages, stream=True
            )
            async for chunk in response:
                text = chunk.choices[0].delta.content if chunk.choices else None
                if text:
                    yield text
        except Exception as exc:
            raise LlmError("模型流式响应失败", code="stream_error") from exc
