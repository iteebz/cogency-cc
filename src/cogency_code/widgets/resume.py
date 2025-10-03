"""Conversation resume widget for selecting existing conversations."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Static
from textual.binding import Binding

from cogency_code.conversations import list_conversations


class ResumeConversation(ModalScreen):
    """Modal screen for selecting a conversation to resume."""
    
    BINDINGS = [
        Binding("escape,q", "dismiss", "Cancel"),
        Binding("enter", "select", "Resume"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header("Select Conversation to Resume")
        yield Static("Use ↑↓ to navigate, Enter to select, Escape to cancel")
        yield DataTable(id="conversation_table")
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load conversations when screen mounts."""
        table = self.query_one(DataTable)
        
        # Add columns
        table.add_columns("Preview", "Messages", "Last Active", "ID")
        
        # Load conversations
        conversations = await list_conversations(limit=20)
        
        if not conversations:
            table.add_row("No conversations found", "", "", "")
            return
        
        # Add conversation rows
        for conv in conversations:
            table.add_row(
                conv["preview"],
                str(conv["message_count"]),
                conv["time_ago"],
                conv["conversation_id"][:8] + "...",  # Show short ID
                key=conv["conversation_id"]  # Store full ID as key
            )
        
        # Focus the table
        table.focus()
    
    def action_select(self) -> None:
        """Select the highlighted conversation and resume it."""
        table = self.query_one(DataTable)
        
        if table.cursor_row is None:
            return
        
        # Get the full conversation ID from the row key
        row_key = table.get_row_key(table.cursor_row)
        if row_key:
            conversation_id = str(row_key.value)
            self.dismiss(conversation_id)
        else:
            self.dismiss(None)  # No selection