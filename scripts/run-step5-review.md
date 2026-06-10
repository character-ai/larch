# run-step5-review.sh contract

`scripts/run-step5-review.sh` is the `/implement` Step 5 launcher for one
`review-and-fix.sh` round. Its job is to keep the SKILL.md call site small and
derive review context from the implement tmpdir.

Caller: `skills/implement/SKILL.md` Step 5.

`run-step5-review.sh` is a top-level Family B launcher; paired-PID plumbing was
removed in breadcrumbs Stage 3 (skill fences still carry the historical monitor
pair until Stage 4).

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
- **Round cap**: The launcher uses a flat Step 5 round cap of **5** as a hard ceiling. The cap is forwarded unchanged as `--round-cap` on the `review-and-fix.sh` argv only (this script does **not** emit `--panel` — panel selection lives inside `review-and-fix.sh` → `review-core.sh`).
- `$IMPLEMENT_TMPDIR/plan.txt`: forwarded as `--plan-file` when present and non-empty.
- `$IMPLEMENT_TMPDIR/session-id`: forwarded as `--run-id`.
- `$IMPLEMENT_TMPDIR/feature-description.txt`: forwarded as `--feature-file`.
- `$IMPLEMENT_TMPDIR/session-env.sh`: forwarded as `--session-env-path`.

Progress hook marker:

- In `--mode loop`, the launcher installs an EXIT trap that writes
  `$IMPLEMENT_TMPDIR/progress/done` when the Step 5 loop process exits on any
  path. The progress-report engine treats that marker as "Step 5 is no longer
  active" and falls through to the generic renderer. Single-round and MAV-apply
  modes do not write the marker.

Hardcoded downstream flag:

- `--mode diff`

Exceptions: none. Missing, empty, or unreadable `$IMPLEMENT_TMPDIR/plan.txt` (or an unreadable session env) is a launcher error.

Harness: `scripts/test-run-step5-review.sh`.

Loop resumes with `--starting-round > 1` emit a timing-only `Step 5 — code review` mark before invoking `review-and-fix.sh`, re-establishing a Step 5 interval without writing token-ledger telemetry.
