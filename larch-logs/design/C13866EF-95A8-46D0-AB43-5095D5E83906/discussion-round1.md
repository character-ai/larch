## Decision 1: Interim-window handling for the deleted monitor (Stage 3 → Stage 4)
- **Question**: Deleting `breadcrumb-monitor.sh` leaves 13 skill-fence/doc invocations (Stage 4 territory, #3119) pointing at a missing script until Stage 4 lands. CI stays green, but a live `/implement` (ship-pr/dispatch) or `/design` (collector/plan-review) run on that build would hit exit 127. Delete outright, or keep a no-op shim?
- **Resolution**: Keep a no-op shim. Rewrite `breadcrumb-monitor.sh` as a tiny no-op that parses its `--stream/--done-sentinel/--status-file/--quiet-log/--surfaced-sentinel/--paired-pid-file` (and any other) args and exits 0, so existing background+monitor fences keep working (`monitor_rc=0` → the backgrounded writer is `wait`ed and its real exit code propagates). Stage 4 (#3119) deletes the shim and the fences together.
- **Source**: user

## Decision 2: larch_err / larch_errf operator-diagnostic redaction
- **Question**: `lib-redact-streaming.sh` (slated for deletion) is also the secret-scrubber behind `larch_err`/`larch_errf` in `lib-quiet.sh` (added for breadcrumb parity, #2807). Committed quiet logs are redacted independently at commit time by `lib-larch-log.sh`. Revert `larch_err` to plain stderr, or preserve redaction?
- **Resolution**: Preserve via direct call. Delete only the `lib-redact-streaming.sh` wrapper; rewire `larch_quiet_redact_diagnostic_stream` to call `redact-secrets.sh --streaming --state-file <state>` directly (the same engine `lib-larch-log.sh:393` uses). Defense-in-depth on operator diagnostics is retained.
- **Source**: user

## Decision 3: redact-secrets.sh --streaming mode
- **Question**: The issue says `--streaming` "may have no remaining consumer after breadcrumbs go and can be removed; verify during partition." Verify.
- **Resolution**: KEEP `--streaming`. It has surviving, breadcrumb-independent consumers: `lib-larch-log.sh:393` (`larch-log.sh commit` redaction) and — per Decision 2 — the rewired `larch_err` path. Do NOT remove `--streaming` mode or its `test-redact-secrets.sh` coverage.
- **Source**: codebase

## Decision 4: Scope boundary vs sibling partition pieces
- **Question**: What is in-scope for Stage 3 vs deferred to Stage 4 (#3119) / Stage 5 (#3120)?
- **Resolution**: Stage 3 = `scripts/*.sh` + lint scripts + their test harnesses + `Makefile` + `agent-lint.toml` + `scripts/relevant-checks.sh` + grep-based structure tests ONLY. Defer to Stage 4: skill-fence (`skills/**`, `.claude/**`, `.claude/rules/*.md`) Family-B fence collapse, `BASH_AUTHORING.md §4` removal, `AGENTS.md`/`SECURITY.md`/`docs/**` trims, closing #2919. Defer to Stage 5: #3063 hardening carry-overs. This piece makes NO markdown/SKILL.md/public-doc edits.
- **Source**: codebase (sibling issues #3119 / #3120) + user (replace-via-full-flow)

## Decision 5: assess-plan-round.sh runtime monitor consumer
- **Question**: `skills/design/scripts/assess-plan-round.sh` invokes `breadcrumb-monitor.sh` internally (lines 186/202) — an executable, not a doc fence. How to handle?
- **Resolution**: Clean it in this piece (it is a dispatch script, Stage 3 territory). Drop the `MONITOR_SH` definition + monitor call and the `LARCH_BREADCRUMB_STREAM`/`LARCH_DONE_SENTINEL`/`LARCH_STATUS_FILE`/`LARCH_BREADCRUMBS_SURFACED_FILE`/`LARCH_PAIRED_PID_FILE` exports; keep the background dispatch, its own `wait "$dispatch_pid"` (already provides completion), and the `LARCH_QUIET_LOG_FILE` forensics redirect. Update its harnesses (`test-assess-plan-round.sh` / `test-dispatch-plan-assessors.sh`) to match. (Even with the shim present, this internal consumer is fully cleaned so the rip-out is real at the executable layer.)
- **Source**: codebase

## Decision 6: Hard constraints — what must not break / must be preserved
- **Question**: What existing behavior must be preserved?
- **Resolution**: (a) Committed `larch-logs/<run-id>/breadcrumbs/` forensics directory + the quiet-log bridge (Stage 1, #3116) must keep working. (b) `redact-secrets.sh` + `redact-tmpdir-paths.sh` stay. (c) The residual polling-loop ban must be retained when `lint-foreground-markers.sh` / `test-lint-foreground-markers.sh` / `test-implement-anti-polling-rule.sh` are shrunk. (d) CI must stay green after this piece alone (`make lint` + harness shards). (e) The no-op shim must keep the existing fence wait-propagation semantics intact (exit 0 so `monitor_rc=0`).
- **Source**: issue + user
