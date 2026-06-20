## Proposed Design Outline

### Goals
- Resolve all 14 items in #4757: concrete fixes, docs corrections, test-coverage gaps, and audit closures.
- Land real code/docs/test changes where defects exist; record explicit no-defect closures otherwise.
- Keep every change surgical and independently traceable to one item.

### Non-goals
- No re-splitting of this deliberately-combined OOS issue.
- No refactors, polish, or scope beyond the 14 items.
- No regression pins for no-defect audits unless a genuine correctness risk is found.

### Approach sketch
- Item 1: add tally-scalar fallback for empty self-review JSONL in `fluff-analysis.py` and `audit_runs.py`.
- Items 2, 3, 9: docs corrections (run-logs intro, linting shard label, thin-wrapper vs migration-recipe reconcile).
- Items 4, 5, 7: assess pytest coverage; add failure-path tests where genuinely missing.
- Items 8, 10-14: investigate during design; pin a regression test only where risk is real, else document closure.

### Surfaces in scope
- `skills/fluff-analysis/scripts/fluff-analysis.py`, `python/audit_runs.py`
- `docs/run-logs.md`, `docs/linting.md`, `docs/python-migration.md`, `AGENTS.md` / `.claude/rules/python-first-scripts.md`
- `python/design_lifecycle.py`, `python/duplicate_code.py`, `python/test_duplicate_code*.py`
- stall-recovery pytest, clarify publish-path tests, `Makefile`, `.github/workflows/ci.yaml`

### Open questions
- None. Per-item pin-vs-close calls are resolved during drafting per the Round 1 policy.
