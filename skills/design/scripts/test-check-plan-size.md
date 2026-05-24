# skills/design/scripts/test-check-plan-size.sh

Offline regression harness for [`check-plan-size.sh`](check-plan-size.sh). Captures the `emit_kv` contract stream with `LARCH_QUIET_DISABLE=1` (same pattern as [`test-emit-plan.sh`](test-emit-plan.sh)).

## Cases exercised

1. No triggers — medium plan, few headings, moderate `diff_lines`.
2. Plan-body soft — 251 body lines (strict `>` past 250).
3. Diff-lines soft — `diff_lines` past 600.
4. Files-count soft — nine `### NEW/UPDATED/REWRITTEN` headings.
5. Multiple soft reasons — combined crossings; `TRIGGER_REASONS` uses fixed priority `plan-body-lines,diff-lines,files-count`.
6. Plan-body hard — 801 body lines.
7. Diff-lines hard — `diff_lines` past 1500.
8. Hard + multiple soft crossings — hard precedence (`SOFT_TRIGGER_FIRED=false`) with full `TRIGGER_REASONS` list.
9. Missing plan file — exit 2, `PLAN_SIZE_STATUS=missing-plan`.
10. Malformed trailer — exit 2, `PLAN_SIZE_STATUS=missing-diff-lines`.
11. Boundary equalities — 250 / 600 / 8 / 800 / 1500 do not trip (five sub-cases).
12. Zero headings — `FILES_COUNT=0`, no `set -e` abort from `grep -c`.
13. Multiple `diff_lines:` lines — rejects when final non-empty line is not the trailer; accepts when trailer is last non-empty line.
14. Whitespace-tolerant headings — `###  NEW:` and `### UPDATED :` count.
15. Hard at 801 lines — same as helper-level hard detection (orchestrator `--partition` + hard interaction is pinned in `scripts/test-design-structure.sh`).

## Run

```bash
bash skills/design/scripts/test-check-plan-size.sh
# or
make test-check-plan-size
```
