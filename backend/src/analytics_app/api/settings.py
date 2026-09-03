from fastapi import APIRouter, HTTPException, Request

from analytics_app.db.connection import test_connection
from analytics_app.domain.models import DatabaseConfigInput, ProviderConfigInput, ProviderName
from analytics_app.llm.providers import OpenAICompatibleProvider

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings(request: Request) -> dict[str, object]:
    runtime = request.app.state.runtime
    try:
        database = runtime.public_database().model_dump()
    except ValueError:
        database = None
    return {
        "database": database,
        "providers": [runtime.public_provider(p).model_dump() for p in ProviderName],
        "default_provider": runtime.default_provider,
    }


@router.put("/database")
async def put_database(config: DatabaseConfigInput, request: Request) -> object:
    return request.app.state.runtime.set_database(config)


@router.post("/database/test")
async def post_database_test(config: DatabaseConfigInput, request: Request) -> dict[str, str]:
    current = request.app.state.runtime.database
    if not config.password and current and current.password:
        config.password = current.password
    try:
        return await test_connection(config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="无法连接 PostgreSQL，请检查配置。") from exc


@router.put("/providers/{provider}")
async def put_provider(
    provider: ProviderName, config: ProviderConfigInput, request: Request
) -> object:
    return request.app.state.runtime.set_provider(provider, config)


@router.post("/providers/{provider}/test")
async def post_provider_test(
    provider: ProviderName, config: ProviderConfigInput, request: Request
) -> dict[str, str]:
    current = request.app.state.runtime.providers.get(provider)
    if not config.api_key and current and current.api_key:
        config.api_key = current.api_key
    try:
        llm = OpenAICompatibleProvider(provider, config)
        await llm.complete([{"role": "user", "content": "只回复 OK"}])
        return {"status": "ok", "provider": provider.value, "model": config.model}
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"无法连接 {provider.value} 模型服务。"
        ) from exc
