from datetime import datetime, timezone
from pathlib import Path

from prototype.session_metadata import SessionMetadata, parse_session_metadata


FIXTURE = Path(__file__).parent / "resources" / "codex-session-fictional.jsonl"


class TestParseCodexSessionMetadata:
    def test_reads_codex_rollout_metadata_from_fictional_fixture(self):
        metadata = parse_session_metadata("codex", FIXTURE)

        assert metadata.created_at == datetime(
            2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc
        )
        assert metadata.updated_at == datetime(
            2026, 6, 1, 10, 6, 0, 250000, tzinfo=timezone.utc
        )
        assert metadata.cwd == Path("/workspace/example-app")
        assert metadata.title == "Add a command line report for build status"
        assert metadata.user_prompt_count == 3
        assert metadata.files_edited == (
            "/tmp/outside-workspace.txt",
            "README.md",
            "src/report.py",
            "tests/test_report.py",
        )

    def test_ignores_malformed_jsonl_rows(self, tmp_path):
        session = tmp_path / "rollout.jsonl"
        session.write_text(
            "\n".join(
                [
                    "not json",
                    (
                        '{"timestamp":"2026-06-01T10:00:00Z","type":"session_meta",'
                        '"payload":{"timestamp":"2026-06-01T09:59:00Z","cwd":"/repo/app"}}'
                    ),
                    (
                        '{"timestamp":"2026-06-01T10:01:00Z","type":"event_msg",'
                        '"payload":{"type":"user_message","message":"Please fix the tests"}}'
                    ),
                ]
            ),
            encoding="utf-8",
        )

        metadata = parse_session_metadata("codex", session)

        assert metadata.created_at == datetime(2026, 6, 1, 9, 59, tzinfo=timezone.utc)
        assert metadata.updated_at == datetime(2026, 6, 1, 10, 1, tzinfo=timezone.utc)
        assert metadata.cwd == Path("/repo/app")
        assert metadata.title == "Please fix the tests"
        assert metadata.user_prompt_count == 1

    def test_returns_empty_metadata_for_unsupported_agent(self, tmp_path):
        session = tmp_path / "session.jsonl"
        session.write_text("{}", encoding="utf-8")

        metadata = parse_session_metadata("claude-code", session)

        assert metadata == SessionMetadata(
            title=None,
            created_at=None,
            updated_at=None,
            cwd=None,
            user_prompt_count=0,
            files_edited=(),
        )
