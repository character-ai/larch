## Plan

Stage 3 of the 5-piece rip-out (#3111). Remove the breadcrumb-monitor contract at the **scripts + lint** layer only. Skill-fence collapse, `BASH_AUTHORING.md §4`, and public-doc trims are Stage 4 (#3119); #3063 hardening is Stage 5 (#3120). Two Round 1 decisions shape the plan: keep `breadcrumb-monitor.sh` as a **no-op shim** until the 13 still-live fences are removed in Stage 4; **preserve `larch_err` redaction** by calling `redact-secrets.sh --streaming` directly.

### Reviewer note — delete-vs-shrink for lint-foreground-markers
The issue says "shrink `scripts/lint-foreground-markers.*`". Verified: `lint-foreground-markers.sh` is **100% Family-B fence enforcement**; it contains **no** polling-loop-ban logic. The polling-loop ban lives in `test-implement-anti-polling-rule.sh` via AGENTS.md literal pins. So Stage 3 deletes `lint-foreground-markers.sh` + harness and retains the polling-ban in `test-implement-anti-polling-rule.sh`.

## Files to modify/create

### REWRITTEN: `scripts/breadcrumb-monitor.sh`
Replace the full monitor with a tiny no-op compatibility shim. Consume all current flags (`--stream`, `--done-sentinel`, `--status-file`, `--quiet-log`, `--surfaced-sentinel`, `--paired-pid-file`, `--poll-interval=`, `--rate-cap=`, `--final-tail-lines=`, `--mode=`, `-h/--help`) and `exit 0` for every invocation shape, including unknown args. Do **not** source `lib-quiet.sh` / `lib-larch-log.sh`. Exit 0 keeps existing Stage-4-deferred fences in their `monitor_rc=0` branch so they still `wait` the background writer and propagate its real exit code.

### UPDATED: `scripts/breadcrumb-monitor.md`
Rewrite to document only the temporary Stage 3 compatibility shim contract: no streaming, no sentinel watching, no paired-PID timeout signaling, no redaction, always exit 0, retained only until Stage 4 removes the remaining fences. Remove references to deleted monitor harnesses.

### REWRITTEN: `scripts/lib-quiet.sh`
Remove breadcrumb/sentinel/paired-PID plumbing: `larch_quiet_fd3_is_visible`; the `LARCH_BREADCRUMBS_SURFACED_FILE` write inside `larch_quiet_init`; `larch_quiet_bc_valid_category`; done-sentinel trap implementation; paired-PID implementation; and `larch_quiet_source_larch_log_lib`. Preserve short **no-op compatibility shims** for `larch_quiet_append_done_trap` and `larch_quiet_write_paired_pid_file` through Stage 4 so any still-live/deferred fence or missed dynamic caller cannot fail with `command not found`. Rewire `larch_quiet_redact_diagnostic_stream` to pipe through `redact-secrets.sh --streaming --state-file "$state"` directly; keep `larch_quiet_redaction_state_file` and the `[ ! -x ]` fallback. Keep `emit`/`emit_kv`/`larch_quiet_init`/`sanitize_diagnostic_line`.

### UPDATED: `scripts/lib-quiet.md`
Drop breadcrumb/paired-PID/sentinel contract sections. Document the temporary no-op compatibility shims and that `larch_err` redaction now calls `redact-secrets.sh --streaming` directly.

### UPDATED: `scripts/test-lib-quiet.sh`
Remove tests for `larch_quiet_bc_valid_category`, paired-PID writes/invalid/races, done-sentinel writes, and `LARCH_BREADCRUMBS_SURFACED_FILE`. Add/keep coverage that the two compatibility shims are harmless no-ops. Update the `larch_err` redaction test to the direct `redact-secrets.sh --streaming` path. Keep `emit`/`emit_kv` coverage.

### UPDATED: `skills/design/scripts/assess-plan-round.sh`
Drop the `MONITOR_SH` definition, foreground `breadcrumb-monitor.sh` call, breadcrumb/sentinel/status/paired-PID exports, and `monitor_rc` warning block. Keep the background dispatch, the existing `wait "$dispatch_pid"`, and `LARCH_QUIET_LOG_FILE` forensics redirect. Update sibling `.md`, `test-assess-plan-round.sh`, and `test-dispatch-plan-assessors.sh`.

### UPDATED: `skills/design/scripts/dispatch-plan-assessors.sh`
Remove any `larch_quiet_write_paired_pid_file` call, paired-PID env handling, and dead unset/env barriers. Update sibling `.md` and `test-dispatch-plan-assessors.sh` expectations.

### UPDATED: Family-B caller sweep
Update `scripts/ship-pr.sh`, `scripts/run-step5-review.sh`, `scripts/dispatch-plan-voters.sh`, `scripts/collect-agent-results.sh`, and `skills/implement/scripts/run-step2-dispatch.sh`: remove `larch_quiet_write_paired_pid_file`, breadcrumb stream/sentinel/status/surfaced/paired-PID plumbing, and `unset LARCH_PAIRED_PID_FILE` barriers. Update each sibling `.md`.

### UPDATED: Dead barrier sweep
Remove dead `LARCH_PAIRED_PID_FILE` unset/env barriers from `scripts/dispatch-code-voters.sh`, `skills/design/scripts/decompose-aggregator.sh`, `skills/design/scripts/decompose-panel-dispatch.sh`, `skills/design/scripts/dispatch-plan-review-panel.sh`, `skills/review/scripts/dispatch-panel.sh`, and `skills/review/scripts/aggregate-findings.sh`. Update sibling `.md` files only where they document the barrier.

### UPDATED: `SECURITY.md`
Replace monitor-side timeout/redaction claims with Stage 3 behavior: the live monitor is a no-op shim, paired-PID timeout signaling is removed, `larch_err` still redacts through `redact-secrets.sh --streaming`, and durable log publication redaction remains in the surviving larch-log/design-log paths.

### UPDATED: `scripts/test-implement-anti-polling-rule.sh`
Shrink to retain only the AGENTS.md polling-loop-ban literal pins. Remove Family-B Step-5 background+`breadcrumb-monitor.sh` pairing assertions. Update sibling `.md`.

### UPDATED: `Makefile`
Remove `lint-foreground`, `lint-foreground-markers`, `test-lint-foreground-markers`, `test-breadcrumb-monitor`, `test-breadcrumb-monitor-bash32`, and `test-background-monitor-wait` targets, their `.PHONY` entries, shard memberships, and the aggregate `lint:` dependency. Rebalance shard lists so shard coverage still passes.

### UPDATED: `agent-lint.toml`
Remove exclusions/comment blocks for `lint-foreground-markers.*`, `test-lint-foreground-markers.*`, `test-breadcrumb-monitor*`, `test-background-monitor-wait*`, and `lib-redact-streaming.md`.

### UPDATED: `.pre-commit-config.yaml`
Remove the `lint-foreground-markers` hook.

### UPDATED: `scripts/relevant-checks.sh`
Remove routing for `test-background-monitor-wait` and `test-lint-foreground-markers`. Leave generic redaction/collector routing intact.

### UPDATED: `scripts/test-relevant-checks.sh`
Update expected direct-target/routing assertions to match the removed `relevant-checks.sh` routes.

### UPDATED: grep-based structure tests
Audit `scripts/test-design-structure.sh`, `scripts/test-implement-structure.sh`, `scripts/test-research-structure.sh`, `scripts/test-review-structure.sh`, and any `test-*-anchor*` / `test-references-headers.sh` for assertions against removed surfaces. Relax only breadcrumb-monitor harness, lint-foreground-markers behavior, paired-PID, sentinel, and `lib-redact-streaming` assertions. Do **not** touch skill-fence banner assertions that remain until Stage 4.

### UPDATED: Deleted files
Delete `scripts/lib-redact-streaming.sh`, `scripts/lib-redact-streaming.md`, `scripts/test-breadcrumb-monitor.sh`, `scripts/test-breadcrumb-monitor.md`, `scripts/test-breadcrumb-monitor-bash32.sh`, `scripts/test-breadcrumb-monitor-bash32.md`, `scripts/test-background-monitor-wait.sh`, `scripts/test-background-monitor-wait.md`, `scripts/lint-foreground-markers.sh`, `scripts/lint-foreground-markers.md`, `scripts/test-lint-foreground-markers.sh`, and `scripts/test-lint-foreground-markers.md`.

## Approach
1. Rewire `lib-quiet.sh` first, preserving no-op shims for `larch_quiet_append_done_trap` and `larch_quiet_write_paired_pid_file`.
2. Sweep all known paired-PID/breadcrumb callers, including `dispatch-plan-assessors.sh`.
3. Replace `breadcrumb-monitor.sh` with the no-op shim and rewrite its `.md`.
4. Delete removed libraries/harnesses/lints.
5. Update Makefile, pre-commit, agent-lint, relevant-checks, SECURITY.md, and structure tests.
6. Run a final grep for `lib-redact-streaming`, `lint-foreground-markers`, `test-breadcrumb-monitor`, `test-background-monitor-wait`, `LARCH_PAIRED_PID_FILE`, `LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`, `larch_quiet_append_done_trap`, and `larch_quiet_write_paired_pid_file`; only the intentional shim definitions/docs may remain for the helper names.

## Edge cases
- The shim monitor must always exit 0 so Stage-4-deferred fences still wait on the writer.
- The lib-quiet helper shims must not write files or require env vars.
- `larch_err` fallback must still emit unredacted diagnostics with a warning if `redact-secrets.sh` is missing or non-executable.
- `assess-plan-round.sh` must retain its own `wait "$dispatch_pid"`.
- Makefile shard removal must not leave empty/misnumbered shards.

## Failure modes
- Undefined helper errors from missed callers: mitigated by temporary no-op shims plus caller grep sweep.
- Stale harness routing in `test-relevant-checks.sh`: mitigated by updating the harness with `relevant-checks.sh`.
- Stale security docs: mitigated by updating `SECURITY.md` in this PR.
- CI red from deleted-file references: mitigated by Makefile/agent-lint/pre-commit/structure-test sweeps.
- Redaction regression: mitigated by direct `redact-secrets.sh --streaming` test coverage.

## Testing strategy
- `make lint`
- `make test-lib-quiet`
- `make test-implement-anti-polling-rule`
- `make test-assess-plan-round`
- `make test-dispatch-plan-assessors`
- `make test-relevant-checks`
- Manual: confirm removed Makefile targets no longer exist and final grep leaves only intentional Stage 3 compatibility references.


## Acceptance

- `scripts/breadcrumb-monitor.sh` is a tiny no-op compatibility shim: it consumes all current flags and exits 0 for every invocation shape, so the Stage-4-deferred fences still take their `monitor_rc=0` branch, `wait` the backgrounded writer, and propagate its real exit code. It does not source `lib-quiet.sh` / `lib-larch-log.sh`.
- `scripts/lib-quiet.sh` contains no breadcrumb stream / sentinel / paired-PID plumbing except two intentional no-op compatibility shims (`larch_quiet_append_done_trap`, `larch_quiet_write_paired_pid_file`). `larch_err` / `larch_errf` still redact, now via `redact-secrets.sh --streaming` called directly; the not-executable fallback still emits the diagnostic with a warning.
- `scripts/lib-redact-streaming.{sh,md}`, `scripts/lint-foreground-markers.{sh,md}`, `scripts/test-lint-foreground-markers.{sh,md}`, `scripts/test-breadcrumb-monitor*`, and `scripts/test-background-monitor-wait.{sh,md}` are deleted, with every `Makefile`, `.pre-commit-config.yaml`, `agent-lint.toml`, and `scripts/relevant-checks.sh` reference removed.
- The polling-loop ban survives in `scripts/test-implement-anti-polling-rule.sh` (AGENTS.md literal pins); only the Family-B background+monitor pairing assertions are removed.
- `redact-secrets.sh --streaming` mode is preserved (surviving consumers: `lib-larch-log.sh` and the rewired `larch_err`).
- The committed `larch-logs/<run-id>/breadcrumbs/` forensics directory and the Stage 1 quiet-log bridge are unchanged and still function.
- `skills/design/scripts/assess-plan-round.sh` no longer invokes the monitor and retains its own `wait "$dispatch_pid"`; the design Step 3.6 assessor path still works.
- `make lint` passes (all harness shards green; `test-harness-shards-coverage` accepts the rebalanced shards; no dangling references to deleted files).
- No skill-fence / markdown collapse and no `BASH_AUTHORING.md §4` removal in this piece (deferred to Stage 4 / #3119). `SECURITY.md` is updated in this piece per accepted review FINDING_2 to describe the Stage 3 no-op monitor, removed paired-PID timeout signaling, surviving `larch_err` direct redaction, and surviving durable-log redaction.
diff_lines: 4850
