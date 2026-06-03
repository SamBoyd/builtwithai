import instructor

from prototype.config import Config, DEFAULT_LLM_MODEL, PROVIDER_API_KEY_ENV_NAMES
from prototype.schemas import ReceiptResult


DEFAULT_MODEL = DEFAULT_LLM_MODEL
DEFAULT_TEMPERATURE = 1
PROVIDER_EXTRAS = {
    "openai": "openai",
    "google": "google",
    "generative-ai": "google",
    "groq": "groq",
}


class LLMClientError(Exception):
    pass


def _provider_from_model(model: str) -> str:
    try:
        provider, model_name = model.split("/", 1)
    except ValueError:
        raise LLMClientError(
            'LLM_MODEL must use model string format, like "anthropic/claude-sonnet-4-6"'
        ) from None
    if not provider or not model_name:
        raise LLMClientError(
            'LLM_MODEL must use model string format, like "anthropic/claude-sonnet-4-6"'
        )
    return provider


def _api_key_for_provider(config: Config, provider: str) -> str:
    env_name = PROVIDER_API_KEY_ENV_NAMES.get(provider)
    if env_name is None:
        raise LLMClientError(f'LLM_MODEL provider "{provider}" is not configured')
    api_key = config.provider_api_keys.get(provider)
    if not api_key:
        raise LLMClientError(f"{env_name} is required to generate a receipt with {provider}")
    return api_key


def _provider_dependency_guidance(provider: str) -> str | None:
    if provider == "anthropic":
        return (
            "The Anthropic SDK is included in the base BuiltWithAI install; "
            "reinstall or upgrade BuiltWithAI."
        )
    extra = PROVIDER_EXTRAS.get(provider)
    if extra is None:
        return None
    return f'Install BuiltWithAI with provider support, for example `builtwithai[{extra}]`.'


def _missing_provider_sdk_message(error: Exception) -> bool:
    message = str(error).lower()
    return "package is required" in message and "provider" in message


def generate_receipt(prompt: str, config: Config) -> ReceiptResult:
    model = config.llm_model
    provider = _provider_from_model(model)
    api_key = _api_key_for_provider(config, provider)

    try:
        client = instructor.from_provider(model, api_key=api_key)
        return client.create(
            response_model=ReceiptResult,
            messages=[{"role": "user", "content": prompt}],
            temperature=DEFAULT_TEMPERATURE,
        )
    except Exception as error:
        message = f"could not generate receipt with {model}: {error}"
        if _missing_provider_sdk_message(error):
            guidance = _provider_dependency_guidance(provider)
            if guidance is not None:
                message = f"{message} {guidance}"
        raise LLMClientError(message) from error
