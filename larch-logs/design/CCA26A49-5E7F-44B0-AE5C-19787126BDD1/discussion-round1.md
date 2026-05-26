## Decision 1: Issue #2899 disposition
- **Question**: Are the three OOS items (A: implement-finalize.sh:780-781 'amend' wording, B: drop-bump-commit.md:40-48 single-amended-commit implication, C: apply-bump.md:40-41 'bump must remain at HEAD' implication) still valid?
- **Resolution**: All three are already-resolved by commit fdfacb21 (#2852, landed 2026-05-26). `grep -i amend` returns zero matches in all three cited files. The fdfacb21 diff explicitly rewrote apply-bump.md:40-41 to clarify CHANGELOG is a separate commit and drop-bump walks back from HEAD. Source OOS issues #2858/#2859/#2860 were closed today as COMPLETED.
- **Source**: codebase (grep + git show fdfacb21)

## Decision 2: Verification scope
- **Question**: Should the verification step grep only the three cited files, or also adjacent docs in the bump+drop-bump+CHANGELOG edit-in-sync graph?
- **Resolution**: Grep adjacent docs. If residual stale wording is found, include edits in the plan.
- **Source**: user (Round 1 question 1, option 3 "Adjacent grep + fix in plan")

## Decision 3: Residual stale-wording findings
- **Question**: What stale 'amend'-into-bump-commit wording remains in adjacent docs after #2852?
- **Resolution**: Two sites with stale wording, one dead-code site:
  1. `scripts/git-commit.md:3` — Phrasing "Step 8a `CHANGELOG` commit on the path that doesn't amend" implies an amend path still exists. After #2852, all Step 8a CHANGELOG commits go through `commit-changelog.sh`; no amend path. Fix: drop the qualifier, leaving "Step 8a `CHANGELOG` commit".
  2. `scripts/test-implement-finalize.md:3` — Phrase "CHANGELOG detection/amend" describes harness stubs. The `git-amend-add.sh` stub at test-implement-finalize.sh:275-281 is retained but no test path exercises `STUB_AMEND_FAIL=true` (confirmed via grep — never set anywhere). Reword to "CHANGELOG detection" to reflect that no production-path amend remains.
  3. `scripts/test-implement-finalize.sh:275-281` — `git-amend-add.sh` stub gated on `STUB_AMEND_FAIL=true`. No call sets STUB_AMEND_FAIL=true. Dead code. Not in this plan's scope (the parent `git-amend-add.sh` script is intentionally retained per its .md). Surface as OOS observation for a future cleanup pass.
- **Source**: codebase (grep across scripts/ skills/ for "amend")

## Decision 4: Close-comment style
- **Question**: Short link+cite vs per-item evidence block?
- **Resolution**: Short link + cite.
- **Source**: user (Round 1 question 2, option 1 "Short link + cite")

## Decision 5: Out of scope
- **Question**: What is explicitly NOT being done in this plan?
- **Resolution**:
  - NO edits to `implement-finalize.sh`, `drop-bump-commit.md`, or `apply-bump.md` (already updated by #2852).
  - NO removal of `git-amend-add.sh` script or its `.md` sibling (intentionally retained per `git-amend-add.md:3`).
  - NO removal of the dormant `STUB_AMEND_FAIL` test stub (surfaced as OOS observation only).
  - NO edits to historical CHANGELOG.md entries (immutable past-tense).
  - NO edits to `larch-log-flush.md` reference to `git-amend-add.sh` (still valid since the script exists).
- **Source**: user constraint (issue is fundamentally a close-as-stale; minimal residual cleanup only)
