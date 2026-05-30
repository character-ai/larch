## Decision 1: Scope — only the 3 genuinely-remaining Stage-5 items
- **Question**: Given 3 of 6 Stage-5 surfaces are already implemented on main (924345fba), what scope should /design plan for?
- **Resolution**: Plan only (A) `design-log-publish.sh` parent-directory (ancestor) symlink TOCTOU rescan [+ update the `SECURITY.md:~207` "not fully closed" caveat + add an ancestor-race harness case]; (B) `lib-quiet` `sanitize_diagnostic_line` passthrough audit; (C) `ship-pr.sh` fallback-relay control-byte sanitization [+ `test-ship-pr.sh`]. DROP the already-done items: `test-design-log-publish.sh` render-cache symlink harness, `SECURITY.md` render-cache text (except the caveat update from A), `test-mermaid-fragments.sh` embedded-`=` regression.
- **Source**: user

## Decision 2: lib-quiet audit breadth — broad repo sweep
- **Question**: How broad should the `sanitize_diagnostic_line` passthrough audit be?
- **Resolution**: Broad repo sweep — find every `larch_err`/`larch_errf` site that forwards external content and route high-risk ones through `sanitize_diagnostic_line`; not confined to `lib-quiet.sh` + `ship-pr.sh`. Concrete sites in `$DESIGN_TMPDIR/audit-findings.md`: HIGH = `ship-pr.sh`, `collect-findings.sh` (×2); MEDIUM (route for defense-in-depth) = `collect-agent-results.sh`, `review-core.sh`; LOW (document only) = `eval-research.sh`, `validate-citations.sh` dry-run seam, `generate-topology-docs.sh`, ~40 static usage heredocs.
- **Source**: user + codebase

## Decision 3: larch-log.sh excluded from the TOCTOU rescan
- **Question**: Does the implement-side publisher `larch-log.sh` need the same ancestor-TOCTOU rescan?
- **Resolution**: No. `larch-log.sh` uses a different staging model (`stage_round_artifact` with per-source `[ ! -L ] || continue` and an allowlisted round-artifact set) — not the `find -type l` → `find -type f` tree-enumeration pattern. The ancestor-TOCTOU is specific to `design-log-publish.sh`'s plan-review / render-cache / `.completed` subtrees.
- **Source**: codebase

## Decision 4: step-7a.sh CODE_FLOW_SKIP_REASON is moot
- **Question**: Should #3063 Cluster-3 Item-3 (`step-7a.sh` `CODE_FLOW_SKIP_REASON` sanitization) be included?
- **Resolution**: No — that relay no longer exists in `step-7a.sh` (removed during the breadcrumb-rip cleanup). Correctly excluded from #3120.
- **Source**: codebase

## Decision 5: Hard constraints (must preserve)
- **Question**: What must not break?
- **Resolution**: (a) Bash 3.2 portability (BASH_AUTHORING.md §3) — `sanitize_diagnostic_line` uses `LC_ALL=C tr`, compatible. (b) Preserve the existing `redact-secrets.sh` layering in every relay — add control-byte sanitization ON TOP, do not replace secret redaction. (c) Preserve LF line boundaries (per-line sanitize, `lib-quiet.sh` contract lines 81-88). (d) Do not regress the existing symlink/render-cache tests in `test-design-log-publish.sh`. (e) Update each script's sibling `.md` in sync (script-md-siblings rule); update `SECURITY.md` caveat only if A actually closes the race.
- **Source**: codebase
