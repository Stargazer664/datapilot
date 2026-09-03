from analytics_app.domain.models import ProviderName
from analytics_app.llm.providers import provider_defaults


def test_provider_defaults_are_isolated() -> None:
    assert provider_defaults(ProviderName.OPENAI).base_url == "https://api.openai.com/v1"
    assert provider_defaults(ProviderName.DEEPSEEK).base_url == "https://api.deepseek.com"
    assert "compatible-mode" in provider_defaults(ProviderName.QWEN).base_url
