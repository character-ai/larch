# dispatch-code-voters.sh

Launches the `/review` judge voting panel: Claude (always) plus each **available** external (Codex, Cursor). The panel uses **shrink-not-backfill** — an unavailable external is dropped, never replaced by a duplicate judge (the alternate external or an extra Claude). The eligible panel is therefore Claude plus the number of available externals: the full tier when both vendors are up, the unanimous tier when one is up, and the binding single-judge tier when both are down. The Codex and Cursor slots are always written to the manifest, but `dispatch-with-waterfall.sh` is invoked with `--no-fallback`, so an absent or failed external slot is dropped from the result set rather than back-filled. The acceptance-threshold table in `skills/shared/voting-protocol.md` compensates for the smaller panel; a panel that shrank solely from vendor unavailability is the designed state, not a degradation.

Voter 1 is always Claude (the floor) and is launched directly through `scripts/launch-claude-review.sh`. Voter 2 (Codex) and Voter 3 (Cursor) are dispatched through `scripts/dispatch-with-waterfall.sh --no-fallback`: each slot launches only when its vendor is available, and an unavailable or failed external is dropped, not back-filled. The dispatcher maps the waterfall's surviving outputs back to the Codex/Cursor slots **by tool name** (not by position), because `--no-fallback` removes dropped slots from `ALL_OUTPUT_FILES` and positional indexing would otherwise mis-assign a lone survivor.

Before invoking nested `dispatch-with-waterfall.sh`, the script defensively
does not allocate paired-PID files; this script is not a top-level
Family B writer.

The `dispatch-with-waterfall.sh` invocation is wrapped with `set +e`/`set -e` so a non-zero exit (e.g. when a reviewer launcher exits abnormally mid-run) does not abort the dispatch before the voter tally step. A non-zero waterfall exit is logged via `larch_err` and treated as an empty waterfall result; the post-wait size checks then classify individual voters as failed or launched based on file presence.

## Prompt integrity

`make_voter_prompt_file` checks the exit code of `render-voter-prompt.sh` and asserts that the rendered prompt contains `Read the ballot from this path` before launching any voter. Either failure aborts with a loud `larch_err` message and exit 2, preventing silently truncated prompts from reaching voters.

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

All launched voter dispatches use `mode=description`. The voter prompt is rendered by `${CLAUDE_PLUGIN_ROOT}/skills/shared/scripts/render-voter-prompt.sh` (`--id-grammar finding-oos`, `--verification-context code`; see `skills/shared/scripts/render-voter-prompt.md`) and directs the model to Read the ballot plus bounded regular-file copies of diff/plan context produced under `--review-tmpdir` (`diff-context.txt`, `plan-context.txt`). Cited `<file>:<line>` references in each finding give it everything needed to verify on demand while keeping the voter context under the byte caps enforced by `make_bounded_context_copy`.

## Behavior

Voter 1 runs synchronously via `launch-claude-review.sh` with `--role voter`. Voter 2 (Codex) and Voter 3 (Cursor) are dispatched together through `dispatch-with-waterfall.sh --no-fallback`:

- A slot launches only when its vendor is available (`--codex-present` mirrors `--codex-available`, `--cursor-present` mirrors `--cursor-available`).
- An unavailable or failed external slot is **dropped** (`tool-absent` for an absent vendor; a collector/format failure for an available-but-broken one), not back-filled to the alternate external or to Claude. Dropped slots are omitted from `ALL_OUTPUT_FILES`.

The script always writes both Codex and Cursor slots into the NDJSON manifest (the waterfall decides per-slot whether to launch). Each surviving output is mapped back to its slot by tool name. An external that was **unavailable** is marked `VOTER_<n>_STATUS=skipped`; an external that was **available but produced no usable output** is marked `failed`. `DISPATCH_OK` is set to `false` only when Voter 1 (the Claude floor) fails — externals are optional under shrink-not-backfill, so their absence or failure does not flip `DISPATCH_OK`.

A `voter1_rc=1` exit with non-zero `output_bytes` and empty launcher-stderr indicates the claude CLI received an API-level error response (rate limit, server overload, or transient auth failure) rather than a wrapper validation failure; the CLI exits 1 with JSON error body on stdout while the `launch-claude-review.sh` shell wrapper passes all its own checks and emits nothing to stderr. This shape is distinct from `voter1_rc=2`, which indicates a wrapper validation failure caught inside `launch-claude-review.sh` before the CLI return. When only Voter 1 is affected, the available external voters still run. See #2433 for the investigation that identified and characterized this pattern.

## Voter `.done` sentinel barrier

Before assigning size-based `failed` statuses, the dispatcher waits for the `.done` sentinel for each launched voter by calling [scripts/wait-for-reviewers.sh](wait-for-reviewers.md). The barrier is deliberately positioned after voter path/tool/status binding and before any `-s` output checks, so outputs that become visible while their sentinel is still pending are re-evaluated after completion (#2973). Slots already marked `skipped` are preserved across the post-barrier size pass; an intentionally skipped Voter 2 or Voter 3 (its external vendor was unavailable) is never downgraded to `failed` just because its output path is empty.

The wait captures stdout because `wait-for-reviewers.sh` reports `TIMEOUT <idx> <basename>` rows on stdout and exits 0 for normal timeout operation. Timeout rows are logged with `larch_err`; exit 1 is treated separately as a usage/config error and is also logged. Both paths are non-blocking: the dispatcher proceeds with whatever files exist and lets the post-barrier size checks preserve degraded-quorum behavior. The default timeout is 60 seconds and can be overridden with `LARCH_VOTER_WAIT_TIMEOUT`. The branch uses `if/fi` guards so the normal `_wait_rc=0` path remains safe under `set -e`.

## Output

- `VOTER_1_PATH`, `VOTER_2_PATH`, `VOTER_3_PATH`: final output path per slot.
- `VOTER_PATHS_FILE`: path to `code-voter-paths.txt` under `--review-tmpdir`, listing non-empty voter paths in slot order. A skipped external (`VOTER_2_STATUS=skipped` or `VOTER_3_STATUS=skipped`) is omitted, so the file holds 1–3 lines depending on vendor availability (1 = Claude only when both externals are down); atomic write.
- `VOTER_1_TOOL`, `VOTER_2_TOOL`, `VOTER_3_TOOL`: tool assigned to each slot (`claude` for Voter 1; `codex`/`cursor` for Voters 2/3, retained even when that slot is `skipped`). Externals never become `claude` under shrink-not-backfill.
- `VOTER_1_STATUS`, `VOTER_2_STATUS`, `VOTER_3_STATUS`: `launched`, `skipped` (external vendor unavailable — shrink-not-backfill), or `failed`. Voter 1 (Claude) is never `skipped`.
- `VOTER_1_PARSE_RATE_STATUS`, `VOTER_2_PARSE_RATE_STATUS`, `VOTER_3_PARSE_RATE_STATUS`: `OK`, `NOT_SUBSTANTIVE`, or `SKIPPED` when the slot failed or was skipped before parse-rate evaluation.
- `DEGRADED_PANEL_WARNING`: emitted when effective judges fall below the **eligible** panel size, which is `1` (Claude) plus the number of available externals. A panel that shrank solely because a vendor was unavailable is **not** degraded (one vendor down → 2/2, both down → 1/1: no warning); only a genuine failure of an *available* judge (e.g. 1/2 or 0/1) raises it.
- `DISPATCH_OK`: `false` only when the direct Claude voter (the floor) fails; an absent or failed external does not flip it.

When `VOTER_1_STATUS=failed` (non-zero exit or empty output from the Claude voter), a Warnings entry is appended to `execution-issues.md` via `append-tool-failure.sh`, capturing `voter1_rc`, the output byte count, the first 200 bytes of `$VOTER_1_PATH` when `voter1_rc != 0` and the file is non-empty (under a `--- first 200 bytes of voter output ---` header), the first 200 bytes of `${VOTER_1_PATH}.diag` when present, and the first 500 bytes of `${VOTER_1_PATH}.launcher-stderr` when present. The launcher-stderr sidecar (captured from the `launch-claude-review.sh` invocation via `2> "${VOTER_1_PATH}.launcher-stderr"`) carries the specific validation message that `launch-claude-subprocess.sh`'s `fail()` emits, so the Warning identifies which check tripped instead of only the exit code. The log path resolves via `LARCH_EXECUTION_ISSUES_LOG`, `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, or `$REVIEW_TMPDIR/execution-issues.md` in that order (#2254, #2292).

After voter statuses are resolved, `check_voter_parse_rate` runs for each non-failed voter. It counts ballot item IDs (`FINDING_N` and `OOS_N`) that produce `JUDGE_ERROR` from the `vote_for_id` logic against the voter file (i.e., the ballot entry for that item was absent or unparseable), emits `PARSE_RATE_STATUS=OK|NOT_SUBSTANTIVE` internally, and when the `JUDGE_ERROR` fraction is ≥ 80% logs a Warnings entry with the actual launcher label and first 200 bytes of the file. Parse-rate diags are slot/output-specific sidecars such as `$REVIEW_TMPDIR/codex-vote-output-parse-rate-diag.txt`; each sidecar records the output path and its SHA-256 so tally only suppresses the exact narrative-only file that produced the diag. This detects the failure mode where a voter produced non-empty prose without any parseable `FINDING_N:` or `OOS_N:` vote lines (#2265).

A harness-only guard in `check_voter_parse_rate` suppresses the `append-tool-failure.sh` call entirely when both conditions hold: `voter_path` is inside `REVIEW_TMPDIR`, and either `REVIEW_TMPDIR` or `voter_path` lives under a harness path segment (`test-dispatch-code-voters.*`, `test-collect-*`, `test-check-*`, `test-tally-*`). The local slot-specific diag sidecar is still written so harness assertions on diag presence continue to pass, and the stderr warning still emits, but no parse-rate warning is appended to any resolved `execution-issues.md` target for those harness paths. This prevents test-fixture diagnostics from leaking into a parent `/implement` run's `execution-issues.md` when linting runs inside an active `/implement` session without suppressing production warnings for unrelated paths that merely contain those substrings (#2363).

When a voter is classified `NOT_SUBSTANTIVE`, the script retries that slot once with a strict structured-vote prefix prepended to the original prompt. The retry writes to a temporary retry output first. If the retry parses cleanly, the script replaces any existing first-pass sidecar and copies the pre-retry (first-pass) content from the canonical voter path to that sidecar (`*-vote-output-first-pass.txt` when the canonical path ends in `.txt`, otherwise `*-first-pass` beside the voter file) before promoting the retry artifact with `mv`, then clears the parse-rate diag file. The copy is best-effort: on `cp` failure the script emits a warning to stderr via `larch_err` but still promotes the retry output so a full disk never blocks the retry path. If the retry also fails or produces no output, the original voter output and original parse-rate diag are preserved and no new first-pass sidecar is written. Slot identity is unchanged: no extra voter slot is added.

The `make_voter_prompt_file` function includes a silent-drop warning: non-matching lines are ignored and voters MUST output exactly one `FINDING_N:` or `OOS_N:` vote line per ballot item using the exact ID from the ballot heading, with the four rating axes on the same line.

`skipped` means the external vendor was unavailable, so the slot was intentionally not launched and no duplicate judge replaces it (shrink-not-backfill). For external slots (`VOTER_2_STATUS`, `VOTER_3_STATUS`), `failed` means the vendor was available but the final output path is missing or empty after the waterfall completes. For `VOTER_1_STATUS`, `failed` means the direct Claude voter exited non-zero or produced an empty output file; when that failure leaves a non-empty output file behind, the warning flow still records its byte count and a short excerpt for diagnosis.

## Callers and Harness

- Caller: `skills/review/scripts/review-core.sh`
- Harness: `scripts/test-dispatch-code-voters.sh`
