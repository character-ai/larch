# scripts/dispatch-with-waterfall.sh — contract

Three-phase per-slot fallback dispatcher for review-style fanout.

Input is an NDJSON slots file. Each row must contain:

- `slot`: stable slot label
- `tool`: primary external tool, `codex` or `cursor`
- `output`: phase-1 output path
- `agent` or `prompt_file`: source prompt for launchers

Rows may include optional metadata such as `weight` and `focus_area`; the dispatcher preserves validation compatibility and ignores those fields at launch time.

Phases:

1. Launch each slot on its assigned external tool when `--<tool>-present true`.
2. Failed or absent phase-1 slots launch on the other present external tool.
3. Remaining slots launch through `scripts/launch-claude-review.sh`.

Each phase is collected with `scripts/collect-agent-results.sh --summary-only`; `STATUS=OK` and `STATUS=cap_hit` settle a slot. Other statuses advance to the next phase, and a phase-3 failure leaves `DISPATCH_OK=false`.

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

Guards:

- Empty slots manifest (zero JSON rows) exits **2** with `slots file contains no slot rows` and does not emit stdout KVs or write a paths-file.
- Any resolved final output path containing a literal newline or carriage return exits **2** before writing the paths-file (line-oriented contract).

Regression harness: `scripts/test-dispatch-with-waterfall.sh`.
