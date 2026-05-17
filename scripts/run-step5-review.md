# run-step5-review.sh contract

`scripts/run-step5-review.sh` is the `/implement` Step 5 launcher for one
`review-and-fix.sh` round. Its job is to keep the SKILL.md call site small and
derive review context from the implement tmpdir.

Caller: `skills/implement/SKILL.md` Step 5.

Arguments:

- `--implement-tmpdir PATH` is required.
- `--round-num N` is required.

Derived sources:

- `$IMPLEMENT_TMPDIR/session-env.sh`
  - `POST_PLAN_WORKFLOW_PATH`: `SIMPLE` maps to `--panel simple --round-cap 5`;
    `HARD` maps to `--panel hard --round-cap 7`.
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
