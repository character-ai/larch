## Goal
Harden RUN_ID path-traversal guard and document token-cost/token-tally divergence

## Implementation Plan

### Goal
Two hardening items from OOS review of #2468:
1. Add `RUN_ID` path-traversal guard in `skills/implement/scripts/write-final-report.sh` before `run_dir` construction.
2. Expand cross-reference docs in `scripts/token-cost.md` and `scripts/token-tally.md` to document the intentional divergence between the two helpers.

### Files to modify
- `skills/implement/scripts/write-final-report.sh` — add `case` guard before line 104
- `scripts/token-cost.md` — expand existing Note section with rate/rounding/N/A details
- `scripts/token-tally.md` — add a symmetric cross-reference note

### Approach

**Item 1 — write-final-report.sh RUN_ID guard**

After line 75 (where `RUN_ID` is fully resolved), add a `case`-based rejection before `run_dir` is constructed at line 104:

```bash
case "$RUN_ID" in
    */*|*'..'*) emit_kv_out STATUS failed
                emit_kv_out ERROR "invalid RUN_ID (path-traversal characters rejected)"
                exit 1 ;;
esac
```

Pattern mirrors `refresh-run-logs.sh` lines 38-41 exactly. Uses `emit_kv_out` consistent with the surrounding error-handling style (lines 106-109). This is ~5 LOC.

**Item 2 — token-cost.md / token-tally.md cross-references**

`token-cost.md` already has a brief "Note on `/research`" section. Expand it with explicit rate/rounding/N/A semantics:
- `token-cost.sh`: implement+fix-issue only; three separate vendor rates (`LARCH_CLAUDE_RATE_PER_M`, `LARCH_CODEX_RATE_PER_M`, `LARCH_CURSOR_RATE_PER_M`); each vendor is `N/A` independently when its rate is unset.
- `token-tally.sh`: research only; single `LARCH_TOKEN_RATE_PER_M` rate; `$` column omitted entirely (not `N/A` per vendor) when unset.

`token-tally.md` has no cross-reference. Add a parallel "Note on `/implement` and `/fix-issue`" section pointing back to `token-cost.sh`.

### Testing strategy
- Run `/relevant-checks` (pre-commit + agent-lint) to confirm no regressions.
- Verify the guard compiles correctly via `bash -n skills/implement/scripts/write-final-report.sh`.

## Test plan
(no test plan section in plan-file)
