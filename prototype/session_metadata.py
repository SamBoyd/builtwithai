import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict


MAX_TITLE_LENGTH = 122
TITLE_ELLIPSIS = "..."


class CodexRolloutLine(TypedDict):
    timestamp: NotRequired[str]
    type: str
    payload: NotRequired[dict[str, Any]]


class CodexSessionMetaPayload(TypedDict):
    timestamp: NotRequired[str]
    cwd: NotRequired[str]
    title: NotRequired[str]
    name: NotRequired[str]


class CodexEventPayload(TypedDict):
    type: str
    message: NotRequired[str]
    changes: NotRequired[dict[str, Any]]


@dataclass(frozen=True)
class SessionMetadata:
    title: str | None
    created_at: datetime | None
    updated_at: datetime | None
    cwd: Path | None
    user_prompt_count: int
    files_edited: tuple[str, ...] = ()


def parse_session_metadata(agent_name: str, path: Path) -> SessionMetadata:
    parser = _PARSERS.get(agent_name)
    if parser is None:
        return empty_session_metadata()
    return parser(path)


def empty_session_metadata() -> SessionMetadata:
    return SessionMetadata(
        title=None,
        created_at=None,
        updated_at=None,
        cwd=None,
        user_prompt_count=0,
        files_edited=(),
    )


def _parse_codex_session(path: Path) -> SessionMetadata:
    title = None
    created_at = None
    updated_at = None
    cwd = None
    user_prompt_count = 0
    files_edited = set[str]()

    for row in _read_jsonl(path):
        timestamp = _parse_timestamp(row.get("timestamp"))
        if timestamp is not None:
            updated_at = timestamp

        payload = row.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        row_type = row.get("type")
        if row_type == "session_meta":
            created_at = created_at or _parse_timestamp(payload.get("timestamp")) or timestamp
            cwd = cwd or _parse_path(payload.get("cwd"))
            title = title or _first_string(payload, ("title", "name"))
        elif row_type == "event_msg":
            event_type = payload.get("type")
            if event_type == "user_message":
                user_prompt_count += 1
                title = title or _normalize_title(payload.get("message"))
            elif event_type == "patch_apply_end":
                files_edited.update(_changed_files(payload, cwd))

    return SessionMetadata(
        title=title,
        created_at=created_at,
        updated_at=updated_at,
        cwd=cwd,
        user_prompt_count=user_prompt_count,
        files_edited=tuple(sorted(files_edited)),
    )


def _read_jsonl(path: Path) -> Iterator[CodexRolloutLine]:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            yield row


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_path(value: object) -> Path | None:
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _first_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_title(value)
    return None


def _normalize_title(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if len(normalized) > MAX_TITLE_LENGTH:
        return f"{normalized[: MAX_TITLE_LENGTH - len(TITLE_ELLIPSIS)]}{TITLE_ELLIPSIS}"
    return normalized or None


def _changed_files(payload: dict[str, Any], cwd: Path | None) -> tuple[str, ...]:
    changes = payload.get("changes")
    if not isinstance(changes, dict):
        return ()
    return tuple(_display_path(Path(path), cwd) for path in changes)


def _display_path(path: Path, cwd: Path | None) -> str:
    if cwd is not None:
        try:
            return str(path.relative_to(cwd))
        except ValueError:
            pass
    return str(path)


_PARSERS: dict[str, Callable[[Path], SessionMetadata]] = {
    "codex": _parse_codex_session,
}
