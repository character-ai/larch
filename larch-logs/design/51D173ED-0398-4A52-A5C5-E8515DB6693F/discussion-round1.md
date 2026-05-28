## Decision 1: Scope confirmation
- **Question**: 12-item OOS combine spans 3 clusters; should all be in scope for this `--simple` design, or a subset?
- **Resolution**: All 12 items in one pass (as originally combined). Clusters 1+2+3 each implemented in this design. Combined PR touches `scripts/lib-quiet.sh`, `scripts/breadcrumb-monitor.sh`, `scripts/design-log-publish.sh`, `scripts/run-step5-review.sh`, `scripts/ship-pr.sh`, `skills/implement/scripts/step-7a.sh`, `SECURITY.md`, `scripts/design-log-publish.md`, `scripts/test-design-log-publish.sh`, `scripts/test-mermaid-fragments.sh`.
- **Source**: user

## Decision 2: Cluster 1 Item C — design-log-publish.sh breadcrumb-helper failure semantics
- **Question**: When `larch_log_publish_breadcrumbs_shared` (or related breadcrumb-helper invocations) fails inside `design-log-publish.sh:402-405`, should publish hard-abort (`PUBLISH_OK=false`) or emit a soft warning while publish proceeds?
- **Resolution**: Hard abort. Treat breadcrumb-helper failure as a publish failure, matching `larch-log.sh commit` semantics. This eliminates the failure-mode skew called out in the OOS body and gives operators a symmetric contract across both helpers that share the redaction pipeline.
- **Source**: user

## Decision 3: Cluster 1 Item B — breadcrumb-monitor.sh:149 tmpdir redaction
- **Question**: Should the foreground monitor at `scripts/breadcrumb-monitor.sh:149` pipe each surfaced line through `redact-tmpdir-paths.sh`, or should the omission be documented as intentional with no code change?
- **Resolution**: Apply redaction (code fix). Pipe each surfaced line through `redact-tmpdir-paths.sh` in the foreground monitor before printing. Eliminates the tmpdir leak parity gap with committed `larch-logs/.../breadcrumbs/` copies.
- **Source**: user

## Decision 4: Hard constraints (codebase finding)
- **Question**: What existing behavior of the touched scripts must not regress?
- **Resolution**:
  - `scripts/lib-quiet.sh` FD-3 contract (`larch_quiet_init` / `larch_emit_kv` / `larch_quiet_append_done_trap`) and the existing PID-keyed ownership check at `scripts/lib-quiet.sh:172`.
  - `scripts/breadcrumb-monitor.sh` must continue to honor `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` / `LARCH_BREADCRUMBS_SURFACED_FILE` for top-level Family B writers (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`, `dispatch-plan-voters.sh`) per `BASH_AUTHORING.md` §4. The `--paired-pid-file` argument and post-monitor `wait` invariant remain unchanged.
  - `scripts/design-log-publish.sh` must continue to emit `PUBLISH_OK=true|false` as a machine line; consumers (Step 5c orchestrator in `/design`) parse this directly. Adding new `PUBLISH_OK=false` exit conditions is acceptable; removing the line is not.
  - `sanitize_diagnostic_line` opt-in adoption — must not alter behavior of currently-sanitized call sites (`scripts/ci-failed-jobs.sh`). Only add new call sites under audit; do not refactor existing ones.
  - Render-cache fail-closed policy already documented at `SECURITY.md:186` ("`render-cache/` requires the root to be a real directory…") — Item 2C may already be satisfied at the high-level note; a more targeted line under the early "Security Findings in OOS Workflows" summary or canonical `## Breadcrumb stream redaction` section may still be useful. Plan to verify and adjust minimally.
- **Source**: codebase (`scripts/lib-quiet.sh`, `scripts/breadcrumb-monitor.sh`, `scripts/design-log-publish.sh`, `SECURITY.md`, `BASH_AUTHORING.md`)
