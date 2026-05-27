from dataclasses import dataclass
from pathlib import Path


@dataclass
class Transcript:
    path: Path
    mode: str
    content: str


def load_transcript(path: Path) -> Transcript:
    return Transcript(
        path=path,
        mode="text",
        content=path.read_text(encoding="utf-8"),
    )
