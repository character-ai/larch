## Proposed Design Outline

### Goals
- Close the parent-directory (ancestor) symlink TOCTOU gap in `design-log-publish.sh` staging for the plan-review, render-cache, and `.completed` subtrees.
- Route high-risk external-content `larch_err`/`larch_errf` relays through `sanitize_diagnostic_line` (broad audit), layered on top of existing `redact-secrets.sh`.

### Non-goals
- No re-implementation of already-landed items (render-cache symlink harness, mermaid embedded-`=` test, render-cache SECURITY text).
- No changes to `larch-log.sh` staging (different model) and no revival of the ripped-out breadcrumb feature / its Cluster-1 items.

### Approach sketch
- `design-log-publish.sh`: before `design_publish_stage_file`, re-validate that no ancestor component of each staged file became a symlink after the initial `find -type l` scan (per-file ancestor rescan), for all 3 subtrees; fail closed on detection.
- Update the `SECURITY.md:~207` "parent-directory races … not fully closed" caveat to reflect the closed race; add an ancestor-race case to `test-design-log-publish.sh`.
- `ship-pr.sh` + `collect-findings.sh` (HIGH), `collect-agent-results.sh` + `review-core.sh` (MEDIUM): wrap each relayed line with `sanitize_diagnostic_line` after `redact-secrets.sh`.
- Record the audit (HIGH/MEDIUM/LOW sites) in `lib-quiet.md`.

### Surfaces in scope
- `scripts/design-log-publish.sh`, `scripts/test-design-log-publish.sh`, `SECURITY.md`
- `scripts/ship-pr.sh`, `scripts/test-ship-pr.sh`, `scripts/lib-quiet.md`
- `skills/review/scripts/collect-findings.sh`, `scripts/collect-agent-results.sh`, `skills/review/scripts/review-core.sh` (+ sibling `.md` / harnesses)

### Open questions
- MEDIUM internal-stderr relays (`collect-agent-results.sh`, `review-core.sh`): route for defense-in-depth (leaning yes, per "broad sweep") or document-only? Plan/review can finalize.
