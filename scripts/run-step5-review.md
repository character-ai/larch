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
- **Round cap**: The launcher uses a flat Step 5 round cap of **5** as a hard ceiling. The cap is forwarded unchanged as `--round-cap` on the `review-and-fix.sh` argv only (this script does **not** emit `--panel` — panel selection lives inside `review-and-fix.sh` → `review core`).
- `$IMPLEMENT_TMPDIR/plan.txt`: forwarded as `--plan-file` when present and non-empty.
- `$IMPLEMENT_TMPDIR/session-id`: forwarded as `--run-id`.
- `$IMPLEMENT_TMPDIR/feature-description.txt`: forwarded as `--feature-file`.
- `$IMPLEMENT_TMPDIR/session-env.sh`: forwarded as `--session-env-path`.
- `$IMPLEMENT_TMPDIR/scout-coder-manifest.json`: forwarded as
  `--pre-scouted-manifest` only when
  `$IMPLEMENT_TMPDIR/step2-external-scout-eligible.txt` exists and mode is not
  `mav-apply`.
- `$IMPLEMENT_TMPDIR/step2-external-scout-eligible.txt`: the Step 5 pre-scout
  eligibility marker. Missing marker does not force `--dynamic-archetypes 0`;
  `review-and-fix.sh` keeps the implement-mode default of 3 dynamic archetypes
  and may run the legacy live scout.
- `$IMPLEMENT_TMPDIR/step2-scout-coder-status.env`: when present, supplies
  `SCOUT_CODER_STATUS` for pre-scout forwarding. `--pre-scouted-manifest` is
  forwarded only when the marker exists and `SCOUT_CODER_STATUS=ok`.
- `$IMPLEMENT_TMPDIR/step2-spawn-coder.txt`: remains the cross-coder tmpdir
  guard and does not enable Step 5 dynamic review by itself.

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

## Escalation ledger behavior

`run-step5-review.sh` preserves the child review KV stream while detecting `STEP5_REVIEW_STATUS`. For `coder-main-agent-required`, the wrapper owns the canonical `record-escalation` call before returning control to Main Claude. Ledger write failures fail open through fallback evidence or a tagged `record-escalation` Tool Failure.

For `main-agent-vote-required`, the wrapper emits prompt-side ledger-ready fields and does not record directly:

- `STEP5_REVIEW_LEDGER_READY=true`
- `STEP5_REVIEW_LEDGER_SITE=step5-mav`
- `STEP5_REVIEW_LEDGER_TRIGGER=main-agent-vote-required`
- `STEP5_REVIEW_LEDGER_STEP=5`
- `STEP5_REVIEW_LEDGER_PHASE=review`
- `STEP5_REVIEW_LEDGER_DISPATCHER=run-step5-review`
- `STEP5_REVIEW_LEDGER_EXIT_CODE=<n>`
- `STEP5_REVIEW_LEDGER_FAILURE_DETAIL_LOG=<path>` when available
