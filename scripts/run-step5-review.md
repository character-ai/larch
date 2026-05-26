# run-step5-review.sh contract

`scripts/run-step5-review.sh` is the `/implement` Step 5 launcher for one
`review-and-fix.sh` round. Its job is to keep the SKILL.md call site small and
derive review context from the implement tmpdir.

Caller: `skills/implement/SKILL.md` Step 5.

`run-step5-review.sh` is a top-level Family B writer for
`LARCH_PAIRED_PID_FILE`; it writes its own PID after installing the done trap
and unsets the env var before invoking nested `review-and-fix.sh`.

**Issue-anchored note**: `/implement` consumes a positional GitHub issue for Preflight; the plan text for review is read from the conventional path `$IMPLEMENT_TMPDIR/plan.txt` (not from `session-env.sh`).

Arguments:

- `--implement-tmpdir PATH` is required.
- `--round-num N` is required.

Derived sources:

- `$IMPLEMENT_TMPDIR/session-env.sh`
  - `CODEX_PRESENT`: forwarded as `--codex-available`.
  - `CURSOR_PRESENT`: forwarded as `--cursor-available`.
  - `LARCH_CLAUDE_PLUGIN_ROOT`: resolves the downstream script path when
    `CLAUDE_PLUGIN_ROOT` is not already set.
  - token/timing keys are re-exported for downstream telemetry compatibility.
- **Round cap**: `WORKFLOW_PATH` is treated as `HARD` for Step 5 (unified review contract). The launcher derives a **base** Step 5 round cap of **5**, then adds the count of prior rounds whose `round-<k>/review-and-fix.env` records `DEGRADED_ROUND=true` (below the current `--round-num`) so degraded panels do not consume a valid review slot. The effective cap is forwarded as `--round-cap` on the `review-and-fix.sh` argv only (this script does **not** emit `--panel` — the unified hard panel is selected inside `review-and-fix.sh` → `review-core.sh`).
- `$IMPLEMENT_TMPDIR/plan.txt`: forwarded as `--plan-file` when present and non-empty.
- `$IMPLEMENT_TMPDIR/session-id`: forwarded as `--run-id`.
- `$IMPLEMENT_TMPDIR/feature-description.txt`: forwarded as `--feature-file`.
- `$IMPLEMENT_TMPDIR/session-env.sh`: forwarded as `--session-env-path`.

Hardcoded downstream flag:

- `--mode diff`

Exceptions: none. Missing, empty, or unreadable `$IMPLEMENT_TMPDIR/plan.txt` (or an unreadable session env) is a launcher error.

Harness: `scripts/test-run-step5-review.sh`.
