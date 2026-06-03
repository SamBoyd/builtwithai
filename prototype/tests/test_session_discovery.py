from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from prototype.session_discovery import discover_sessions
from prototype.session_metadata import SessionMetadata


class TestDiscoverSessions:
    def test_returns_recent_codex_sessions_from_override_directory(self, tmp_path, monkeypatch):
        older = tmp_path / "older.jsonl"
        newer = tmp_path / "newer.jsonl"
        older.write_text("old", encoding="utf-8")
        newer.write_text("new", encoding="utf-8")
        older.touch()
        newer.touch()
        metadata = SessionMetadata(
            title="Recent session",
            created_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 6, 1, 10, 5, tzinfo=timezone.utc),
            cwd=Path("/repo/app"),
            user_prompt_count=4,
            files_edited=("app.py",),
        )
        parser = Mock(return_value=metadata)
        monkeypatch.setenv("BUILTWITHAI_CODEX_SESSIONS_DIR", str(tmp_path))
        monkeypatch.setattr("prototype.session_discovery.parse_session_metadata", parser)

        sessions = discover_sessions("codex", limit=10)

        assert [session.path for session in sessions] == [newer, older]
        assert sessions[0].agent == "codex"
        assert sessions[0].label == "newer.jsonl"
        assert sessions[0].metadata == metadata
        parser.assert_any_call("codex", newer)
        parser.assert_any_call("codex", older)

    def test_returns_empty_list_when_agent_directory_does_not_exist(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUILTWITHAI_CODEX_SESSIONS_DIR", str(tmp_path / "missing"))

        assert discover_sessions("codex", limit=10) == []

    def test_rejects_unknown_agent(self):
        try:
            discover_sessions("missing-agent")
        except ValueError as error:
            assert 'unsupported agent "missing-agent"' in str(error)
        else:
            raise AssertionError("expected ValueError")
