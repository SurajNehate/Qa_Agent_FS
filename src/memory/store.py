"""LangChain-compatible SQLite chat history store.

Wraps the repository CRUD into a BaseChatMessageHistory interface
so it plugs directly into LangChain/LangGraph patterns.
"""

import os

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy.orm import sessionmaker

from src.memory.models import get_engine, init_db
from src.memory import repository


class SQLiteChatHistory(BaseChatMessageHistory):
    """Persistent chat history backed by SQLite.

    Usage:
        history = SQLiteChatHistory(session_id="abc-123")
        history.add_message(HumanMessage(content="Hello"))
        history.add_message(AIMessage(content="Hi there!"))
        print(history.messages)  # [HumanMessage(...), AIMessage(...)]
    """

    def __init__(self, session_id: str, db_url: str | None = None):
        self.session_id = session_id
        self.db_url = db_url or os.getenv(
            "DATABASE_MEMORY_URL", "sqlite:///./data/memory.db"
        )
        self._engine = get_engine(self.db_url)
        init_db(self.db_url)  # Ensure tables exist
        self._SessionLocal = sessionmaker(bind=self._engine)

        # Ensure session record exists
        with self._SessionLocal() as db:
            if not repository.get_session(db, self.session_id):
                from src.memory.models import ConversationSession
                session = ConversationSession(id=self.session_id)
                db.add(session)
                db.commit()

    @property
    def messages(self) -> list[BaseMessage]:
        """Load all messages from SQLite as LangChain BaseMessage objects."""
        with self._SessionLocal() as db:
            rows = repository.get_messages(db, self.session_id)
            result = []
            for row in rows:
                if row.role == "human":
                    result.append(HumanMessage(content=row.content))
                elif row.role == "ai":
                    result.append(AIMessage(content=row.content))
            return result

    def add_message(self, message: BaseMessage) -> None:
        """Persist a single message to SQLite."""
        role = "human" if isinstance(message, HumanMessage) else "ai"
        with self._SessionLocal() as db:
            repository.add_message(db, self.session_id, role, message.content)

    def clear(self) -> None:
        """Delete all messages for this session."""
        with self._SessionLocal() as db:
            repository.clear_session_messages(db, self.session_id)
