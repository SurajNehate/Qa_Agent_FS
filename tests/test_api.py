"""Tests for the FastAPI REST API layer.

Uses FastAPI's TestClient for synchronous testing without a running server.
"""

import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.schemas import AskRequest, AskResponse, HealthResponse, IngestResponse


class TestHealthEndpoint(unittest.TestCase):
    """Test the /api/health endpoint."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("src.api.main._get_store")
    @patch("src.tools.web_search.is_tavily_configured", return_value=False)
    def test_health_returns_ok(self, mock_tavily, mock_store):
        """Health endpoint should return 200 with status ok."""
        store = MagicMock()
        store._collection.count.return_value = 0
        mock_store.return_value = store

        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.2.0"

    @patch("src.api.main._get_store")
    @patch("src.tools.web_search.is_tavily_configured", return_value=True)
    def test_health_shows_feature_flags(self, mock_tavily, mock_store):
        """Health should reflect rag_ready and web_search_ready correctly."""
        store = MagicMock()
        store._collection.count.return_value = 10
        mock_store.return_value = store

        resp = self.client.get("/api/health")
        data = resp.json()
        assert data["rag_ready"] is True
        assert data["web_search_ready"] is True


class TestAskEndpoint(unittest.TestCase):
    """Test the /api/ask endpoint."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("src.api.main._get_llm")
    @patch("src.api.main._get_store")
    @patch("src.core.graph.run_graph")
    def test_ask_returns_answer(self, mock_run, mock_store, mock_llm):
        """POST /api/ask should return an answer from run_graph."""
        mock_run.return_value = {
            "answer": "LangGraph is a framework.",
            "citations": [{"source": "docs.txt", "page": "1"}],
            "source_type": "rag",
            "used_fallback": False,
            "error": None,
        }
        mock_store.return_value = MagicMock()
        mock_llm.return_value = MagicMock()

        resp = self.client.post("/api/ask", json={
            "question": "What is LangGraph?",
            "rag_enabled": True,
            "tools_enabled": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "LangGraph is a framework."
        assert data["source_type"] == "rag"
        assert len(data["citations"]) == 1

    @patch("src.api.main._get_llm")
    @patch("src.api.main._get_store")
    @patch("src.core.graph.run_graph")
    def test_ask_returns_500_on_error(self, mock_run, mock_store, mock_llm):
        """POST /api/ask should return 500 when graph returns an error."""
        mock_run.return_value = {"error": "LLM timeout"}
        mock_store.return_value = MagicMock()
        mock_llm.return_value = MagicMock()

        resp = self.client.post("/api/ask", json={"question": "Hello"})
        assert resp.status_code == 500

    def test_ask_rejects_empty_question(self):
        """POST /api/ask should reject empty question."""
        resp = self.client.post("/api/ask", json={"question": ""})
        assert resp.status_code == 422  # Pydantic validation error


class TestSchemas(unittest.TestCase):
    """Test Pydantic schemas."""

    def test_ask_request_defaults(self):
        """AskRequest should have sensible defaults."""
        req = AskRequest(question="Hello")
        assert req.rag_enabled is True
        assert req.tools_enabled is False
        assert req.session_id is None

    def test_ask_response_model(self):
        """AskResponse should serialize correctly."""
        resp = AskResponse(
            answer="Test answer",
            citations=[{"source": "file.txt"}],
            source_type="rag",
            used_fallback=False,
        )
        data = resp.model_dump()
        assert data["answer"] == "Test answer"
        assert data["source_type"] == "rag"

    def test_health_response_defaults(self):
        """HealthResponse should have correct defaults."""
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.rag_ready is False
        assert resp.web_search_ready is False

    def test_ingest_response(self):
        """IngestResponse should serialize correctly."""
        resp = IngestResponse(files_processed=3, chunks_created=42)
        assert resp.files_processed == 3
        assert resp.chunks_created == 42


class TestDocsEndpoint(unittest.TestCase):
    """Test that OpenAPI docs are accessible."""

    def setUp(self):
        self.client = TestClient(app)

    def test_docs_accessible(self):
        """GET /docs should return the Swagger UI."""
        resp = self.client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self):
        """GET /openapi.json should return valid OpenAPI schema."""
        resp = self.client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
        assert "/api/ask" in data["paths"]
        assert "/api/health" in data["paths"]
        assert "/api/ingest" in data["paths"]

