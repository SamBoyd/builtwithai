import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    env_var: str
    default_dir: Path
    glob_pattern: str


@dataclass(frozen=True)
class SessionCandidate:
    agent: str
    path: Path
    label: str
    modified_at: float


AGENTS = {
    "codex": AgentDefinition(
        name="codex",
        env_var="BUILTWITHAI_CODEX_SESSIONS_DIR",
        default_dir=Path.home() / ".codex" / "sessions",
        glob_pattern="**/*.jsonl",
    ),
    "claude-code": AgentDefinition(
        name="claude-code",
        env_var="BUILTWITHAI_CLAUDE_CODE_SESSIONS_DIR",
        default_dir=Path.home() / ".claude" / "projects",
        glob_pattern="**/*.jsonl",
    ),
    "opencode": AgentDefinition(
        name="opencode",
        env_var="BUILTWITHAI_OPENCODE_SESSIONS_DIR",
        default_dir=Path.home() / ".local" / "share" / "opencode",
        glob_pattern="**/*.jsonl",
    ),
}


def _session_root(agent: AgentDefinition) -> Path:
    configured = os.environ.get(agent.env_var)
    if configured:
        return Path(configured).expanduser()
    return agent.default_dir


def discover_sessions(agent_name: str, limit: int = 25) -> list[SessionCandidate]:
    try:
        agent = AGENTS[agent_name]
    except KeyError as error:
        raise ValueError(f'unsupported agent "{agent_name}"') from error

    root = _session_root(agent)
    if not root.exists():
        return []

    candidates = [
        SessionCandidate(
            agent=agent.name,
            path=path,
            label=path.name,
            modified_at=path.stat().st_mtime,
        )
        for path in root.glob(agent.glob_pattern)
        if path.is_file()
    ]
    return sorted(candidates, key=lambda session: session.modified_at, reverse=True)[:limit]
