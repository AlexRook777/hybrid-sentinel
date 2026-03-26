# Project Structure

### Requirement: Python Package Structure
The project SHALL use a `src/` layout with `hybrid_sentinel` as the importable Python package, managed by `uv` with a `pyproject.toml` manifest.

#### Scenario: Package is importable after installation
- **WHEN** the package is installed via `uv sync`
- **THEN** `import hybrid_sentinel` succeeds without error
- **AND** `hybrid_sentinel.__version__` returns a valid semver string

#### Scenario: Dependencies resolve without conflicts
- **WHEN** `uv lock` is run against the project
- **THEN** all dependencies (FastAPI, Bytewax, River, LangGraph) resolve successfully
- **AND** a `uv.lock` lockfile is generated

### Requirement: Development Tooling Configuration
The project SHALL include configuration for linting (ruff), type checking (mypy), and testing (pytest) in `pyproject.toml`.

#### Scenario: Linter runs cleanly on scaffold
- **WHEN** `ruff check src/` is run on the initial scaffold
- **THEN** no linting errors are reported

#### Scenario: Type checker runs on scaffold
- **WHEN** `mypy src/` is run on the initial scaffold
- **THEN** no type errors are reported

#### Scenario: Test suite discovers and runs tests
- **WHEN** `pytest` is run from the project root
- **THEN** at least one test is discovered and passes

### Requirement: Application Configuration
The project SHALL provide a configuration module that loads settings from environment variables with sensible defaults.

#### Scenario: Default configuration loads without environment variables
- **WHEN** the application starts without any environment variables set
- **THEN** the configuration loads with default values
- **AND** the application name defaults to "hybrid-sentinel"
- **AND** the log level defaults to "INFO"

#### Scenario: Environment variables override defaults
- **WHEN** the environment variable `SENTINEL_LOG_LEVEL` is set to "DEBUG"
- **THEN** the configuration reflects the overridden value

### Requirement: Container Build
The project SHALL include a Dockerfile that produces a runnable container image.

#### Scenario: Docker build succeeds
- **WHEN** `docker build .` is run from the project root
- **THEN** the build completes without errors
- **AND** the resulting image contains the installed `hybrid_sentinel` package
