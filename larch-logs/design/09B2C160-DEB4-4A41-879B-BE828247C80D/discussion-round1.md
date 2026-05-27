## Decision 1: Failure-reporting contract when all three waterfall tiers fail
- **Question**: When Codex → Cursor → Claude all fail to emit a valid patch for one round, how does `revise-plan-with-waterfall.sh` report?
- **Resolution**: Always exit 0 and emit `REVISE_STATUS=ok|failed-no-patch|failed-validation|failed-apply` (and related KVs) via the quiet contract stream. Caller treats `failed-*` as a degraded round and keeps `plan.txt` unchanged.
- **Source**: user (Step 1c)

## Decision 2: Test harness execution mode
- **Question**: How should `scripts/test-revise-plan-with-waterfall.sh` exercise the three waterfall tiers?
- **Resolution**: Fully mocked — stub Codex/Cursor/Claude launchers via env-var path overrides. Harness runs offline with deterministic fixtures covering patch validator, apply/revert, waterfall promotion, and emit-plan gate. No live LLM calls.
- **Source**: user (Step 1c)

## Decision 3: Scope boundary — `revise-plan-with-waterfall.sh` is a standalone library script
- **Question**: Is `revise-plan-with-waterfall.sh` an internal helper for Piece 5 (`plan-review-loop.sh`) or a generally-callable utility?
- **Resolution**: Standalone library script — invokable from any caller via clear argv (mirroring `scripts/dispatch-with-waterfall.sh`). Piece 5 (#2871) is the primary caller. Issue title "Standalone revision waterfall" confirms.
- **Source**: codebase (sibling script `scripts/dispatch-with-waterfall.sh` precedent + issue title)

## Decision 4: Out-of-scope: integration wiring with `plan-review-loop.sh`
- **Question**: Does this issue land integration code into `plan-review-loop.sh` (Piece 5)?
- **Resolution**: No. Integration with the multi-round driver belongs to Piece 5 (#2871). This issue ships ONLY the standalone script + harness + sibling .md docs.
- **Source**: issue body (Piece 5 #2871 explicitly owns `plan-review-loop.sh` extensions and integration tests)

## Decision 5: Hard constraints to preserve
- **Question**: What invariants must this script respect?
- **Resolution**:
  - Bash 3.2 portability (`BASH_AUTHORING.md` §3).
  - Quiet contract stream via `lib-quiet.sh` (`emit_kv`, `emit_breadcrumb`).
  - Existing `plan.txt` grammar (final `diff_lines: <N>` trailer; `### NEW:/UPDATED:/REWRITTEN:` headings parsed by scout/check-plan-size).
  - `ACTION=EMIT_PLAN` gate is re-run after a successful patch apply so `diff-lines.txt` stays in sync (this is the "emit-plan gate" called out in the issue scope).
  - Codex / Cursor / Claude launchers use existing surfaces (`launch-codex-review.sh`, `launch-cursor-review.sh`, `launch-claude-review.sh --context-files` newly available from Piece 1 #2867).
- **Source**: codebase + repo conventions

Recorded 5 decisions resolved (2 from user Step 1c, 3 from codebase / short-circuit).
