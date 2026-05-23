# dispatch-plan-voters.sh Contract

`scripts/dispatch-plan-voters.sh` launches `/design` Step 3 external voter slots through `scripts/dispatch-with-waterfall.sh`.

The script owns only Voter 2 and Voter 3. Each slot is dispatched through the same three-phase waterfall used elsewhere:

- Phase 1: primary external tool (`codex` for Voter 2, `cursor` for Voter 3) when present
- Phase 2: alternate external tool when Phase 1 is absent or fails
- Phase 3: Claude replacement when both external phases are absent or fail

## Behavior

The script writes per-slot prompt files, builds a two-slot NDJSON manifest, and calls `dispatch-with-waterfall.sh` with `--mode description`. It reads `ALL_OUTPUT_FILES`, `ALL_OUTPUT_TOOLS`, and `DISPATCH_OK` from the waterfall's KV output to determine the final path and tool for each voter slot.

Inputs are `--ballot-file`, `--design-tmpdir`, `--codex-available`, `--cursor-available`, and optional `--session-env-path`. The ballot is referenced by path in the generated voter prompts.

## Stdout KV

Stdout is `KEY=value` only:

- `VOTER_2_PATH`, `VOTER_3_PATH`
- `VOTER_PATHS_FILE` — path to `plan-voter-paths.txt` under `--design-tmpdir`, one non-failed voter path per line (atomic write)
- `VOTER_2_TOOL`, `VOTER_3_TOOL`
- `VOTER_2_STATUS`, `VOTER_3_STATUS`
- optional `DEGRADED_PANEL_WARNING`
- `DISPATCH_OK`

`fallback` means the slot completed on Claude after waterfall fallback. `failed` means the final output file is missing, empty, or still narrative-only after the parse-rate retry path. When fewer than 2 effective external-voter slots produce substantive vote output, the script emits a degraded-panel warning so `/design` can compensate with Claude Voter 1.

## Harness

Harness: `scripts/test-dispatch-plan-voters.sh`, wired through `make test-dispatch-plan-voters`.
