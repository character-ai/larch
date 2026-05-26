# scripts/dispatch-with-waterfall.sh — contract

Three-phase per-slot fallback dispatcher for review-style fanout.

Input is an NDJSON slots file. Each row must contain:

- `slot`: stable slot label
- `tool`: primary external tool, `codex` or `cursor`
- `output`: phase-1 output path
- `agent` or `prompt_file`: source prompt for launchers

Rows may include optional metadata such as `weight` and `focus_area`; the dispatcher preserves validation compatibility and ignores those fields at launch time.

Rows may also include optional `fallback_group`. Empty or absent
`fallback_group` keeps legacy behavior: no group ledger is created and the slot
participates in the normal per-slot waterfall. When at least one row has a
group, the dispatcher writes `<dirname-of-resolved-slots-file>/waterfall-group-results.tsv`
as grouped slots settle.

Phases:

1. Launch each slot on its assigned external tool when `--<tool>-present true`.
2. Failed or absent phase-1 slots launch on the other present external tool.
3. Remaining slots launch through `scripts/launch-claude-review.sh`.

Each phase is collected with `scripts/collect-agent-results.sh --summary-only`; `STATUS=OK` and `STATUS=cap_hit` settle a slot. Other statuses advance to the next phase, and a phase-3 failure leaves `DISPATCH_OK=false`.

Grouped dedup:

- The ledger schema is TSV: `group<TAB>slot_name<TAB>tool<TAB>output_path<TAB>status`, with optional sixth `source_slot` only for reused rows.
- `status` is a single token: `ok` for a fresh successful result, `reused` when a slot copied another slot's result.
- Phase-1 and phase-2 `STATUS=OK` results for grouped slots append `ok` rows.
- Phase-2 launches are serialized within each `fallback_group`. Before launching a grouped phase-2 slot, the dispatcher looks for an existing `ok` row for the same group and fallback tool. If found, it copies that output to the slot's phase-1 output path, records final bookkeeping, and skips the launch.
- Ungrouped phase-2 slots remain on the legacy parallel path.
- Reused slots write `${output}.dedup` with exactly:

```text
DEDUPE_REUSED_FROM=<source_slot>
DEDUPE_REUSED_TOOL=<source_tool>
```

They also emit `DEDUPE_REUSED=true`, `DEDUPE_REUSED_FROM`, and
`DEDUPE_REUSED_TOOL` KVs and are included in `ALL_OUTPUT_FILES` /
`ALL_OUTPUT_TOOLS` without entering phase 3.

Example: `decomp-cursor-arch` and `decomp-codex-arch` share
`fallback_group="decomp-arch"`. If the codex primary succeeds in phase 1 and
the cursor primary fails, the cursor slot's phase-2 codex fallback reuses
`decomp-codex-arch`; the cursor output sidecar contains
`DEDUPE_REUSED_FROM=decomp-codex-arch`.

Stdout keys:

- `PHASE1_SLOTS`, `PHASE2_SLOTS`, `PHASE3_SLOTS`
- `ALL_OUTPUT_FILES`
- `ALL_OUTPUT_FILES_PATH` — absolute/resolved path to the line-oriented paths-file (one output path per line, slot order); default file is `<slots-file>.output-files`, overridable with `--paths-file <path>`
- `ALL_OUTPUT_TOOLS`
- `FALLBACK_COUNT`
- `WARN=cost-fallback-exceeded-threshold` when phase-3 count exceeds `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` (default 3)
- `DISPATCH_OK=true|false`

Flags:

- `--paths-file <path>` — write the final paths list to this path instead of the default `<slots-file>.output-files`. The file is replaced atomically each run (temp file in the same directory + `mv`).
- `--require-result-pattern <regex>` — caller-supplied ERE (`grep -E`) that a `STATUS=OK` result file must match for the slot to settle on the assigned phase tool. Pre-validated once after argv parse against empty stdin; if the pattern is not a valid ERE (`grep` rc > 1) the dispatcher exits **2** with `larch_err` before any slot launches. Applied only to `STATUS=OK`; `STATUS=cap_hit` bypasses the gate so the launcher-side token-budget skip remains terminal. On a `STATUS=OK` pattern miss, the slot is routed through the existing `failed[]` path (phase-1 → phase-2 → phase-3 fallback) with no new exit codes or sidecar files. When the flag is unset (default), behavior is unchanged.

Non-adopters: the sketch phase has no waterfall caller (sketches tolerate narration-only outputs as "no contested position" in synthesis) and the plan-review collector flow (`plan-review-loop.sh` / `dispatch-plan-review-panel.sh`) performs its own structured checks via `collect-agent-results.sh --structured-reviewer-validation`. Current opt-in callers are `skills/design/scripts/decompose-aggregator.sh` and `skills/design/scripts/decompose-panel-dispatch.sh`, both passing `^[[:space:]]*## Recommendation`.

Guards:

- Empty slots manifest (zero JSON rows) exits **2** with `slots file contains no slot rows` and does not emit stdout KVs or write a paths-file.
- Any resolved final output path containing a literal newline or carriage return exits **2** before writing the paths-file (line-oriented contract).
- For grouped rows, `fallback_group`, `slot`, and `output` must not contain tab, newline, or carriage return. Violations print `STEP_FAILED=MANIFEST_VALIDATION` to stdout, emit a diagnostic on stderr, and exit non-zero before launches.

Regression harness: `scripts/test-dispatch-with-waterfall.sh`.
