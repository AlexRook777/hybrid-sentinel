---
name: "Code Review"
description: Multi-perspective code review of specified files or directories
category: Review
tags: [review, security, quality]
---

Perform a thorough multi-perspective code review.

**Input**: Specify files, directories, or a change name (e.g., `/code-review src/hybrid_sentinel/stream/`, `/code-review add-stream-processing`). If omitted, review all uncommitted changes.

**Steps**

1. **Determine scope**

   - If a path is given, review that file/directory
   - If a change name is given, read its tasks.md to find implemented files
   - If nothing specified, use `git diff --name-only` and `git diff --cached --name-only` plus untracked files to find what changed

   Announce: "Reviewing: <scope description>"

2. **Read all files in scope**

   Read every file that will be reviewed. Do NOT review code you haven't read.

3. **Run automated checks in parallel**

   Use the Bash tool to run these (skip any that aren't configured):
   ```bash
   ruff check <paths>
   mypy <paths>
   ```
   Collect results but continue even if tools fail.

4. **Perform multi-perspective review**

   Review the code from **six perspectives**, using a separate heading for each:

   ### Security
   - Injection vulnerabilities (SQL, command, XSS)
   - Authentication/authorization gaps
   - Secrets or credentials in code
   - Input validation at system boundaries
   - OWASP Top 10 relevance
   - For FastAPI: request validation, dependency injection safety

   ### Correctness
   - Logic errors, off-by-one, race conditions
   - Error handling: are exceptions caught appropriately?
   - Edge cases: empty inputs, None values, boundary conditions
   - Async correctness: proper await, no blocking in async contexts
   - Resource cleanup: files, connections, locks properly closed

   ### Performance
   - Unnecessary allocations or copies
   - N+1 queries or repeated expensive operations
   - Blocking calls in async code paths
   - Missing timeouts on external calls
   - Memory leaks (unclosed resources, growing collections)

   ### Architecture & Design
   - Single responsibility: does each module/class do one thing?
   - Coupling: are modules properly decoupled?
   - Consistency with project conventions (see CLAUDE.md)
   - API design: clear interfaces, proper status codes
   - Testability: can components be tested in isolation?

   ### Code Quality
   - Naming clarity
   - Dead code or unused imports
   - Missing type hints on public interfaces
   - Overly complex functions (consider cyclomatic complexity)
   - Duplicated logic that should be shared

   ### Spec Alignment
   If a change name was provided or can be inferred from the files under review:
   - Read the change's `proposal.md`, `design.md`, `tasks.md`, and any `spec-delta.md` files from `openspec/changes/<change-name>/`
   - Verify every SHALL requirement in the spec-delta has a corresponding implementation
   - Check that EARS scenarios (GIVEN/WHEN/THEN) are covered by tests
   - Flag any implemented behavior that contradicts or extends beyond the spec
   - Flag any spec requirements that appear unimplemented or partially implemented
   - Verify design decisions in `design.md` were followed (data structures, patterns, module boundaries)

   If no change context is available, skip this section and note: "No OpenSpec change context — spec alignment not checked."

5. **Summarize findings**

   End with a summary table:

   ```
   ## Summary

   | Perspective    | Issues | Severity |
   |----------------|--------|----------|
   | Security       | N      | High/Med/Low/None |
   | Correctness    | N      | High/Med/Low/None |
   | Performance    | N      | High/Med/Low/None |
   | Architecture   | N      | High/Med/Low/None |
   | Code Quality   | N      | High/Med/Low/None |
   | Spec Alignment | N      | High/Med/Low/None |
   ```

   Then list actionable items ordered by severity (High first).

**Output Format**

```
## Code Review: <scope>

**Files reviewed:** N files
**Linter results:** ruff: N issues, mypy: N issues

### Security
<findings or "No issues found.">

### Correctness
<findings or "No issues found.">

### Performance
<findings or "No issues found.">

### Architecture & Design
<findings or "No issues found.">

### Code Quality
<findings or "No issues found.">

### Spec Alignment
<findings or "No OpenSpec change context — spec alignment not checked.">

## Summary
| Perspective    | Issues | Severity |
|----------------|--------|----------|
| ...            | ...    | ...      |

## Action Items
1. **[HIGH]** <description> — <file:line>
2. **[MED]** <description> — <file:line>
3. **[LOW]** <description> — <file:line>
```

**Guardrails**
- Always read files before reviewing — never review code you haven't seen
- Be specific: reference file paths and line numbers for every finding
- Distinguish between bugs (must fix) and suggestions (nice to have)
- Don't flag style issues already handled by ruff/mypy
- Don't suggest adding docstrings, comments, or type hints to code that wasn't changed
- Keep findings actionable — say what to fix, not just what's wrong
- If no issues found in a perspective, say so briefly and move on
