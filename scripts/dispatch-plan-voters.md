# dispatch-plan-voters.sh Contract

`scripts/dispatch-plan-voters.sh` launches `/design` Step 3 **plan-review** voter slots: **Voter 1 (Claude)** via `scripts/launch-claude-review.sh`, and **Voters 2–3** (Codex, Cursor) through `scripts/dispatch-with-waterfall.sh`.

- Sources `scripts/lib-plan-voter-coverage.sh`; effective-judge coverage and the per-slot status KV block are emitted by that library.
- Validates `--design-tmpdir` via `scripts/lib-design-tmpdir.sh` (`larch_design_tmpdir_validate`) after argv parsing and before `mkdir -p`.

## Voter 1 (Claude)

- Prompt from `skills/shared/scripts/render-voter-prompt.sh` (`--id-grammar finding-oos`, `--verification-context plan`), same renderer family as Voters 2–3.
- Invokes `"$SCRIPT_DIR/launch-claude-review.sh"` with `--role voter`, `--timing-task-kind claude-plan-voter`, `--timeout 1200`, output at `$DESIGN_TMPDIR/claude-vote-output.txt`.
- On launcher failure or empty output, writes `voter1-diag.txt` and may append via `append-tool-failure.sh` (same pattern as code-review voter diagnostics).

## Voters 2–3 (externals + waterfall)

Each slot is dispatched through the same three-phase waterfall used elsewhere:

- Phase 1: primary external tool (`codex` for Voter 2, `cursor` for Voter 3) when present
- Phase 2: alternate external tool when Phase 1 is absent or fails
- Phase 3: Claude replacement when both external phases are absent or fail

The script writes per-slot prompt files, builds a two-slot NDJSON manifest (Voters 2–3 only), and calls `dispatch-with-waterfall.sh` with `--mode description` and `--timeout 1860`. The 1860s per-voter waterfall cap follows the `skills/design/SKILL.md` anti-pattern #5 timeout family for plan-review/dialectic phases; Voter 1 remains on its separate `launch-claude-review.sh --timeout 1200` path. It reads `ALL_OUTPUT_FILES`, `ALL_OUTPUT_TOOLS`, and `DISPATCH_OK` from the waterfall's KV output to determine the final path and tool for each external slot.

`dispatch-plan-voters.sh` is a top-level Family B writer; paired-PID plumbing
was removed in breadcrumbs Stage 3.

## Parse-rate retries

Sources `scripts/lib-voter-parse-rate.sh` with `LARCH_VPR_*` set for plan ballots (`finding-oos`, `plan` retry prefix). Runs `check_and_retry_voter_parse_rate` for all three voters when a slot is not already `failed`.

## DISPATCH_OK

`DISPATCH_OK` mirrors the waterfall value but is forced to `false` when **Voter 1** ends in `failed` (parity with `dispatch-code-voters.sh`).

## Inputs

`--ballot-file`, `--design-tmpdir`, `--codex-available`, `--cursor-available`, optional `--session-env-path`. The ballot is referenced by path in the generated voter prompts.

## Per-round `--design-tmpdir` Routing

Callers may pass a per-round subdirectory, for example `$DESIGN_TMPDIR/plan-review/round-N`, as `--design-tmpdir`. The dispatcher writes all per-slot outputs inside that directory: `claude-vote-output.txt`, `codex-vote-output.txt`, `cursor-vote-output.txt`, `plan-voter-paths.txt`, and `plan-voter-slots.ndjson`. Existing single-round callers continue to pass the top-level `$DESIGN_TMPDIR`; no new argv flag is required.

## Stdout KV

Stdout is `KEY=value` only:

- `VOTER_1_PATH`, `VOTER_1_TOOL`, `VOTER_1_STATUS`, `VOTER_1_PARSE_RATE_STATUS`
- `VOTER_2_PATH`, `VOTER_3_PATH`
- `VOTER_PATHS_FILE` — when at least one non-failed voter path was written, path to `plan-voter-paths.txt` under `--design-tmpdir`, one path per line (**Voter 1 first** when not failed), atomic write. Omitted when the paths file is empty so downstream callers do not feed an empty `--paths-file` without checking statuses first.
- `VOTER_2_TOOL`, `VOTER_3_TOOL`
- `VOTER_2_STATUS`, `VOTER_3_STATUS`
- `VOTER_2_PARSE_RATE_STATUS`, `VOTER_3_PARSE_RATE_STATUS`
- optional `DEGRADED_PANEL_WARNING`
- optional `WARN=plan-voter slot N (<tool>) failed on usage-limit/quota` (#3378)
- `DISPATCH_OK`

Under `--no-fallback`, external voter slots emit `launched` when `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` from the waterfall name a non-empty final path (including collector retry paths such as `<manifest>-retry.txt` while the manifest path stays empty). `failed` means the final output file is missing, empty, or still narrative-only after the parse-rate retry path. `fallback` is reserved for legacy multi-phase waterfall runs where the final tool is Claude; plan-review voters do not promote `launched` to `fallback` when the tool remains codex or cursor. When fewer than three effective judges produce substantive vote output, the script may emit a degraded-panel warning.

When the panel is degraded, the dispatcher checks whether a failed external voter (codex/cursor) left a usage-limit/quota signature in its `${path}.sidecar` or `${path}.diag` (via `external_is_quota_failure` from `lib-external-launcher-common.sh`). If so it appends the cause to the `DEGRADED_PANEL_WARNING` banner and emits a per-slot quota `WARN` line, so a quota-driven judge-count degradation is not silently attributed to a generic failure (#3378). The matching per-tool failure is also recorded to `execution-issues.md` by `launch-review.sh`.

## Primary callers

- `skills/design/scripts/plan-review-loop.sh` (full plan-review driver)
- Historical references in `skills/design/references/plan-review.md`

## Harness

`scripts/test-dispatch-plan-voters.sh`, wired through `make test-dispatch-plan-voters`.
