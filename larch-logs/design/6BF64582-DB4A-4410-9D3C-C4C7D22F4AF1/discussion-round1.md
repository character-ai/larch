## Decision 1: SECURITY.md section structure
- **Question**: Should the new section use 4 sub-bullets (per Acceptance) or 5 sub-bullets (per Scope)?
- **Resolution**: Five sub-bullets as scoped: per-run-tmpdir-only / monitor-side per-line fail-closed / committed-copies via `larch-log.sh write --batch breadcrumbs` with atomic mktemp+mv / per-file skip+warn fail-closed / pattern-based residual risk
- **Source**: user (Step 1c clarifying question)

## Decision 2: SECURITY.md placement
- **Question**: Where in SECURITY.md should the new section live?
- **Resolution**: New top-level `## Breadcrumb stream redaction` section, inserted immediately after `## Trust Model` and before `## Fixed-string matching for interpolated values (issue #775 unified grep -F doctrine)`
- **Source**: user (Step 1c clarifying question)

## Decision 3: docs/run-logs.md placement
- **Question**: Where in docs/run-logs.md should the breadcrumbs/ directory + commit contract live?
- **Source**: user (Step 1c clarifying question)
- **Resolution**: New `### breadcrumbs/` subsection under `## Directory structure`. The new subsection includes both the directory layout and the `--streaming`-redacted commit contract (path resolution, `*.ndjson` filter, basename mapping, partial-success semantics) plus a cross-reference to the SECURITY.md section.

## Decision 4: Hard constraints (codebase-derived, no user input needed)
- **Question**: What must not break?
- **Resolution**: (1) Existing `## Trust Model` / `## Fixed-string matching` ordering must be preserved (only an insertion between them). (2) Existing run-logs.md `## Directory structure` prose and downstream `### round-<N>/` subsection must be preserved. (3) `redact-secrets.sh --streaming --state-file`, `lib-redact-streaming.sh` exit-1 semantics, and `scripts/larch-log.sh write --batch breadcrumbs` paths must be cited accurately against current code at `scripts/larch-log.sh` (lines 137-161, 513, 527-529 confirmed in Step 0c). (4) No code changes — pure docs.
- **Source**: codebase
