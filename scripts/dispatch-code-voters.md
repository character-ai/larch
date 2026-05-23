# dispatch-code-voters.sh

Launches the `/review` judge voting panel through the current waterfall stack. Every review round uses a 3-judge panel (Claude + Codex + Cursor). The Codex-first and Cursor-first slots are always present in the manifest; session-wide Codex absence or per-slot failures waterfall through `dispatch-with-waterfall.sh` (Codex → Cursor → Claude per slot) so unhealthy externals are replaced without shrinking the intended panel shape.

Voter 1 is always Claude and is launched directly through `scripts/launch-claude-review.sh`. Voter 2 and Voter 3 are dispatched as Codex-first and Cursor-first slots through `scripts/dispatch-with-waterfall.sh`, so each external slot can fall through to the alternate external tool and then to Claude when necessary.

## Inputs

- `--ballot-file FILE`: required markdown ballot path.
- `--review-tmpdir DIR`: required output directory.
- `--codex-available true|false`: whether Codex is present for Phase 1.
- `--cursor-available true|false`: whether Cursor is present for Phase 1.
- `--session-env-path FILE`: optional nested-session context.
- `--diff-file FILE`: accepted for backward compatibility but not forwarded to voter launches; voters receive ballot only and Read cited files on demand.
- `--plan-file FILE`: accepted for backward compatibility but not forwarded to voter launches; voters receive ballot only and Read cited files on demand.
- `--round-num N`: positive integer review round number (default `1`). Used for breadcrumbs, retry logging, and per-round artifact paths; it does **not** change which voters are launched.

## Voter-role context shape

All launched voter dispatches use `mode=description` with no inline diff or plan context. The voter prompt directs the model to Read the ballot from disk; cited `<file>:<line>` references in each finding give it everything needed to verify on demand. This keeps the voter context under the 1 MB cap regardless of branch diff size.

## Behavior

Voter 1 runs synchronously via `launch-claude-review.sh` with `--role voter`. Voter 2 (Codex-first) and Voter 3 (Cursor-first) are dispatched together through `dispatch-with-waterfall.sh`:

- Phase 1: primary external tool (Codex for Voter 2, Cursor for Voter 3) when present.
- Phase 2: alternate external tool when Phase 1 is absent or fails.
- Phase 3: Claude replacement when both external phases are absent or fail.

The script always writes both waterfall slots into the NDJSON manifest and calls the waterfall with `--codex-present` mirroring `--codex-available`. `DISPATCH_OK` is set to `false` when Voter 1 fails or any launched waterfall slot hard-fails in Phase 3.

A `voter1_rc=1` exit with non-zero `output_bytes` and empty launcher-stderr indicates the claude CLI received an API-level error response (rate limit, server overload, or transient auth failure) rather than a wrapper validation failure; the CLI exits 1 with JSON error body on stdout while the `launch-claude-review.sh` shell wrapper passes all its own checks and emits nothing to stderr. This shape is distinct from `voter1_rc=2`, which indicates a wrapper validation failure caught inside `launch-claude-review.sh` before the CLI return. When only Voter 1 is affected, the remaining waterfall voters still run under the three-slot contract. See #2433 for the investigation that identified and characterized this pattern.

## Output

- `VOTER_1_PATH`, `VOTER_2_PATH`, `VOTER_3_PATH`: final output path per slot.
- `VOTER_PATHS_FILE`: path to `code-voter-paths.txt` under `--review-tmpdir`, listing non-empty voter paths in slot order (Voter 2 omitted when `VOTER_2_STATUS=skipped` in round 2+); atomic write.
- `VOTER_1_TOOL`, `VOTER_2_TOOL`, `VOTER_3_TOOL`: final tool that produced each slot (`claude`, `codex`, or `cursor`).
- `VOTER_1_STATUS`, `VOTER_2_STATUS`, `VOTER_3_STATUS`: `launched`, `fallback`, or `failed`.
- `VOTER_1_PARSE_RATE_STATUS`, `VOTER_2_PARSE_RATE_STATUS`, `VOTER_3_PARSE_RATE_STATUS`: `OK`, `NOT_SUBSTANTIVE`, or `SKIPPED` when the slot failed before parse-rate evaluation.
- `DEGRADED_PANEL_WARNING`: emitted when effective judges fall below the expected count of **3** for the round.
- `DISPATCH_OK`: `false` when the direct Claude voter fails or any waterfall slot hard-fails in Phase 3.

When `VOTER_1_STATUS=failed` (non-zero exit or empty output from the Claude voter), a Warnings entry is appended to `execution-issues.md` via `append-tool-failure.sh`, capturing `voter1_rc`, the output byte count, the first 200 bytes of `$VOTER_1_PATH` when `voter1_rc != 0` and the file is non-empty (under a `--- first 200 bytes of voter output ---` header), the first 200 bytes of `${VOTER_1_PATH}.diag` when present, and the first 500 bytes of `${VOTER_1_PATH}.launcher-stderr` when present. The launcher-stderr sidecar (captured from the `launch-claude-review.sh` invocation via `2> "${VOTER_1_PATH}.launcher-stderr"`) carries the specific validation message that `launch-claude-subprocess.sh`'s `fail()` emits, so the Warning identifies which check tripped instead of only the exit code. The log path resolves via `LARCH_EXECUTION_ISSUES_LOG`, `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, or `$REVIEW_TMPDIR/execution-issues.md` in that order (#2254, #2292).

After voter statuses are resolved, `check_voter_parse_rate` runs for each non-failed voter. It counts ballot finding IDs that produce `JUDGE_ERROR` from the `vote_for_id` logic against the voter file (i.e., the ballot entry for that finding was absent or unparseable), emits `PARSE_RATE_STATUS=OK|NOT_SUBSTANTIVE` internally, and when the `JUDGE_ERROR` fraction is ≥ 80% logs a Warnings entry with the actual launcher label and first 200 bytes of the file. Parse-rate diags are slot/output-specific sidecars such as `$REVIEW_TMPDIR/codex-vote-output-parse-rate-diag.txt`; each sidecar records the output path and its SHA-256 so tally only suppresses the exact narrative-only file that produced the diag. This detects the failure mode where a voter produced non-empty prose without any parseable `FINDING_N: YES|NO|EXONERATE` lines (#2265).

A harness-only guard in `check_voter_parse_rate` suppresses the `append-tool-failure.sh` call entirely when both conditions hold: `voter_path` is inside `REVIEW_TMPDIR`, and either `REVIEW_TMPDIR` or `voter_path` lives under a harness path segment (`test-dispatch-code-voters.*`, `test-collect-*`, `test-check-*`, `test-tally-*`). The local slot-specific diag sidecar is still written so harness assertions on diag presence continue to pass, and the stderr warning still emits, but no parse-rate warning is appended to any resolved `execution-issues.md` target for those harness paths. This prevents test-fixture diagnostics from leaking into a parent `/implement` run's `execution-issues.md` when linting runs inside an active `/implement` session without suppressing production warnings for unrelated paths that merely contain those substrings (#2363).

When a voter is classified `NOT_SUBSTANTIVE`, the script retries that slot once with a strict structured-vote prefix prepended to the original prompt. The retry writes to a temporary retry output first. If the retry parses cleanly, the script replaces any existing first-pass sidecar and copies the pre-retry (first-pass) content from the canonical voter path to that sidecar (`*-vote-output-first-pass.txt` when the canonical path ends in `.txt`, otherwise `*-first-pass` beside the voter file) before promoting the retry artifact with `mv`, then clears the parse-rate diag file. The copy is best-effort: on `cp` failure the script emits a warning to stderr via `larch_err` but still promotes the retry output so a full disk never blocks the retry path. If the retry also fails or produces no output, the original voter output and original parse-rate diag are preserved and no new first-pass sidecar is written. Slot identity is unchanged: no extra voter slot is added.

The `make_voter_prompt_file` function includes a silent-drop warning: non-matching lines are ignored and voters MUST output exactly one `FINDING_N: YES|NO|EXONERATE` line per finding using the exact ID from the ballot heading.

`fallback` means the slot finished on Claude after a waterfall fallback. For waterfall slots (`VOTER_2_STATUS`, `VOTER_3_STATUS`), `failed` means the final output path is missing or empty after the waterfall completes. For `VOTER_1_STATUS`, `failed` means the direct Claude voter exited non-zero or produced an empty output file; when that failure leaves a non-empty output file behind, the warning flow still records its byte count and a short excerpt for diagnosis.

## Callers and Harness

- Caller: `skills/review/scripts/review-core.sh`
- Harness: `scripts/test-dispatch-code-voters.sh`
