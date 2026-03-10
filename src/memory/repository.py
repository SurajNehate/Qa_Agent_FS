"""CRUD operations for conversation sessions and messages."""

from sqlalchemy import desc
from sqlalchemy.orm import Session as DBSession

from src.memory.models import ConversationSession, ConversationMessage


def create_session(db: DBSession, title: str = "New conversation") -> ConversationSession:
    """Create a new conversation session."""
    session = ConversationSession(title=title[:100])
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, session_id: str) -> ConversationSession | None:
    """Get a session by ID."""
    return db.query(ConversationSession).filter_by(id=session_id).first()


def list_sessions(db: DBSession, limit: int = 20) -> list[ConversationSession]:
    """List recent sessions, newest first."""
    return (
        db.query(ConversationSession)
        .order_by(desc(ConversationSession.updated_at))
        .limit(limit)
        .all()
    )


def delete_session(db: DBSession, session_id: str) -> None:
    """Delete a session and all its messages (cascade)."""
    session = get_session(db, session_id)
    if session:
        db.delete(session)
        db.commit()


def add_message(
    db: DBSession, session_id: str, role: str, content: str
) -> ConversationMessage:
    """Add a message to a session. Updates session title from first question."""
    msg = ConversationMessage(session_id=session_id, role=role, content=content)
    db.add(msg)

    # Auto-title: use first human message as session title
    session = get_session(db, session_id)
    if session and session.title == "New conversation" and role == "human":
        session.title = content[:60]

    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db: DBSession, session_id: str) -> list[ConversationMessage]:
    """Get all messages for a session, in chronological order."""
    return (
        db.query(ConversationMessage)
        .filter_by(session_id=session_id)
        .order_by(ConversationMessage.created_at)
        .all()
    )


def clear_session_messages(db: DBSession, session_id: str) -> None:
    """Delete all messages in a session (keeps the session itself)."""
    db.query(ConversationMessage).filter_by(session_id=session_id).delete()
    db.commit()
