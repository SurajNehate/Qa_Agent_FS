"""SQLAlchemy ORM models for persistent conversation memory."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class ConversationSession(Base):
    """A single conversation session (one chat thread)."""

    __tablename__ = "conversation_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(100), default="New conversation")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )

    def __repr__(self):
        return f"<Session {self.id[:8]}... title='{self.title}'>"


class ConversationMessage(Base):
    """A single message within a conversation session."""

    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("conversation_sessions.id"), nullable=False)
    role = Column(String(10), nullable=False)  # "human" or "ai"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("ConversationSession", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id} role={self.role} session={self.session_id[:8]}...>"


def get_engine(db_url: str = "sqlite:///./data/memory.db"):
    """Create a SQLAlchemy engine."""
    return create_engine(db_url, echo=False)


def init_db(db_url: str = "sqlite:///./data/memory.db"):
    """Create all tables (simple alternative to Alembic for development)."""
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return engine
