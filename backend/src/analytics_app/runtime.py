from __future__ import annotations

from analytics_app.config import AppSettings
from analytics_app.domain.models import (
    DatabaseConfigInput,
    DatabaseConfigPublic,
    ProviderConfigInput,
    ProviderConfigPublic,
    ProviderName,
)
from analytics_app.llm.providers import provider_defaults


class RuntimeConfigStore:
    """Process-local secret store. Secrets are never persisted to SQLite."""

    def __init__(self, settings: AppSettings) -> None:
        self.database: DatabaseConfigInput | None = None
        postgres_database = getattr(settings, "postgres_database", None)
        postgres_user = getattr(settings, "postgres_user", None)
        if postgres_database and postgres_user:
            self.database = DatabaseConfigInput(
                host=getattr(settings, "postgres_host", "localhost"),
                port=getattr(settings, "postgres_port", 5432),
                database=postgres_database,
                username=postgres_user,
                password=getattr(settings, "postgres_password", None),
                allowed_schemas=["public"],
            )
        self.providers: dict[ProviderName, ProviderConfigInput] = {
            ProviderName.OPENAI: ProviderConfigInput(
                api_key=settings.openai_api_key, model=settings.openai_model
            ),
            ProviderName.DEEPSEEK: ProviderConfigInput(
                api_key=settings.deepseek_api_key, model=settings.deepseek_model
            ),
            ProviderName.QWEN: ProviderConfigInput(
                api_key=settings.qwen_api_key,
                model=settings.qwen_model,
                base_url=settings.qwen_base_url,
            ),
        }
        self.default_provider = ProviderName.OPENAI

    def set_database(self, config: DatabaseConfigInput) -> DatabaseConfigPublic:
        if not config.password and self.database and self.database.password:
            config.password = self.database.password
        self.database = config
        return self.public_database()

    def public_database(self) -> DatabaseConfigPublic:
        if not self.database:
            raise ValueError("PostgreSQL 尚未配置")
        value = self.database
        return DatabaseConfigPublic(
            **value.model_dump(exclude={"password"}),
            password_configured=bool(value.password and value.password.get_secret_value()),
        )

    def set_provider(
        self, provider: ProviderName, config: ProviderConfigInput
    ) -> ProviderConfigPublic:
        current = self.providers.get(provider)
        if not config.api_key and current and current.api_key:
            config.api_key = current.api_key
        self.providers[provider] = config
        return self.public_provider(provider)

    def public_provider(self, provider: ProviderName) -> ProviderConfigPublic:
        value = self.providers[provider]
        defaults = provider_defaults(provider)
        return ProviderConfigPublic(
            provider=provider,
            base_url=value.base_url or defaults.base_url,
            model=value.model or defaults.model,
            timeout_seconds=value.timeout_seconds,
            api_key_configured=bool(value.api_key and value.api_key.get_secret_value()),
        )
