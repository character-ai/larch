## Goal
Convert 8 /research scripts to quiet-by-default via lib-quiet.sh

## Implementation Plan
## Implementation Plan: Quiet-by-default Phase 5 — /research scripts

### Goal
Convert 8 /research scripts to use lib-quiet.sh (FD-3 + emit/emit_kv), update test files, and update .md contract siblings. Identical conversion pattern to prior phases.

### Lib-quiet.sh path conventions
- Scripts in `skills/research/scripts/`: source via `"$SCRIPT_DIR/../../../scripts/lib-quiet.sh"`
  (validate-citations.sh: already has REPO_ROOT, use `"$REPO_ROOT/scripts/lib-quiet.sh"`)
- Scripts in `scripts/`: source via `"$SCRIPT_DIR/lib-quiet.sh"` or `"$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh"`

### 1. skills/research/scripts/compute-research-banner.sh (67 lines)
- Add `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"` after `set -euo pipefail`
- Source `"$SCRIPT_DIR/../../../scripts/lib-quiet.sh"` and call `larch_quiet_init`
- Change `printf '%s\n' "$banner"` in `emit_banner()` → `emit "$banner"`
- Tests: skills/research/scripts/test-research-banner.sh — add `export LARCH_QUIET_DISABLE=1`
- .md: skills/research/scripts/compute-research-banner.md — add FAILURE_LOG note

### 2. skills/research/scripts/render-findings-batch.sh (512 lines)
- Add SCRIPT_DIR, source lib-quiet.sh, larch_quiet_init after `set -euo pipefail`
- Change `echo "COUNT=$i"` (line 511) → `emit_kv COUNT "$i"`
- Tests: skills/research/scripts/test-render-findings-batch.sh — add LARCH_QUIET_DISABLE=1
- .md: skills/research/scripts/render-findings-batch.md — add FAILURE_LOG note

### 3. skills/research/scripts/run-research-planner.sh (177 lines)
- Add SCRIPT_DIR, source lib-quiet.sh, larch_quiet_init after `set -euo pipefail`
- Change all `echo "REASON=..."` → `emit_kv REASON "..."`
- Change `echo "COUNT=$COUNT"` → `emit_kv COUNT "$COUNT"`
- Change `echo "OUTPUT=$OUTPUT_PATH"` → `emit_kv OUTPUT "$OUTPUT_PATH"`
- Tests: skills/research/scripts/test-run-research-planner.sh — add LARCH_QUIET_DISABLE=1
- .md: skills/research/scripts/run-research-planner.md — add FAILURE_LOG note

### 4. skills/research/scripts/validate-citations.sh (965 lines)
- Script already has SCRIPT_DIR and REPO_ROOT — source `"$REPO_ROOT/scripts/lib-quiet.sh"`
- Call `larch_quiet_init` after `set -uo pipefail` and existing source lines
- Note: deliberately NOT using `-e` (fail-soft design) — lib-quiet still works
- Change `printf 'SUMMARY=PASS=%d FAIL=%d UNKNOWN=%d TOTAL=%d\n' ...` → use `emit` with formatted string
- Tests: skills/research/scripts/test-validate-citations.sh and test-validate-citations-budget.sh — add LARCH_QUIET_DISABLE=1
- .md: skills/research/scripts/validate-citations.md — add FAILURE_LOG note

### 5. scripts/eval-research.sh (721 lines)
- Already has CLAUDE_PLUGIN_ROOT — source `"$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh"` after set -euo pipefail and CLAUDE_PLUGIN_ROOT bootstrap
- Call `larch_quiet_init`
- The script emits operator-facing output (markdown table, breadcrumbs, final summary)
- Specific contract output to convert:
  - `printf 'eval-research: baseline written to %s\n' ...` → `emit "eval-research: baseline written to $WRITE_BASELINE_FILE"`
  - `printf '\neval-research: complete — %d entries run\n' "$ENTRIES_RUN"` → `emit "..."` with formatted string
  - Row printing in the summary loop: `printf '| ... |'` → `emit "| ... |"` (table rows are contract output)
  - Header/divider lines: `printf '\n%s\n%s\n'` → `emit "$SUMMARY_HEADER"` + `emit "$SUMMARY_DIVIDER"`
  - `printf '\neval-research: no entries matched ...\n'` — this goes to stderr (already >&2), leave as is
- Tests: scripts/test-eval-research-baseline-flag.sh — add LARCH_QUIET_DISABLE=1
- .md: scripts/eval-research.md — add FAILURE_LOG note

### 6. scripts/deny-edit-write.sh (141 lines)
- Add SCRIPT_DIR after shebang block, source lib-quiet.sh, larch_quiet_init
- Uses `set -uo pipefail` (no `-e`, intentional) — lib-quiet still works
- Refactor `block()`: capture JSON to variable and use `emit`:
  ```bash
  block() {
    local json
    json=$(jq -cn '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"/research is a read-only-repo skill -- Edit/Write/NotebookEdit outside /tmp is not permitted."}}' 2>/dev/null) \
      || json='{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"/research is a read-only-repo skill -- Edit/Write/NotebookEdit outside /tmp is not permitted."}}'
    emit "$json"
    exit 0
  }
  ```
- Refactor jq-absent static fallback: `emit '{"hookSpecificOutput":...}'` + exit 0
- Tests: scripts/test-deny-edit-write.sh — add LARCH_QUIET_DISABLE=1
- .md: scripts/deny-edit-write.md — add FAILURE_LOG note

### 7. scripts/audit-edit-write.sh (27 lines)
- Add SCRIPT_DIR, source lib-quiet.sh, larch_quiet_init
- Uses `set -uo pipefail` without `-e` (intentional — write failures must not interrupt)
- No contract stdout — all output goes to `$LOG` file (not stdout)
- The `printf '%s' "$INPUT" | jq ... >> "$LOG"` is a file write, not stdout — no emit changes needed
- Tests: scripts/test-audit-edit-write.sh — add LARCH_QUIET_DISABLE=1
- .md: scripts/audit-edit-write.md — add FAILURE_LOG note

### 8. scripts/validate-research-output.sh (425 lines)
- Add SCRIPT_DIR, source lib-quiet.sh, larch_quiet_init after set -euo pipefail
- Contract stdout: one-line diagnostic on failure (non-zero exit)
- Change diagnostic `echo "..."` lines to `emit "..."`:
  - `echo "file missing or not readable: $INPUT"` → `emit "file missing or not readable: $INPUT"`
  - `echo "structured records not found after repair"` → `emit "..."`
  - `echo "body too thin: ..."` → `emit "..."`
  - `echo "no provenance marker found"` → `emit "..."`
- Tests: scripts/test-validate-research-output.sh — add LARCH_QUIET_DISABLE=1
- .md: scripts/validate-research-output.md — add FAILURE_LOG note

### Test files (add `export LARCH_QUIET_DISABLE=1` after `set -euo pipefail`):
- skills/research/scripts/test-validate-citations.sh
- skills/research/scripts/test-validate-citations-budget.sh
- skills/research/scripts/test-render-findings-batch.sh
- skills/research/scripts/test-run-research-planner.sh
- skills/research/scripts/test-research-banner.sh
- skills/research/scripts/test-research-angle-prompts.sh (if it calls any of these scripts)
- skills/research/scripts/test-synthesis-subagent.sh (if applicable)
- scripts/test-eval-research-baseline-flag.sh
- scripts/test-research-structure.sh
- scripts/test-validate-research-output.sh
- scripts/test-audit-edit-write.sh
- scripts/test-deny-edit-write.sh

### .md contract siblings (add FAILURE_LOG note to each):
- skills/research/scripts/compute-research-banner.md
- skills/research/scripts/render-findings-batch.md
- skills/research/scripts/run-research-planner.md
- skills/research/scripts/validate-citations.md
- scripts/eval-research.md
- scripts/deny-edit-write.md
- scripts/audit-edit-write.md
- scripts/validate-research-output.md

### Edge cases
- validate-citations.sh EXIT trap writes degraded sidecar on non-zero: this is a file write (not stdout), safe with lib-quiet
- deny-edit-write.sh: hook contract uses FD 3 via emit — hook runner sees JSON on original stdout
- eval-research.sh: operator harness with complex output — all non-emit stdout goes to log (progress chatter, schema validation output, etc.)
- audit-edit-write.sh: all real output goes to LOG file (>>), not stdout; quiet init is safe


## Test plan
- `make test` (or relevant test targets) must pass
- Manual smoke check: source lib-quiet.sh in a test and confirm emit_kv output reaches caller
