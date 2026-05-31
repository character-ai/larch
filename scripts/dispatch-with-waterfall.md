# scripts/dispatch-with-waterfall.sh — contract

Three-phase per-slot fallback dispatcher for review-style fanout.

Input is an NDJSON slots file. Each row must contain:

- `slot`: stable slot label
- `tool`: primary external tool, `codex` or `cursor`
- `output`: phase-1 output path
- `agent` or `prompt_file`: source prompt for launchers

Rows may include optional metadata such as `weight` and `focus_area`; the dispatcher preserves validation compatibility and ignores those fields at launch time.

Per-slot launcher stderr is captured to `${output}.launch-stderr` (stdout remains `/dev/null`) so launcher-level validation failures are recoverable and surfaced by `collect-agent-results.sh` via the failed-agent stderr tail path (#3202).

## Phases (default)

1. Launch each slot on its assigned external tool when `--<tool>-present true`.
2. Failed or absent phase-1 slots launch on the other present external tool.
3. Remaining slots launch through `scripts/launch-claude-review.sh`.

Each phase is collected with `scripts/collect-agent-results.sh --summary-only`; `STATUS=OK` and `STATUS=cap_hit` settle a slot. Other statuses advance to the next phase, and a phase-3 failure leaves `DISPATCH_OK=false`.

No result is ever copied between slots. Grouped reuse-by-copy (`fallback_group`, group ledger, `.dedup` sidecars) was removed.

## `--no-fallback` (single-phase, drop-on-failure)

When `--no-fallback` is set:

- Only phase 1 runs. Slots whose tool is absent (not `--<tool>-present`) or whose phase-1 collection is not `OK`/`cap_hit` are **dropped** (`final_outputs[idx]` stays empty; `DISPATCH_OK` remains `true` for the run).
- Phase 2 and phase 3 are skipped.
- The paths-file and `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` stdout lists include **only** succeeded slots (empty dropped slots are omitted).

`/design` plan-review, decompose, assessor, and plan-voter panels use this mode with availability-gated slot emission so absent tools are not manifest rows at all.

## Stdout keys

- `PHASE1_SLOTS`, `PHASE2_SLOTS`, `PHASE3_SLOTS`
- `ALL_OUTPUT_FILES`
- `ALL_OUTPUT_FILES_PATH` — absolute/resolved path to the line-oriented paths-file (one output path per line, slot order for non-empty entries under `--no-fallback`); default file is `<slots-file>.output-files`, overridable with `--paths-file <path>`
- `ALL_OUTPUT_TOOLS`
- `FALLBACK_COUNT`
- `COMBINED_FALLBACK_COUNT` (equals `FALLBACK_COUNT`; phase-2 relaunch accounting was removed with grouped reuse)
- `WARN=cost-fallback-exceeded-threshold` when `COMBINED_FALLBACK_COUNT` exceeds `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` (default 3)
- `DISPATCH_OK=true|false`

## Flags

- `--no-fallback` — single-phase, drop-on-failure; see above.
- `--paths-file <path>` — write the final paths list to this path instead of the default `<slots-file>.output-files`. The file is replaced atomically each run (temp file in the same directory + `mv`).
- `--require-result-pattern <regex>` — caller-supplied ERE (`grep -E`) that a `STATUS=OK` result file must match for the slot to settle on the assigned phase tool. Pre-validated once after argv parse against empty stdin; if the pattern is not a valid ERE (`grep` rc > 1) the dispatcher exits **2** with `larch_err` before any slot launches. Applied only to `STATUS=OK`; `STATUS=cap_hit` bypasses the gate so the launcher-side token-budget skip remains terminal. On a `STATUS=OK` pattern miss, the slot is routed through the existing `failed[]` path (phase-1 → phase-2 → phase-3 fallback) unless `--no-fallback` is set (then the slot is dropped). When the flag is unset (default), behavior is unchanged except reuse removal.
- `--require-first-line-pattern <regex>` — same pre-validation and fallback semantics as `--require-result-pattern`, but only the first non-blank line must match.

Current opt-in callers for any-line matching are `skills/design/scripts/decompose-aggregator.sh` and `skills/design/scripts/decompose-panel-dispatch.sh`, both passing `^[[:space:]]*## Recommendation`. The plan-review panel dispatcher uses `--require-first-line-pattern '^[[:space:]]*(schema_version|\{"no_issues_found)'` so narration followed by valid-looking TSV cannot settle the slot.

## Guards

- Empty slots manifest (zero JSON rows) exits **2** with `slots file contains no slot rows` and does not emit stdout KVs or write a paths-file.
- Any resolved final output path containing a literal newline or carriage return exits **2** before writing the paths-file (line-oriented contract).

Regression harness: `scripts/test-dispatch-with-waterfall.sh`. Rip-out guard: `scripts/test-no-grouped-reuse-guard.sh`.
