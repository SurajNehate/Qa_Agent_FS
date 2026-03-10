"""Tests for SQLite persistent conversation memory."""

import os
import uuid

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from src.memory.models import init_db, get_engine, Base
from src.memory.store import SQLiteChatHistory
from src.memory import repository
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_url(tmp_path):
    """Provide a temp SQLite DB URL for each test."""
    db_file = tmp_path / "test_memory.db"
    url = f"sqlite:///{db_file}"
    init_db(url)
    return url


@pytest.fixture
def db_session(db_url):
    """Provide a SQLAlchemy session."""
    engine = get_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


class TestRepository:
    """Test CRUD operations on sessions and messages."""

    def test_create_and_get_session(self, db_session):
        session = repository.create_session(db_session, "Test session")
        assert session.id is not None
        assert session.title == "Test session"

        fetched = repository.get_session(db_session, session.id)
        assert fetched is not None
        assert fetched.title == "Test session"

    def test_list_sessions(self, db_session):
        repository.create_session(db_session, "Session 1")
        repository.create_session(db_session, "Session 2")
        sessions = repository.list_sessions(db_session)
        assert len(sessions) == 2

    def test_delete_session(self, db_session):
        session = repository.create_session(db_session, "To delete")
        repository.add_message(db_session, session.id, "human", "Hello")
        repository.delete_session(db_session, session.id)

        assert repository.get_session(db_session, session.id) is None
        assert repository.get_messages(db_session, session.id) == []

    def test_add_and_get_messages(self, db_session):
        session = repository.create_session(db_session, "Test")
        repository.add_message(db_session, session.id, "human", "What is RAG?")
        repository.add_message(db_session, session.id, "ai", "RAG is retrieval-augmented generation.")
        repository.add_message(db_session, session.id, "human", "Tell me more")
        repository.add_message(db_session, session.id, "ai", "It combines retrieval with generation.")

        messages = repository.get_messages(db_session, session.id)
        assert len(messages) == 4
        assert messages[0].role == "human"
        assert messages[1].role == "ai"
        assert messages[2].content == "Tell me more"

    def test_auto_title_from_first_question(self, db_session):
        session = repository.create_session(db_session, "New conversation")
        repository.add_message(db_session, session.id, "human", "What is LangGraph used for?")

        db_session.refresh(session)
        assert session.title == "What is LangGraph used for?"

    def test_clear_session_messages(self, db_session):
        session = repository.create_session(db_session, "Test")
        repository.add_message(db_session, session.id, "human", "Hello")
        repository.add_message(db_session, session.id, "ai", "Hi")

        repository.clear_session_messages(db_session, session.id)
        assert repository.get_messages(db_session, session.id) == []
        # Session itself still exists
        assert repository.get_session(db_session, session.id) is not None


class TestSQLiteChatHistory:
    """Test the LangChain-compatible wrapper."""

    def test_messages_property_returns_langchain_types(self, db_url):
        session_id = str(uuid.uuid4())
        history = SQLiteChatHistory(session_id=session_id, db_url=db_url)

        history.add_message(HumanMessage(content="Hello"))
        history.add_message(AIMessage(content="Hi there!"))

        messages = history.messages
        assert len(messages) == 2
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi there!"

    def test_clear_removes_messages(self, db_url):
        session_id = str(uuid.uuid4())
        history = SQLiteChatHistory(session_id=session_id, db_url=db_url)

        history.add_message(HumanMessage(content="Hello"))
        history.clear()

        assert len(history.messages) == 0

    def test_persistence_across_instances(self, db_url):
        """Messages persist when creating a new SQLiteChatHistory with same session_id."""
        session_id = str(uuid.uuid4())

        # Instance 1: add messages
        h1 = SQLiteChatHistory(session_id=session_id, db_url=db_url)
        h1.add_message(HumanMessage(content="Persisted question"))
        h1.add_message(AIMessage(content="Persisted answer"))

        # Instance 2: read messages (simulates app restart)
        h2 = SQLiteChatHistory(session_id=session_id, db_url=db_url)
        messages = h2.messages
        assert len(messages) == 2
        assert messages[0].content == "Persisted question"
