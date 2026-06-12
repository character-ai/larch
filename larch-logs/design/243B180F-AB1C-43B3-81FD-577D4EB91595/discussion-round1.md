## Decision 1: Scope for `strip_lifecycle_prefix` duplication
- **Question**: Should the plan add a cross-file sync guard for the Bash/Python duplication?
- **Resolution**: No. User said "no enhancement of bash machinery we are replacing with python machinery." Skip OOS_1 first entirely.
- **Source**: user

## Decision 2: Already-done items
- **Question**: How to handle the items the research shows are already implemented?
- **Resolution**: Treat as out of scope (already done). The plan covers only the three confirmed gaps.
- **Source**: codebase (confirmed by reading Makefile, test harness, CI workflow)

## Decision 3: In-scope items
- **Question**: What are the three remaining gaps?
- **Resolution**:
  1. `relevant-checks.sh` — no case for `scripts/implement-preflight.sh` / `scripts/implement-preflight.md` / `scripts/test-implement-preflight.sh` → `test-implement-preflight`
  2. `SECURITY.md` line ~245 — stale claim that `--emergency` and `--merge` are mutually exclusive (SKILL.md says they're compatible)
  3. `scripts/test-implement-preflight.sh` — refusal-template first-line assertion (`**❌ /implement preflight: admission blocked — ...`) is present only on the `managed-prefix` branch; missing for `has-blockers`, `missing-designed-prefix`, `report-title`, and `error` branches
- **Source**: codebase
