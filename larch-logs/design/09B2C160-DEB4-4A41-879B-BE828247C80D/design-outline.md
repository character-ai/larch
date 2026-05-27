## Proposed Design Outline

### Goals
- Ship a standalone library script `skills/design/scripts/revise-plan-with-waterfall.sh` that drives a Codex → Cursor → Claude waterfall, emitting an LLM-generated patch, validating it, applying it to `plan.txt` (with revert on failure), and re-running `ACTION=EMIT_PLAN` afterwards.
- Make the script callable from any orchestrator (primary caller is Piece 5 / #2871 `plan-review-loop.sh`) via clear argv mirroring `scripts/dispatch-with-waterfall.sh` conventions.
- Ship a fully-mocked offline harness `scripts/test-revise-plan-with-waterfall.sh` covering waterfall promotion, validator, apply/revert, and emit-plan gate.

### Non-goals
- Integrating the new script into `skills/design/scripts/plan-review-loop.sh` (Piece 5 #2871 owns that).
- Changing existing launcher contracts (`launch-codex-review.sh`, `launch-cursor-review.sh`, `launch-claude-review.sh`).
- Adding new public launcher flags (Piece 1 #2867 already added `--context-files` on the Claude launcher).
- Modifying `plan.txt` grammar, `ACTION=EMIT_PLAN`, or `check-plan-size.sh`.
- Multi-round loop semantics, convergence predicate, per-round artifact promotion, or design-log publish wiring (Piece 5 #2871 owns those).

### Approach sketch
- Argv-driven Bash 3.2 script: `--design-tmpdir`, `--plan-file`, `--findings-file`, `--feature-file`, `--codex-present`, `--cursor-present`, `--round-num`, `--timeout`, plus harness override env vars for launcher paths.
- Per-tier flow: render a structured prompt (plan + accepted findings + feature context as `--context-files`), launch the tier with a per-tier output path under `$DESIGN_TMPDIR/plan-review/round-<N>/revise/`, validate the emitted patch (file present + non-empty + applies cleanly to `plan.txt` + produces a result still passing `ACTION=EMIT_PLAN`), then either accept or fall through to the next tier.
- Apply/revert: snapshot `plan.txt` to `plan.txt.before-revise` before any tier attempts apply; restore on validation/apply failure of every tier.
- Emit-plan gate: on first successful tier, run `ACTION=EMIT_PLAN` via `design-driver.sh` to refresh `$DESIGN_TMPDIR/diff-lines.txt`. Validation failure here counts as a tier failure (waterfall continues).
- Output: stdout KVs via `lib-quiet.sh` (`REVISE_STATUS=ok|failed-no-patch|failed-validation|failed-apply`, `REVISE_TIER=codex|cursor|claude`, `REVISE_PATCH_PATH=…`, `REVISE_PLAN_HASH_BEFORE=…`, `REVISE_PLAN_HASH_AFTER=…`); script always exits 0 on logical outcomes (failure modes signalled in KVs).
- Harness: stub launchers via env-var overrides (`LARCH_TEST_CODEX_LAUNCHER`, `LARCH_TEST_CURSOR_LAUNCHER`, `LARCH_TEST_CLAUDE_LAUNCHER`) that return canned patch fixtures. Each test case exercises one waterfall scenario (Codex ok / Codex bad-patch + Cursor ok / both fail + Claude ok / all three fail / emit-plan gate fails post-apply).

### Surfaces in scope
- `skills/design/scripts/revise-plan-with-waterfall.sh` (new)
- `skills/design/scripts/revise-plan-with-waterfall.md` (new sibling spec)
- `scripts/test-revise-plan-with-waterfall.sh` (new offline harness)
- `scripts/test-revise-plan-with-waterfall.md` (new sibling spec)
- Existing surfaces consumed read-only: `scripts/lib-quiet.sh`, `skills/design/scripts/design-driver.sh` (for `ACTION=EMIT_PLAN`), `scripts/launch-codex-review.sh`, `scripts/launch-cursor-review.sh`, `scripts/launch-claude-review.sh`.

### Open questions
- Exact patch format the LLM tiers emit (unified diff vs full file replacement). The sketch phase should compare both and pick — both are viable with a small validator.
