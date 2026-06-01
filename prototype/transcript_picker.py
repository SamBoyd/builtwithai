from pathlib import Path


class TranscriptPickerError(Exception):
    pass


class TranscriptPickerApp:
    def run(self) -> Path | None:
        app = _build_textual_app()
        return app.run()


def _build_textual_app():
    from textual.app import App, ComposeResult
    from textual.containers import Vertical
    from textual.widgets import Footer, Header, ListItem, ListView, Select, Static

    from prototype.session_discovery import AGENTS, SessionCandidate, discover_sessions

    class SessionListItem(ListItem):
        def __init__(self, session: SessionCandidate):
            self.session = session
            super().__init__(Static(f"{session.label}\n{session.path}"))

    class TextualTranscriptPickerApp(App[Path | None]):
        BINDINGS = [("q", "quit", "Quit")]

        def __init__(self):
            super().__init__()
            self.agent_name = "codex"

        def compose(self) -> ComposeResult:
            yield Header()
            with Vertical():
                yield Select(
                    [(name, name) for name in AGENTS],
                    value=self.agent_name,
                    id="agent-select",
                )
                yield ListView(id="session-list")
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
            session_list = self.query_one("#session-list", ListView)
            session_list.clear()
            for session in discover_sessions(self.agent_name):
                session_list.append(SessionListItem(session))

    return TextualTranscriptPickerApp()


def pick_transcript() -> Path:
    selected = TranscriptPickerApp().run()
    if selected is None:
        raise TranscriptPickerError("no transcript selected")
    return selected

if __name__ == "__main__":
    TranscriptPickerApp().run()
