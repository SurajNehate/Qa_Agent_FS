# Hardening Checklist

These items improve production quality but don't teach new agentic AI patterns.
They can be addressed at any point without a dedicated version prompt.

## Database

- [ ] **Alembic migrations** - Replace `init_db()` / `Base.metadata.create_all()` with proper Alembic migration setup. Add initial migration `001_create_memory_tables.py` and a `make migrate` target.
- [ ] **Connection pooling** - Current SQLite usage creates connections per request. For scaling beyond a single process, add `pool_size` and `pool_pre_ping` to `create_engine()`.

## Code Quality

- [ ] **Split app.py** - Currently 382 lines (over 300-line budget). Extract into:
  - `src/ui/sidebar.py` - Session management, upload, settings
  - `src/ui/chat.py` - Chat display and input handling
  - `src/ui/app.py` - Main layout and routing (should be under 100 lines)
- [ ] **Fail-fast API key validation** - On startup, check that the selected LLM provider's API key is present. Currently errors only surface during the first LLM call.

## Build and Tooling

- [ ] **Makefile completeness** - Add missing targets:
  ```makefile
  migrate:
      alembic upgrade head

  debug:
      LANGGRAPH_DEBUG=true streamlit run src/ui/app.py

  lint:
      ruff check src/ tests/
  ```
- [ ] **Pre-commit hooks** - Add ruff + mypy checks
- [ ] **CI pipeline** - GitHub Actions for test + lint on push

## Retrieval Quality

- [ ] **Score threshold filtering** - Filter out documents with similarity score below `CONTEXT_SCORE_THRESHOLD` in `prepare_retrieval()`. Currently returns TOP_K results regardless of relevance.
- [ ] **Hybrid search** - Combine dense (embedding) and sparse (BM25) retrieval for better accuracy.
- [ ] **Chunk metadata enrichment** - Add section headers, document titles, and page numbers to chunk metadata for better citation quality.

## Security

- [ ] **Input sanitization** - Validate and sanitize user input before passing to LLM prompts
- [ ] **Rate limiting** - Add request rate limiting for the Streamlit app
- [ ] **API key rotation** - Support for rotating API keys without restart
