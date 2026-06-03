from datetime import datetime, timezone
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest

from prototype.session_discovery import SessionCandidate
from prototype.session_metadata import SessionMetadata
from prototype.transcript_picker import (
    TranscriptPickerError,
    _build_textual_app,
    pick_transcript,
)


class FakeApp:
    @classmethod
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self):
        pass

    def query_one(self, _selector, _widget_type):
        return FakeListView.instances[-1]


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class FakeStatic(FakeWidget):
    def __init__(self, renderable, **kwargs):
        super().__init__(renderable, **kwargs)
        self.renderable = renderable


class FakeVertical:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False


class FakeSelect(FakeWidget):
    class Changed:
        pass


class FakeListView(FakeWidget):
    instances = []

    class Selected:
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = None
        self.items = []
        self.instances.append(self)

    def clear(self):
        self.index = None
        self.items = []

    def append(self, item):
        self.items.append(item)


class FakeListItem(FakeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classes = set()

    def set_class(self, enabled, class_name):
        if enabled:
            self.classes.add(class_name)
        else:
            self.classes.discard(class_name)


class FakeHeader(FakeWidget):
    pass


class FakeFooter(FakeWidget):
    pass


def session_metadata():
    return SessionMetadata(
        title="Improve transcript picker",
        created_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 1, 10, 5, tzinfo=timezone.utc),
        cwd=Path("/repo/app"),
        user_prompt_count=4,
        files_edited=("app.py",),
    )


def install_fake_textual(monkeypatch):
    FakeListView.instances = []
    textual_module = ModuleType("textual")
    app_module = ModuleType("textual.app")
    containers_module = ModuleType("textual.containers")
    widgets_module = ModuleType("textual.widgets")

    app_module.App = FakeApp
    app_module.ComposeResult = object
    containers_module.Vertical = FakeVertical
    widgets_module.Footer = FakeFooter
    widgets_module.Header = FakeHeader
    widgets_module.ListItem = FakeListItem
    widgets_module.ListView = FakeListView
    widgets_module.Select = FakeSelect
    widgets_module.Static = FakeStatic

    monkeypatch.setitem(sys.modules, "textual", textual_module)
    monkeypatch.setitem(sys.modules, "textual.app", app_module)
    monkeypatch.setitem(sys.modules, "textual.containers", containers_module)
    monkeypatch.setitem(sys.modules, "textual.widgets", widgets_module)


class TestPickTranscript:
    def test_returns_selected_path_from_app(self, monkeypatch):
        selected = Path("/tmp/session.jsonl")
        app = Mock()
        app.run.return_value = selected
        app_class = Mock(return_value=app)
        monkeypatch.setattr("prototype.transcript_picker.TranscriptPickerApp", app_class)

        assert pick_transcript() == selected
        app_class.assert_called_once_with()

    def test_raises_when_no_path_is_selected(self, monkeypatch):
        app = Mock()
        app.run.return_value = None
        app_class = Mock(return_value=app)
        monkeypatch.setattr("prototype.transcript_picker.TranscriptPickerApp", app_class)

        with pytest.raises(TranscriptPickerError, match="no transcript selected"):
            pick_transcript()


class TestTextualTranscriptPickerApp:
    def test_labels_agent_selector_and_session_list(self, monkeypatch):
        install_fake_textual(monkeypatch)
        app = _build_textual_app()

        labels = [
            widget.renderable
            for widget in app.compose()
            if isinstance(widget, FakeStatic)
        ]

        assert "Agent" in labels
        assert "Transcripts" in labels

    def test_highlights_first_session_after_refresh(self, monkeypatch):
        install_fake_textual(monkeypatch)
        monkeypatch.setattr(
            "prototype.session_discovery.discover_sessions",
            Mock(
                return_value=[
                    SessionCandidate(
                        agent="codex",
                        label="session.jsonl",
                        path=Path("/tmp/session.jsonl"),
                        modified_at=1.0,
                        metadata=session_metadata(),
                    )
                ]
            ),
        )
        app = _build_textual_app()
        list(app.compose())

        app._refresh_sessions()

        assert FakeListView.instances[-1].index == 0

    def test_session_row_uses_metadata(self, monkeypatch):
        install_fake_textual(monkeypatch)
        monkeypatch.setattr(
            "prototype.session_discovery.discover_sessions",
            Mock(
                return_value=[
                    SessionCandidate(
                        agent="codex",
                        label="rollout.jsonl",
                        path=Path("/tmp/session.jsonl"),
                        modified_at=1.0,
                        metadata=session_metadata(),
                    )
                ]
            ),
        )
        app = _build_textual_app()
        list(app.compose())

        app._refresh_sessions()

        row_text = FakeListView.instances[-1].items[0].args[0].renderable
        assert "Improve transcript picker" in row_text
        assert "Prompts: 4" in row_text
        assert "Project: app" in row_text
        assert "Updated: 2026-06-01 10:05 UTC" in row_text
        assert "Created: 2026-06-01 10:00 UTC" in row_text
        assert "/tmp/session.jsonl" not in row_text
