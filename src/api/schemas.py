"""Pydantic request/response schemas for the REST API.

Keeps API contract separate from internal AgentState.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    """Request body for the /api/ask endpoint."""

    question: str = Field(..., min_length=1, description="The question to ask the agent")
    session_id: str | None = Field(None, description="Session ID for conversation memory")
    model: str | None = Field(None, description="LLM model to use (e.g. gpt-5-nano, llama-3.1-8b-instant)")
    rag_enabled: bool = Field(True, description="Enable RAG retrieval from indexed documents")
    tools_enabled: bool = Field(False, description="Enable agent tools (web search, etc.)")

    model_config = {"json_schema_extra": {
        "examples": [{
            "question": "What is LangGraph?",
            "session_id": "abc-123",
            "rag_enabled": True,
            "tools_enabled": False,
        }]
    }}


class IngestRequest(BaseModel):
    """Metadata for document ingestion (files uploaded via multipart)."""

    replace_existing: bool = Field(False, description="If True, clear collection before ingesting")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class AskResponse(BaseModel):
    """Response body for the /api/ask endpoint."""

    answer: str = Field(..., description="Generated answer")
    citations: list[dict] = Field(default_factory=list, description="Source citations")
    source_type: str = Field("direct", description="Answer source: rag | web | fallback | direct")
    used_fallback: bool = Field(False, description="Whether the answer used fallback mode")
    session_id: str | None = Field(None, description="Session ID for this conversation")
    error: str | None = Field(None, description="Error message if something went wrong")


class IngestResponse(BaseModel):
    """Response body for the /api/ingest endpoint."""

    files_processed: int = Field(..., description="Number of files ingested")
    chunks_created: int = Field(..., description="Number of text chunks stored")


class SessionResponse(BaseModel):
    """Single session in the list response."""

    id: str
    title: str
    created_at: str


class HealthResponse(BaseModel):
    """Response body for the /api/health endpoint."""

    status: str = "ok"
    version: str = "0.2.0"
    rag_ready: bool = False
    web_search_ready: bool = False
