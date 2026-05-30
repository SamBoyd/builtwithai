from pathlib import Path
from unittest.mock import patch

from prototype.policy import PolicyContext, get_repository_root, load_policy_context


class TestLoadPolicyContext:
    def test_reads_explicit_policy_path(self, tmp_path):
        policy_path = tmp_path / "policy.md"
        policy_path.write_text("AI use must be disclosed.\n", encoding="utf-8")

        context = load_policy_context(policy_path, tmp_path)

        assert context == PolicyContext(
            status="provided",
            path=policy_path,
            content="AI use must be disclosed.\n",
        )

    def test_prefers_ai_policy_over_contributing(self, tmp_path):
        ai_policy = tmp_path / "AI_POLICY.md"
        contributing = tmp_path / "CONTRIBUTING.md"
        ai_policy.write_text("AI policy text.\n", encoding="utf-8")
        contributing.write_text("Contributing text.\n", encoding="utf-8")

        context = load_policy_context(None, tmp_path)

        assert context == PolicyContext(
            status="discovered",
            path=ai_policy,
            content="AI policy text.\n",
        )

    def test_uses_contributing_when_ai_policy_is_missing(self, tmp_path):
        contributing = tmp_path / "CONTRIBUTING.md"
        contributing.write_text("Contributing text.\n", encoding="utf-8")

        context = load_policy_context(None, tmp_path)

        assert context == PolicyContext(
            status="discovered",
            path=contributing,
            content="Contributing text.\n",
        )

    def test_returns_none_found_without_repository_root(self):
        context = load_policy_context(None, None)

        assert context == PolicyContext(status="none_found", path=None, content="")

    def test_returns_none_found_when_repository_has_no_policy_files(self, tmp_path):
        context = load_policy_context(None, tmp_path)

        assert context == PolicyContext(status="none_found", path=None, content="")


class TestGetRepositoryRoot:
    @patch("prototype.policy.subprocess.run")
    def test_returns_git_repository_root(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "/repo/root\n"

        assert get_repository_root() == Path("/repo/root")
        run.assert_called_once_with(
            ["git", "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        )

    @patch("prototype.policy.subprocess.run")
    def test_returns_none_when_git_command_fails(self, run):
        run.return_value.returncode = 128
        run.return_value.stdout = ""

        assert get_repository_root() is None
