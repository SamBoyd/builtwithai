import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_LLM_MODEL = "openai/gpt-5.5"

PROVIDER_API_KEY_ENV_NAMES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "generative-ai": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "writer": "WRITER_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


@dataclass(frozen=True)
class Config:
    github_token: str | None
    llm_model: str = DEFAULT_LLM_MODEL
    provider_api_keys: dict[str, str | None] = field(default_factory=dict)


def _non_blank_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    return None


def _llm_model() -> str:
    return _non_blank_env("LLM_MODEL") or DEFAULT_LLM_MODEL


def _provider_api_keys() -> dict[str, str | None]:
    return {
        provider: _non_blank_env(env_name)
        for provider, env_name in PROVIDER_API_KEY_ENV_NAMES.items()
    }


def load_config(repo_root: Path | None) -> Config:
    dotenv_path = (repo_root or Path.cwd()) / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)
    return Config(
        github_token=_non_blank_env("GITHUB_TOKEN"),
        llm_model=_llm_model(),
        provider_api_keys=_provider_api_keys(),
    )
