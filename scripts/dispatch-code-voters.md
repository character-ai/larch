# dispatch-code-voters.sh

Launches the `/review` 3-judge voting panel through the current waterfall stack.

Voter 1 is always Claude and is launched directly through `scripts/launch-claude-review.sh`. Voter 2 and Voter 3 are dispatched as Codex-first and Cursor-first slots through `scripts/dispatch-with-waterfall.sh`, so each external slot can fall through to the alternate external tool and then to Claude when necessary.

## Inputs

- `--ballot-file FILE`: required markdown ballot path.
- `--review-tmpdir DIR`: required output directory.
- `--codex-available true|false`: whether Codex is present for Phase 1.
- `--cursor-available true|false`: whether Cursor is present for Phase 1.
- `--session-env-path FILE`: optional nested-session context.
- `--diff-file FILE`: optional diff context for the Claude voter.
- `--plan-file FILE`: optional plan context for the Claude voter.

## Behavior

Voter 1 runs synchronously via `launch-claude-review.sh`. Voter 2 (Codex-first) and Voter 3 (Cursor-first) are dispatched together through `dispatch-with-waterfall.sh`:

- Phase 1: primary external tool (Codex for Voter 2, Cursor for Voter 3) when present.
- Phase 2: alternate external tool when Phase 1 is absent or fails.
- Phase 3: Claude replacement when both external phases are absent or fail.

The script writes per-slot prompt files, builds a two-slot NDJSON manifest, and reads `ALL_OUTPUT_FILES`, `ALL_OUTPUT_TOOLS`, and `DISPATCH_OK` from the waterfall's KV output. `DISPATCH_OK` is set to `false` when Voter 1 fails or any waterfall slot hard-fails in Phase 3.

## Output

- `VOTER_1_PATH`, `VOTER_2_PATH`, `VOTER_3_PATH`: final output path per slot.
- `VOTER_1_TOOL`, `VOTER_2_TOOL`, `VOTER_3_TOOL`: final tool that produced each slot (`claude`, `codex`, or `cursor`).
- `VOTER_1_STATUS`, `VOTER_2_STATUS`, `VOTER_3_STATUS`: `launched`, `fallback`, or `failed`.
- `DEGRADED_PANEL_WARNING`: emitted when fewer than 3 effective judges produced non-empty output.
- `DISPATCH_OK`: `false` when the direct Claude voter fails or any waterfall slot hard-fails in Phase 3.

When `VOTER_1_STATUS=failed` (non-zero exit or empty output from the Claude voter), a Warnings entry is appended to `execution-issues.md` via `append-tool-failure.sh`, capturing `voter1_rc`, the output byte count, and the first 200 bytes of `${VOTER_1_PATH}.diag` when present. The log path resolves via `LARCH_EXECUTION_ISSUES_LOG`, `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, or `$REVIEW_TMPDIR/execution-issues.md` in that order (#2254).

`fallback` means the slot finished on Claude after a waterfall fallback. `failed` means the final output path is missing or empty.

## Callers and Harness

- Caller: `skills/review/scripts/review-core.sh`
- Harness: `scripts/test-dispatch-code-voters.sh`
