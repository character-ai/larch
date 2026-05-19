# dispatch-code-voters.sh

Launches the `/review` 3-judge voting panel through the current waterfall stack.

Voter 1 is always Claude and is launched directly through `scripts/launch-claude-review.sh`. Voter 2 and Voter 3 are dispatched as Codex-first and Cursor-first slots through `scripts/dispatch-with-waterfall.sh`, so each external slot can fall through to the alternate external tool and then to Claude when necessary.

## Inputs

- `--ballot-file FILE`: required markdown ballot path.
- `--review-tmpdir DIR`: required output directory.
- `--codex-available true|false`: whether Codex is present for Phase 1.
- `--cursor-available true|false`: whether Cursor is present for Phase 1.
- `--session-env-path FILE`: optional nested-session context.
- `--diff-file FILE`: accepted for backward compatibility but not forwarded to voter launches; voters receive ballot only and Read cited files on demand.
- `--plan-file FILE`: accepted for backward compatibility but not forwarded to voter launches; voters receive ballot only and Read cited files on demand.

## Voter-role context shape

All three voter dispatches use `mode=description` with no inline diff or plan context. The voter prompt directs the model to Read the ballot from disk; cited `<file>:<line>` references in each finding give it everything needed to verify on demand. This keeps the voter context under the 1 MB cap regardless of branch diff size.

## Behavior

Voter 1 runs synchronously via `launch-claude-review.sh` with `--role voter`. Voter 2 (Codex-first) and Voter 3 (Cursor-first) are dispatched together through `dispatch-with-waterfall.sh`:

- Phase 1: primary external tool (Codex for Voter 2, Cursor for Voter 3) when present.
- Phase 2: alternate external tool when Phase 1 is absent or fails.
- Phase 3: Claude replacement when both external phases are absent or fail.

The script writes per-slot prompt files, builds a two-slot NDJSON manifest, and reads `ALL_OUTPUT_FILES`, `ALL_OUTPUT_TOOLS`, and `DISPATCH_OK` from the waterfall's KV output. `DISPATCH_OK` is set to `false` when Voter 1 fails or any waterfall slot hard-fails in Phase 3.

## Output

- `VOTER_1_PATH`, `VOTER_2_PATH`, `VOTER_3_PATH`: final output path per slot.
- `VOTER_1_TOOL`, `VOTER_2_TOOL`, `VOTER_3_TOOL`: final tool that produced each slot (`claude`, `codex`, or `cursor`).
- `VOTER_1_STATUS`, `VOTER_2_STATUS`, `VOTER_3_STATUS`: `launched`, `fallback`, or `failed`.
- `VOTER_1_PARSE_RATE_STATUS`, `VOTER_2_PARSE_RATE_STATUS`, `VOTER_3_PARSE_RATE_STATUS`: `OK` or `NOT_SUBSTANTIVE` after the one allowed parse-rate retry.
- `DEGRADED_PANEL_WARNING`: emitted when fewer than 3 effective judges produced non-empty output.
- `DISPATCH_OK`: `false` when the direct Claude voter fails or any waterfall slot hard-fails in Phase 3.

When `VOTER_1_STATUS=failed` (non-zero exit or empty output from the Claude voter), a Warnings entry is appended to `execution-issues.md` via `append-tool-failure.sh`, capturing `voter1_rc`, the output byte count, the first 200 bytes of `${VOTER_1_PATH}.diag` when present, and the first 500 bytes of `${VOTER_1_PATH}.launcher-stderr` when present. The launcher-stderr sidecar (captured from the `launch-claude-review.sh` invocation via `2> "${VOTER_1_PATH}.launcher-stderr"`) carries the specific validation message that `launch-claude-subprocess.sh`'s `fail()` emits, so the Warning identifies which check tripped instead of only the exit code. The log path resolves via `LARCH_EXECUTION_ISSUES_LOG`, `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, or `$REVIEW_TMPDIR/execution-issues.md` in that order (#2254, #2292).

After voter statuses are resolved, `check_voter_parse_rate` runs for each non-failed voter. It counts ballot finding IDs that produce NEUTRAL from the `vote_for_id` logic against the voter file, emits `PARSE_RATE_STATUS=OK|NOT_SUBSTANTIVE` internally, and when the NEUTRAL fraction is ≥ 80% logs a Warnings entry with the voter tool name and first 200 bytes of the file. This detects the failure mode where a voter produced non-empty prose without any parseable `FINDING_N: YES|NO|EXONERATE` lines (#2265).

When a voter is classified `NOT_SUBSTANTIVE`, the script retries that slot once with a strict structured-vote prefix prepended to the original prompt. The retry writes to a temporary retry output first. If the retry parses cleanly, the canonical voter output path is replaced and the parse-rate diag file is cleared. If the retry also fails or produces no output, the original voter output and original parse-rate diag are preserved. Slot identity is unchanged: no extra voter slot is added.

The `make_voter_prompt_file` function includes a silent-drop warning: non-matching lines are ignored and voters MUST output exactly one `FINDING_N: YES|NO|EXONERATE` line per finding using the exact ID from the ballot heading.

`fallback` means the slot finished on Claude after a waterfall fallback. `failed` means the final output path is missing or empty.

## Callers and Harness

- Caller: `skills/review/scripts/review-core.sh`
- Harness: `scripts/test-dispatch-code-voters.sh`
