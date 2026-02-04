"""Conversation Persistence Store.

This module provides functionality for persisting and loading conversation
history to/from disk, enabling session continuity across application restarts.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
import hashlib

logger = logging.getLogger(__name__)


class ConversationMessage(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSession(BaseModel):
    """A conversation session with metadata."""
    session_id: str = Field(..., description="Unique session identifier")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    messages: List[ConversationMessage] = Field(default_factory=list)
    workflow_state: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationStore:
    """Store for persisting conversation history."""

    def __init__(
        self,
        storage_path: str = "data/conversations",
        max_sessions: int = 100,
        max_messages_per_session: int = 1000
    ):
        """Initialize the conversation store.

        Args:
            storage_path: Directory path for storing conversations
            max_sessions: Maximum number of sessions to keep
            max_messages_per_session: Maximum messages per session
        """
        self.storage_path = Path(storage_path)
        self.max_sessions = max_sessions
        self.max_messages_per_session = max_messages_per_session
        self.current_session: Optional[ConversationSession] = None

        # Ensure storage directory exists
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        """Ensure the storage directory exists."""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Storage directory ready: {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to create storage directory: {e}")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().isoformat()
        hash_input = f"{timestamp}-{os.getpid()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.storage_path / f"session_{session_id}.json"

    def _get_index_file(self) -> Path:
        """Get the path to the session index file."""
        return self.storage_path / "session_index.json"

    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> ConversationSession:
        """Create a new conversation session.

        Args:
            metadata: Optional metadata for the session

        Returns:
            New ConversationSession
        """
        session_id = self._generate_session_id()
        session = ConversationSession(
            session_id=session_id,
            metadata=metadata or {}
        )

        self.current_session = session
        self._update_index(session)

        logger.info(f"Created new conversation session: {session_id}")
        return session

    def _update_index(self, session: ConversationSession):
        """Update the session index file."""
        index_file = self._get_index_file()

        try:
            # Load existing index
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            else:
                index = {"sessions": []}

            # Update or add session
            sessions = index.get("sessions", [])
            found = False
            for i, s in enumerate(sessions):
                if s.get("session_id") == session.session_id:
                    sessions[i] = {
                        "session_id": session.session_id,
                        "created_at": session.created_at,
                        "updated_at": session.updated_at,
                        "message_count": len(session.messages)
                    }
                    found = True
                    break

            if not found:
                sessions.append({
                    "session_id": session.session_id,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "message_count": len(session.messages)
                })

            # Enforce max sessions limit
            if len(sessions) > self.max_sessions:
                # Remove oldest sessions
                sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
                sessions = sessions[:self.max_sessions]

            index["sessions"] = sessions

            # Write index
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to update session index: {e}")

    def save_session(self, session: Optional[ConversationSession] = None) -> bool:
        """Save a session to disk.

        Args:
            session: Session to save (uses current session if None)

        Returns:
            True if saved successfully
        """
        session = session or self.current_session
        if not session:
            logger.warning("No session to save")
            return False

        try:
            # Update timestamp
            session.updated_at = datetime.now().isoformat()

            # Enforce message limit
            if len(session.messages) > self.max_messages_per_session:
                session.messages = session.messages[-self.max_messages_per_session:]

            # Save session file
            session_file = self._get_session_file(session.session_id)
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session.model_dump(), f, indent=2)

            # Update index
            self._update_index(session)

            logger.debug(f"Saved session {session.session_id} with {len(session.messages)} messages")
            return True

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load a session from disk.

        Args:
            session_id: ID of the session to load

        Returns:
            ConversationSession if found, None otherwise
        """
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            logger.warning(f"Session file not found: {session_id}")
            return None

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            session = ConversationSession(**data)
            self.current_session = session

            logger.info(f"Loaded session {session_id} with {len(session.messages)} messages")
            return session

        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def get_latest_session(self) -> Optional[ConversationSession]:
        """Get the most recent session.

        Returns:
            Latest ConversationSession if exists
        """
        index_file = self._get_index_file()

        if not index_file.exists():
            return None

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)

            sessions = index.get("sessions", [])
            if not sessions:
                return None

            # Sort by updated_at and get latest
            sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            latest = sessions[0]

            return self.load_session(latest["session_id"])

        except Exception as e:
            logger.error(f"Failed to get latest session: {e}")
            return None

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        auto_save: bool = True
    ) -> bool:
        """Add a message to the current session.

        Args:
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional message metadata
            auto_save: Whether to auto-save after adding

        Returns:
            True if added successfully
        """
        if not self.current_session:
            logger.warning("No active session, creating new one")
            self.create_session()

        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )

        self.current_session.messages.append(message)
        logger.debug(f"Added {role} message to session")

        if auto_save:
            return self.save_session()

        return True

    def update_workflow_state(
        self,
        state: Dict[str, Any],
        auto_save: bool = True
    ) -> bool:
        """Update the workflow state in the current session.

        Args:
            state: New workflow state
            auto_save: Whether to auto-save after updating

        Returns:
            True if updated successfully
        """
        if not self.current_session:
            logger.warning("No active session")
            return False

        self.current_session.workflow_state = state

        if auto_save:
            return self.save_session()

        return True

    def get_conversation_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Get conversation history from current session.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        if not self.current_session:
            return []

        messages = self.current_session.messages
        if limit:
            messages = messages[-limit:]

        return [{"role": m.role, "content": m.content} for m in messages]

    def get_workflow_state(self) -> Dict[str, Any]:
        """Get the workflow state from current session.

        Returns:
            Workflow state dictionary
        """
        if not self.current_session:
            return {}

        return self.current_session.workflow_state

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all stored sessions.

        Returns:
            List of session metadata dictionaries
        """
        index_file = self._get_index_file()

        if not index_file.exists():
            return []

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)

            sessions = index.get("sessions", [])
            sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: ID of the session to delete

        Returns:
            True if deleted successfully
        """
        try:
            # Delete session file
            session_file = self._get_session_file(session_id)
            if session_file.exists():
                session_file.unlink()

            # Update index
            index_file = self._get_index_file()
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)

                sessions = [s for s in index.get("sessions", [])
                           if s.get("session_id") != session_id]
                index["sessions"] = sessions

                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index, f, indent=2)

            # Clear current session if it was deleted
            if self.current_session and self.current_session.session_id == session_id:
                self.current_session = None

            logger.info(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def clear_all_sessions(self) -> bool:
        """Delete all sessions.

        Returns:
            True if cleared successfully
        """
        try:
            # Delete all session files
            for file in self.storage_path.glob("session_*.json"):
                file.unlink()

            # Clear index
            index_file = self._get_index_file()
            if index_file.exists():
                index_file.unlink()

            self.current_session = None

            logger.info("Cleared all sessions")
            return True

        except Exception as e:
            logger.error(f"Failed to clear sessions: {e}")
            return False

    def export_session(self, session_id: str, format: str = "json") -> Optional[str]:
        """Export a session in the specified format.

        Args:
            session_id: ID of the session to export
            format: Export format (json, text)

        Returns:
            Exported content as string
        """
        session = self.load_session(session_id)
        if not session:
            return None

        if format == "json":
            return json.dumps(session.model_dump(), indent=2)

        elif format == "text":
            lines = [
                f"Session: {session.session_id}",
                f"Created: {session.created_at}",
                f"Updated: {session.updated_at}",
                "=" * 50,
                ""
            ]

            for msg in session.messages:
                role = msg.role.upper()
                lines.append(f"[{msg.timestamp}] {role}:")
                lines.append(msg.content)
                lines.append("")

            return "\n".join(lines)

        else:
            logger.warning(f"Unknown export format: {format}")
            return None


# Global conversation store instance
_conversation_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    """Get the global conversation store instance."""
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = ConversationStore()
    return _conversation_store
