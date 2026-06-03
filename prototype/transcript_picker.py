from pathlib import Path

from textual.widgets import Rule


class TranscriptPickerError(Exception):
    pass


class TranscriptPickerApp:
    def run(self) -> Path | None:
        app = _build_textual_app()
        return app.run()


def _build_textual_app():
    from datetime import datetime, timezone

    import humanize
    from textual.app import App, ComposeResult
    from textual.containers import Vertical
    from textual.widgets import Footer, Header, ListItem, ListView, Select, Static

    from prototype.session_discovery import AGENTS, SessionCandidate, discover_sessions

    def format_session_item(session: SessionCandidate) -> str:
        metadata = session.metadata
        title = metadata.title or session.label
        details = [
            _format_detail("Project", _project_name(metadata.cwd)),
            _format_detail("Updated", _format_datetime(metadata.updated_at)),
            _format_detail("Created", _format_datetime(metadata.created_at)),
            _format_detail("Prompts", str(metadata.user_prompt_count)),
        ]
        return f"{title}\n{' [dim]|[/dim] '.join(details)}\n{session.label}"

    def _format_detail(label: str, value: str) -> str:
        return f"[dim]{label}:[/dim] {value}"

    def _format_datetime(value: datetime | None) -> str:
        if value is None:
            return "unknown"
        return humanize.naturaltime(
            value.astimezone(timezone.utc),
            when=datetime.now(timezone.utc),
        )

    def _project_name(value: Path | None) -> str:
        if value is None:
            return "unknown"
        return value.name or str(value)

    class SessionListItem(ListItem):
        def __init__(self, session: SessionCandidate):
            self.session = session
            super().__init__(
                Static(format_session_item(session)),
                classes="session-list-item",
            )

        def watch_highlighted(self, highlighted: bool) -> None:
            self.set_class(highlighted, "selected-transcript")

    class SessionListView(ListView):
        BINDINGS = [("enter", "select_transcript", "Select transcript")]

        def action_select_transcript(self) -> None:
            if self.index is None:
                return
            item = self.children[self.index]
            if isinstance(item, SessionListItem):
                self.app.exit(item.session.path)

    class TextualTranscriptPickerApp(App[Path | None]):
        BINDINGS = [
            ("q", "quit", "Quit"),
        ]
        CSS = """
        .picker-section {
            padding: 1 2;
        }

        .session-list-item {
            padding: 1 1;
        }

        .selected-transcript {
            border: solid #f7c948;
            padding: 0 0;
        }

        .title {
            padding: 2 0;
        }

        .description {
            padding: 0 0 1 0;
        }

        """

        box_sizing = "border-box"

        def __init__(self):
            super().__init__()
            self.agent_name = "codex"

        def compose(self) -> ComposeResult:
            yield Header()
            with Vertical():
                with Vertical(classes="picker-section"):
                    yield Static("Pick a transcript", classes="title")
                    yield Static(
                        "Choose an agent, then select the session transcript to inspect.",
                        classes="description",
                    )
                    yield Static("Agent", classes="title")
                    yield Select(
                        [(name, name) for name in AGENTS],
                        value=self.agent_name,
                        id="agent-select",
                    )
                    yield Static("Transcripts", classes="title")
                    yield SessionListView(id="session-list")
            yield Footer()

        def on_mount(self) -> None:
            self._refresh_sessions()

        def on_select_changed(self, event: Select.Changed) -> None:
            self.agent_name = str(event.value)
            self._refresh_sessions()

        def on_list_view_selected(self, event: ListView.Selected) -> None:
            item = event.item
            if isinstance(item, SessionListItem):
                self.exit(item.session.path)

        def _refresh_sessions(self) -> None:
            session_list = self.query_one("#session-list", SessionListView)
            session_list.clear()
            sessions = discover_sessions(self.agent_name)
            for index, session in enumerate(sessions):
                item = SessionListItem(session)
                if index == 0:
                    item.highlighted = True
                    item.set_class(True, "selected-transcript")
                session_list.append(item)
            if sessions:
                session_list.index = 0

    return TextualTranscriptPickerApp()


def pick_transcript() -> Path:
    selected = TranscriptPickerApp().run()
    if selected is None:
        raise TranscriptPickerError("no transcript selected")
    return selected

if __name__ == "__main__":
    TranscriptPickerApp().run()
