## Why

The Hybrid Sentinel project needs a foundational Python project structure before any feature work can begin. Without a proper scaffold — dependency management, source layout, configuration, and entry points — there is no codebase for the stream processing, anomaly detection, or agent investigation features to build on. This is the first step in the project's strategic roadmap.

## What Changes

- Create a Python package structure using `src/` layout with `hybrid_sentinel` as the root package
- Set up `pyproject.toml` with uv as the package manager and all core dependencies (FastAPI, Bytewax, River, LangGraph)
- Add a FastAPI application entry point with health check endpoint
- Create configuration module for environment-based settings
- Add development tooling configuration (pytest, ruff, mypy)
- Create initial test structure with a passing smoke test
- Add a Dockerfile for containerized deployment

## Capabilities

### New Capabilities
- `project-structure`: Python project layout, packaging, dependency management, and development tooling
- `api-ingestion`: FastAPI application entry point and health check endpoint

### Modified Capabilities

## Impact

- **Code**: Creates `src/hybrid_sentinel/` package with `__init__.py`, `main.py`, `config.py`
- **Dependencies**: Establishes `pyproject.toml` with FastAPI, Bytewax, River, LangGraph, plus dev tools (pytest, ruff, mypy)
- **APIs**: Adds `GET /health` endpoint for liveness checks
- **Systems**: Adds Dockerfile for container builds
