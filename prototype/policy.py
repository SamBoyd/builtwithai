import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


PolicyStatus = Literal["provided", "discovered", "none_found"]


class PolicyContextError(Exception):
    pass


@dataclass(frozen=True)
class PolicyContext:
    status: PolicyStatus
    path: Path | None
    content: str


def get_repository_root() -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def _read_policy(path: Path, status: PolicyStatus) -> PolicyContext:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise PolicyContextError(f"could not read policy file {path}") from error
    except UnicodeDecodeError as error:
        raise PolicyContextError(f"could not read policy file {path} as UTF-8") from error
    return PolicyContext(status=status, path=path, content=content)


def load_policy_context(policy_path: Path | None, repo_root: Path | None) -> PolicyContext:
    if policy_path is not None:
        return _read_policy(policy_path, "provided")

    if repo_root is None:
        return PolicyContext(status="none_found", path=None, content="")

    for filename in ("AI_POLICY.md", "CONTRIBUTING.md"):
        candidate = repo_root / filename
        if candidate.exists():
            return _read_policy(candidate, "discovered")

    return PolicyContext(status="none_found", path=None, content="")
