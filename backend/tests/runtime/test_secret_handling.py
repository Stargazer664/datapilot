from analytics_app.config import AppSettings
from analytics_app.domain.models import DatabaseConfigInput, ProviderConfigInput, ProviderName
from analytics_app.runtime import RuntimeConfigStore


def test_public_settings_never_return_secrets() -> None:
    runtime = RuntimeConfigStore(AppSettings(_env_file=None))
    runtime.set_database(
        DatabaseConfigInput(database="demo", username="reader", password="top-secret")
    )
    runtime.set_provider(
        ProviderName.OPENAI,
        ProviderConfigInput(api_key="sk-top-secret", model="test-model"),
    )

    assert "top-secret" not in runtime.public_database().model_dump_json()
    assert "sk-top-secret" not in runtime.public_provider(ProviderName.OPENAI).model_dump_json()
    assert runtime.public_database().password_configured is True
    assert runtime.public_provider(ProviderName.OPENAI).api_key_configured is True
