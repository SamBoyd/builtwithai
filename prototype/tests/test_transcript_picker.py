from pathlib import Path
from unittest.mock import Mock

import pytest

from prototype.transcript_picker import TranscriptPickerError, pick_transcript


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
