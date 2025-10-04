"""Conversation resume widget for selecting existing conversations."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Static

from cogency_code.conversations import list_conversations


class ResumeConversation(ModalScreen):
    """Modal screen for selecting a conversation to resume."""

    BINDINGS = [
        Binding("escape,q", "dismiss", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Header("Select Conversation to Resume")
        yield Static("Use ↑↓ to navigate, Enter to select, Escape to cancel")
        yield DataTable(id="conversation_table")
        yield Footer()

    async def on_mount(self) -> None:
        """Load conversations when screen mounts."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"

        table.add_columns("Preview", "Messages", "Last Active", "ID")

        conversations = await list_conversations(limit=20)

        if not conversations:
            table.add_row("No conversations found", "", "", "")
            return

        for conv in conversations:
            table.add_row(
                conv["preview"],
                str(conv["message_count"]),
                conv["time_ago"],
                conv["conversation_id"][:8] + "...",
                key=conv["conversation_id"],
            )

        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection via enter or click."""
        if event.row_key and event.row_key.value:
            self.dismiss(str(event.row_key.value))
