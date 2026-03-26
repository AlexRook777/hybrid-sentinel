# API Ingestion

### Requirement: Health Check Endpoint
The API SHALL expose a `GET /health` endpoint that returns the application's operational status.

#### Scenario: Health check returns OK when service is running
- **WHEN** a GET request is made to `/health`
- **THEN** the response status code is 200
- **AND** the response body contains `{"status": "ok"}`

#### Scenario: Health check includes version information
- **WHEN** a GET request is made to `/health`
- **THEN** the response body contains a `version` field matching the package version

### Requirement: FastAPI Application Entry Point
The API SHALL provide a runnable FastAPI application that can be started with `uvicorn`.

#### Scenario: Application starts successfully
- **WHEN** `uvicorn hybrid_sentinel.main:app` is executed
- **THEN** the server starts and listens on the configured host and port
- **AND** logs a startup message

#### Scenario: Application serves OpenAPI documentation
- **WHEN** a GET request is made to `/docs`
- **THEN** the Swagger UI page is served with the API documentation
