import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    openai_api_key: str | None
    github_token: str | None


def _non_blank_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    return None


def load_config(repo_root: Path | None) -> Config:
    dotenv_path = (repo_root or Path.cwd()) / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)
    return Config(
        openai_api_key=_non_blank_env("OPENAI_API_KEY"),
        github_token=_non_blank_env("GITHUB_TOKEN"),
    )
