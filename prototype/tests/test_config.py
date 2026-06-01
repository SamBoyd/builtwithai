import os

from prototype.config import DEFAULT_LLM_MODEL
from prototype.config import load_config


class TestLoadConfig:
    def test_loads_values_from_repo_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(
            "\n".join(
                [
                    "LLM_MODEL=anthropic/claude-sonnet-4-0-20250514",
                    "ANTHROPIC_API_KEY=dotenv-anthropic-key",
                    "OPENAI_API_KEY=dotenv-openai-key",
                    "GITHUB_TOKEN=dotenv-github-token",
                    
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(tmp_path)

        assert config.llm_model == "anthropic/claude-sonnet-4-0-20250514"
        assert config.provider_api_keys["openai"] == "dotenv-openai-key"
        assert config.provider_api_keys["anthropic"] == "dotenv-anthropic-key"
        assert config.github_token == "dotenv-github-token"

    def test_exported_environment_wins_over_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "groq/llama-3.3-70b-versatile")
        monkeypatch.setenv("GROQ_API_KEY", "exported-groq-key")
        monkeypatch.setenv("GITHUB_TOKEN", "exported-github-token")
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(
            "\n".join(
                [
                    "LLM_MODEL=openai/gpt-4.1-mini-2025-04-14",
                    "GROQ_API_KEY=dotenv-groq-key",
                    "GITHUB_TOKEN=dotenv-github-token",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(tmp_path)

        assert config.llm_model == "groq/llama-3.3-70b-versatile"
        assert config.github_token == "exported-github-token"

    def test_missing_dotenv_returns_empty_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        config = load_config(tmp_path)

        assert config.llm_model == DEFAULT_LLM_MODEL
        assert config.github_token is None

    def test_blank_values_are_treated_as_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text("LLM_MODEL=\nGITHUB_TOKEN=\nOPENAI_API_KEY=\n", encoding="utf-8")

        config = load_config(tmp_path)

        assert config.llm_model == DEFAULT_LLM_MODEL
        assert config.provider_api_keys["openai"] is None
        assert config.github_token is None

    def test_uses_cwd_dotenv_when_repo_root_is_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(
            "LLM_MODEL=openai/gpt-4.1-mini-2025-04-14\nOPENAI_API_KEY=cwd-openai-key",
            encoding="utf-8",
        )

        config = load_config(None)

        assert config.llm_model == "openai/gpt-4.1-mini-2025-04-14"
        assert config.provider_api_keys["openai"] == "cwd-openai-key"
        assert config.github_token is None

    def test_loads_google_key_for_both_google_provider_names(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text("GOOGLE_API_KEY=dotenv-google-key\n", encoding="utf-8")

        config = load_config(tmp_path)

        assert config.provider_api_keys["google"] == "dotenv-google-key"
        assert config.provider_api_keys["generative-ai"] == "dotenv-google-key"
