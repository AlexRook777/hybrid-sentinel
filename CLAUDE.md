# CLAUDE.md — Hybrid Sentinel

## Project Overview

**Hybrid Sentinel** is a real-time AI transaction anomaly detection and agentic investigation system
for a custom back-office payment gateway in the Fintech / P2P Payment Routing domain.

Two-stage payment stream data verification:
1. **Neural network** — real-time stream analysis and alert generation
2. **AI agent** — analyzing/filtering alerts and generating inquiries for human review

Full project blueprint: `Real-Time AI Transaction Anomaly Detection & Agentic Investigation.md`

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | **FastAPI** | HTTP endpoints, webhook ingestion |
| Stream Processing | **Bytewax** | Stateful 5-min windows, callback matching |
| Anomaly Detection | **River** | Online/incremental ML, concept drift detection |
| Agent Investigation | **LangGraph** | Autonomous anomaly investigation, Slack alerts |
| Language | **Python 3.12+** | Unified stack |
| Packaging | **uv** or **poetry** | Dependency management |

## Architecture (from blueprint)

```
Webhook/Redpanda → FastAPI Ingestion → Bytewax Stream Processing
                                            ↓
                                    River Anomaly Scoring
                                            ↓
                                   Score > 0.85 threshold
                                            ↓
                                    LangGraph Agent Investigation
                                            ↓
                                    Slack Alert / Case Report
```

### Key Design Decisions

- **Anomaly threshold**: 0.85 score triggers agent investigation
- **Callback timeout**: 300 seconds (5 min) before TIMEOUT anomaly event
- **Target latency**: < 10 seconds for behavioral anomaly detection
- **Target throughput**: 1k-10k TPS

---

## OpenSpec — Spec-Driven Development

This project uses the **OpenSpec framework** for managing specifications as living documentation.
Specs are written before code. Code follows specs. Specs stay current through the archive lifecycle.

### Roadmap

High-level implementation plan lives in `openspec/ROADMAP.md`.
Each phase maps to OpenSpec change(s). Update status as changes progress through the lifecycle.

### Directory Structure

```
hybrid-sentinel/
├── openspec/
│   ├── ROADMAP.md                # High-level phase plan (manually maintained)
│   ├── specs/                    # Living specifications (source of truth)
│   │   ├── stream-processing/
│   │   │   └── spec.md
│   │   ├── anomaly-detection/
│   │   │   └── spec.md
│   │   ├── agent-investigation/
│   │   │   └── spec.md
│   │   └── api-ingestion/
│   │       └── spec.md
│   ├── changes/                  # Active change proposals
│   │   ├── {change-id}/
│   │   │   ├── .openspec.yaml   # Change metadata (managed by CLI)
│   │   │   ├── proposal.md      # Why / What / Impact
│   │   │   ├── design.md        # How (technical approach)
│   │   │   ├── tasks.md         # Implementation checklist (- [ ] / - [x])
│   │   │   └── specs/
│   │   │       └── {capability}/
│   │   │           └── spec-delta.md  # ADDED/MODIFIED/REMOVED
│   │   └── archive/             # Completed changes (immutable history)
│   │       └── {YYYY-MM-DD}-{change-id}/
│   └── .openspec.yaml           # Project-level OpenSpec config
├── src/                          # Source code
├── tests/                        # Test suite
└── CLAUDE.md                     # This file
```

### OpenSpec Lifecycle

```
1. EXPLORE   →  2. PROPOSE   →  3. APPLY     →  4. ARCHIVE
   (think)       (plan)          (code)           (merge & close)
```

| Phase | Slash Command | What Happens | Output |
|-------|--------------|-------------|--------|
| **Explore** | `/opsx:explore` | Think through ideas, investigate codebase, visualize | Clarity, diagrams, decisions |
| **Propose** | `/opsx:propose` | CLI scaffolds change, generates artifacts | `proposal.md`, `design.md`, `tasks.md` |
| **Apply** | `/opsx:apply` | Execute tasks sequentially, test each one | Working code, `- [x]` completed tasks |
| **Archive** | `/opsx:archive` | Sync deltas into living specs, move to archive | Updated `openspec/specs/`, archived change |

**Fluid workflow** — phases are not rigid gates. You can explore mid-implementation, update artifacts anytime.

### Spec Format — EARS (Easy Approach to Requirements Syntax)

Requirements use trigger keywords: **WHEN** (event), **IF** (state), **WHERE** (feature), **WHILE** (continuous)

```markdown
### Requirement: {Name}
WHEN {trigger},
the system SHALL {action and outcome}.

#### Scenario: {Happy Path}
GIVEN {preconditions}
WHEN {action}
THEN {expected outcome}
AND {additional outcome}

#### Scenario: {Error Case}
GIVEN {error preconditions}
WHEN {action}
THEN {error handling}
```

**Rules**:
- Use **SHALL** for binding requirements (not "should" or "may")
- Every requirement MUST have at least one scenario
- Include both positive and error/edge-case scenarios
- Avoid implementation details in requirements (those go in `design.md`)

### Delta Markers

- `## ADDED Requirements` — net-new capabilities
- `## MODIFIED Requirements` — changed behavior (include full updated text)
- `## REMOVED Requirements` — deprecated features with migration path

---

## Installed Skills & Commands

### Slash Commands (in `.claude/commands/opsx/`)

| Command | Usage | Description |
|---------|-------|-------------|
| `/opsx:explore` | `/opsx:explore` | Thinking partner — explore ideas, visualize, investigate |
| `/opsx:propose` | `/opsx:propose add-feature-name` | Create change + generate all artifacts via CLI |
| `/opsx:apply` | `/opsx:apply [change-name]` | Implement tasks sequentially from a change |
| `/opsx:archive` | `/opsx:archive [change-name]` | Archive completed change, sync spec deltas |

### Skills (in `.claude/skills/`)

| Skill | Source | Purpose |
|-------|--------|---------|
| **openspec-propose** | Official (CLI v1.2.0) | Proposal creation with CLI scaffolding |
| **openspec-apply-change** | Official (CLI v1.2.0) | Task implementation with status tracking |
| **openspec-archive-change** | Official (CLI v1.2.0) | Archive + delta sync |
| **openspec-explore** | Official (CLI v1.2.0) | Exploration / thinking partner mode |
| **sequential-thinking** | mrgoonie/claudekit-skills | Structured reasoning for complex decisions |

### Reference Materials (in `.agents/skills/openspec-reference/`)

- `EARS_FORMAT.md` — EARS requirement syntax guide (WHEN/SHALL, GIVEN/WHEN/THEN)
- `VALIDATION_PATTERNS.md` — Grep/bash patterns for validating specs
- `spec-delta-template.md` — Template for ADDED/MODIFIED/REMOVED blocks

---

## MCP Servers

| Server | Purpose | Usage |
|--------|---------|-------|
| **context7** | Fetches latest library docs and code examples | Add `use context7` to any prompt |
| **sequential-thinking** | Step-by-step reasoning for complex architecture decisions | Used automatically when deep reasoning is needed |
| **semgrep** | Static security analysis (SAST) for Python/FastAPI | Auto-scans code for vulnerabilities; 290+ rules |

Example: "How do I set up River anomaly detection? use context7"

### Code Review Workflow

After implementation (e.g., Sonnet completes `/opsx:apply`), review with:

1. **Semgrep** — deterministic security scan: `semgrep scan --config auto src/`
2. **`/code-review`** — multi-agent LLM review (install: `/plugin install code-review`)
3. **Linters** — `ruff check src/ && mypy src/`

---

## Conventions

### Change ID Naming

Format: `{verb}-{feature}` — URL-safe, lowercase, hyphenated.

Verbs: `add-`, `fix-`, `update-`, `remove-`

Examples: `add-stream-processing`, `fix-callback-timeout`, `update-anomaly-threshold`

### Capability Naming (spec directories)

Use kebab-case matching system domains:
- `stream-processing`
- `anomaly-detection`
- `agent-investigation`
- `api-ingestion`

### Commit Strategy

```bash
# After implementation:
git add src/ tests/
git commit -m "Implement {change-id}: {brief description}"

# After archiving (spec merge):
git add openspec/specs/
git commit -m "Merge spec deltas from {change-id}"

git add openspec/changes/
git commit -m "Archive {change-id}"
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-26 | Python + FastAPI stack | 100% Python-compatible, team AI/ML expertise, unified language |
| 2026-03-26 | Bytewax over Flink | Rust-engine + Python API, lower DevOps overhead, sufficient for 1k-10k TPS |
| 2026-03-26 | River for ML | Online/incremental learning, handles concept drift, no batch retraining |
| 2026-03-26 | LangGraph for agent | Natural LLM integration, graph-based investigation workflow |
| 2026-03-26 | OpenSpec for documentation | Spec-driven development, living docs, AI-friendly structure |
| 2026-03-26 | `openspec/` directory convention | Official CLI structure from `openspec init` |
| 2026-03-26 | Official CLI skills over community | Official skills use CLI for scaffolding/status; community forztf skills removed (EARS reference kept) |
| 2026-03-26 | Sequential Thinking MCP + skill | Structured reasoning for complex architecture decisions |
| 2026-03-26 | `openspec/ROADMAP.md` for phase planning | OpenSpec CLI has no native roadmap; manual markdown file tracks phases and maps to changes |
| 2026-03-27 | Semgrep MCP for security scanning | Free SAST with FastAPI-aware rules; critical for payment gateway; deterministic (no LLM hallucinations) |
| 2026-03-27 | `/code-review` plugin for LLM review | Multi-agent review catches logic bugs and convention drift; complements deterministic Semgrep |
