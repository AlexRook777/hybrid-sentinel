## Context

Hybrid Sentinel is a greenfield Python project targeting real-time transaction anomaly detection. No code exists yet. The project needs a standard, well-structured foundation that supports the full tech stack (FastAPI, Bytewax, River, LangGraph) and follows modern Python packaging conventions.

The team works in Python and values a unified stack. The project will be deployed as containers on cloud infrastructure (AWS ECS/K8s).

## Goals / Non-Goals

**Goals:**
- Establish a reproducible Python project with pinned dependencies
- Create a `src/` layout that supports clean imports and packaging
- Set up FastAPI with a health check as the first runnable endpoint
- Configure development tooling (linting, type checking, testing) from day one
- Provide a Dockerfile for containerized builds

**Non-Goals:**
- Implementing any business logic (stream processing, ML, agents)
- Setting up CI/CD pipelines (future change)
- Database or message queue integration
- Production deployment configuration (Kubernetes manifests, Terraform)
- Authentication or authorization

## Decisions

### Decision 1: `uv` as package manager
**Choice**: uv over poetry/pip
**Rationale**: uv is significantly faster for dependency resolution and installation. It supports `pyproject.toml` natively and generates a `uv.lock` lockfile for reproducible builds. The Hybrid Sentinel team values fast iteration speed.
**Alternative considered**: Poetry — mature but slower; pip — no lockfile support.

### Decision 2: `src/` layout
**Choice**: `src/hybrid_sentinel/` over flat `hybrid_sentinel/`
**Rationale**: The `src/` layout prevents accidental imports from the working directory during testing. It's the recommended layout by the Python Packaging Authority (PyPA) and enforces proper installation before import.
**Alternative considered**: Flat layout — simpler but prone to import-path bugs during testing.

### Decision 3: Pydantic Settings for configuration
**Choice**: `pydantic-settings` for environment-based config
**Rationale**: FastAPI already depends on Pydantic. Using `pydantic-settings` provides typed configuration with environment variable loading, `.env` file support, and validation — all with zero extra dependencies.
**Alternative considered**: python-dotenv + dataclasses — no validation; dynaconf — extra dependency with overlapping features.

### Decision 4: Python 3.12+ minimum
**Choice**: Target Python 3.12 as minimum version
**Rationale**: Python 3.12 offers improved error messages, performance gains from the specializing interpreter, and is the current stable version supported by all target libraries (Bytewax, River, LangGraph).

## Risks / Trade-offs

- **[Risk] Bytewax or River may have conflicting transitive dependencies** → Mitigation: Pin versions early, use `uv lock` to detect conflicts before writing code.
- **[Risk] LangGraph is a fast-moving library** → Mitigation: Pin to a specific version in `pyproject.toml`, update deliberately via separate change proposals.
- **[Trade-off] `src/` layout adds slight complexity** → Accepted: The import safety benefits outweigh the minor extra nesting.
