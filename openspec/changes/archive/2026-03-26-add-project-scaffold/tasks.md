## 1. Project Foundation

- [x] 1.1 Create `pyproject.toml` with project metadata, Python 3.12+ requirement, and uv configuration
- [x] 1.2 Add core dependencies: fastapi, uvicorn, bytewax, river, langgraph, pydantic-settings
- [x] 1.3 Add dev dependencies: pytest, ruff, mypy, httpx (for test client)
- [x] 1.4 Create `src/hybrid_sentinel/__init__.py` with `__version__`

## 2. Configuration

- [x] 2.1 Create `src/hybrid_sentinel/config.py` with Pydantic Settings class (app name, log level, host, port)
- [x] 2.2 Verify default config loads without environment variables

## 3. FastAPI Application

- [x] 3.1 Create `src/hybrid_sentinel/main.py` with FastAPI app instance and startup logging
- [x] 3.2 Add `GET /health` endpoint returning `{"status": "ok", "version": "..."}`

## 4. Testing

- [x] 4.1 Create `tests/conftest.py` with FastAPI test client fixture
- [x] 4.2 Create `tests/test_health.py` with health endpoint tests (status code, response body, version field)
- [x] 4.3 Run `pytest` and verify all tests pass

## 5. Tooling & Container

- [x] 5.1 Configure ruff, mypy, and pytest sections in `pyproject.toml`
- [x] 5.2 Run `ruff check` and `mypy` against src — fix any issues
- [x] 5.3 Create `Dockerfile` with multi-stage build (uv install → runtime)
