# run-step5-review.sh contract

`scripts/run-step5-review.sh` is the `/implement` Step 5 launcher for one
`review-and-fix.sh` round. Its job is to keep the SKILL.md call site small and
derive review context from the implement tmpdir.

Caller: `skills/implement/SKILL.md` Step 5.

**Issue-anchored note**: `/implement` consumes a positional GitHub issue for Preflight; `PLAN_FILE` in `session-env.sh` is still the materialized plan excerpt for review prompts — `run-step5-review.sh` does not re-parse argv for a verbal feature tail.

Arguments:

- `--implement-tmpdir PATH` is required.
- `--round-num N` is required.

Derived sources:

- `$IMPLEMENT_TMPDIR/session-env.sh`
  - `POST_PLAN_WORKFLOW_PATH`: must be `SIMPLE` or `HARD`. The launcher derives a
    **base** Step 5 round cap of **5** for both values, then adds the count of
    prior rounds whose `round-<k>/review-and-fix.env` records
    `DEGRADED_ROUND=true` (below the current `--round-num`) so degraded panels do
    not consume a valid review slot. The effective cap is forwarded as
    `--round-cap` on the `review-and-fix.sh` argv only (this script does **not**
    emit `--panel` — the unified hard panel is selected inside
    `review-and-fix.sh` → `review-core.sh`).
  - `CODEX_PRESENT`: forwarded as `--codex-available`.
  - `CURSOR_PRESENT`: forwarded as `--cursor-available`.
  - `PLAN_FILE`: forwarded as `--plan-file`.
  - `LARCH_CLAUDE_PLUGIN_ROOT`: resolves the downstream script path when
    `CLAUDE_PLUGIN_ROOT` is not already set.
  - token/timing keys are re-exported for downstream telemetry compatibility.
- `$IMPLEMENT_TMPDIR/session-id`: forwarded as `--run-id`.
- `$IMPLEMENT_TMPDIR/feature-description.txt`: forwarded as `--feature-file`.
- `$IMPLEMENT_TMPDIR/session-env.sh`: forwarded as `--session-env-path`.

Hardcoded downstream flag:

- `--mode diff`

Exceptions: none. All review context is expected to be available from the
session env and conventional tmpdir artifacts. Missing `POST_PLAN_WORKFLOW_PATH`
or `PLAN_FILE` is a launcher error.

Harness: `scripts/test-run-step5-review.sh`.
