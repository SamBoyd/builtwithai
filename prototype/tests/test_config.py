import os

from prototype.config import load_config


class TestLoadConfig:
    def test_loads_values_from_repo_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(
            "OPENAI_API_KEY=dotenv-openai-key\nGITHUB_TOKEN=dotenv-github-token\n",
            encoding="utf-8",
        )

        config = load_config(tmp_path)

        assert config.openai_api_key == "dotenv-openai-key"
        assert config.github_token == "dotenv-github-token"

    def test_exported_environment_wins_over_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "exported-openai-key")
        monkeypatch.setenv("GITHUB_TOKEN", "exported-github-token")
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(
            "OPENAI_API_KEY=dotenv-openai-key\nGITHUB_TOKEN=dotenv-github-token\n",
            encoding="utf-8",
        )

        config = load_config(tmp_path)

        assert config.openai_api_key == "exported-openai-key"
        assert config.github_token == "exported-github-token"

    def test_missing_dotenv_returns_empty_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        config = load_config(tmp_path)

        assert config.openai_api_key is None
        assert config.github_token is None

    def test_blank_values_are_treated_as_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text("OPENAI_API_KEY=\nGITHUB_TOKEN=\n", encoding="utf-8")

        config = load_config(tmp_path)

        assert config.openai_api_key is None
        assert config.github_token is None

    def test_uses_cwd_dotenv_when_repo_root_is_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.chdir(tmp_path)
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text("OPENAI_API_KEY=cwd-openai-key\n", encoding="utf-8")

        config = load_config(None)

        assert config.openai_api_key == "cwd-openai-key"
        assert config.github_token is None
        assert os.environ["OPENAI_API_KEY"] == "cwd-openai-key"
