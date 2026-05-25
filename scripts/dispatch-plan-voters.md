# dispatch-plan-voters.sh Contract

`scripts/dispatch-plan-voters.sh` launches `/design` Step 3 **plan-review** voter slots: **Voter 1 (Claude)** via `scripts/launch-claude-review.sh`, and **Voters 2–3** (Codex, Cursor) through `scripts/dispatch-with-waterfall.sh`.

## Voter 1 (Claude)

- Prompt from `skills/shared/scripts/render-voter-prompt.sh` (`--id-grammar finding-oos`, `--verification-context plan`), same renderer family as Voters 2–3.
- Invokes `"$SCRIPT_DIR/launch-claude-review.sh"` with `--role voter`, `--timing-task-kind claude-plan-voter`, `--timeout 1200`, output at `$DESIGN_TMPDIR/claude-vote-output.txt`.
- On launcher failure or empty output, writes `voter1-diag.txt` and may append via `append-tool-failure.sh` (same pattern as code-review voter diagnostics).

## Voters 2–3 (externals + waterfall)

Each slot is dispatched through the same three-phase waterfall used elsewhere:

- Phase 1: primary external tool (`codex` for Voter 2, `cursor` for Voter 3) when present
- Phase 2: alternate external tool when Phase 1 is absent or fails
- Phase 3: Claude replacement when both external phases are absent or fail

The script writes per-slot prompt files, builds a two-slot NDJSON manifest (Voters 2–3 only), and calls `dispatch-with-waterfall.sh` with `--mode description`. It reads `ALL_OUTPUT_FILES`, `ALL_OUTPUT_TOOLS`, and `DISPATCH_OK` from the waterfall's KV output to determine the final path and tool for each external slot.

## Parse-rate retries

Sources `scripts/lib-voter-parse-rate.sh` with `LARCH_VPR_*` set for plan ballots (`finding-oos`, `plan` retry prefix). Runs `check_and_retry_voter_parse_rate` for all three voters when a slot is not already `failed`.

Substantive parse-rate success requires only a parseable `YES`/`NO`/`EXONERATE` vote token for each ballot id. Missing rating axes leave blank forensic TSV cells later, but they do not by themselves downgrade the slot to `NOT_SUBSTANTIVE`.

## DISPATCH_OK

`DISPATCH_OK` mirrors the waterfall value but is forced to `false` when **Voter 1** ends in `failed` (parity with `dispatch-code-voters.sh`).

## Inputs

`--ballot-file`, `--design-tmpdir`, `--codex-available`, `--cursor-available`, optional `--session-env-path`. The ballot is referenced by path in the generated voter prompts.

## Stdout KV

Stdout is `KEY=value` only:

- `VOTER_1_PATH`, `VOTER_1_TOOL`, `VOTER_1_STATUS`, `VOTER_1_PARSE_RATE_STATUS`
- `VOTER_2_PATH`, `VOTER_3_PATH`
- `VOTER_PATHS_FILE` — when at least one non-failed voter path was written, path to `plan-voter-paths.txt` under `--design-tmpdir`, one path per line (**Voter 1 first** when not failed), atomic write. Omitted when the paths file is empty so downstream callers do not feed an empty `--paths-file` without checking statuses first.
- `VOTER_2_TOOL`, `VOTER_3_TOOL`
- `VOTER_2_STATUS`, `VOTER_3_STATUS`
- `VOTER_2_PARSE_RATE_STATUS`, `VOTER_3_PARSE_RATE_STATUS`
- optional `DEGRADED_PANEL_WARNING`
- `DISPATCH_OK`

`fallback` means the slot completed on Claude after waterfall fallback. `failed` means the final output file is missing, empty, or still narrative-only after the parse-rate retry path. When fewer than three effective judges produce substantive vote output, the script may emit a degraded-panel warning.

## Primary callers

- `skills/design/scripts/plan-review-loop.sh` (full plan-review driver)
- Historical references in `skills/design/references/plan-review.md`

## Harness

`scripts/test-dispatch-plan-voters.sh`, wired through `make test-dispatch-plan-voters`.
