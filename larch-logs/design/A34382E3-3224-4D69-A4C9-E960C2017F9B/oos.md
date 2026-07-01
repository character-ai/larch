### FINDING_4: Step 8+ omits execution-issues refresh trigger preserve
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The Step 8+ preserve inventory omits the execution-issues refresh trigger sentence (and its pairing with the refresh fence). The plan authorizes tightening the post-driver skeleton and branch blockquotes but does not freeze `When ship-pr-exit-matrix.md requires tracking metadata projection refresh, run this fence; skip it when ISSUE_NUMBER is empty or 0.` or explicitly pair it with the `python/cli.py execution-issues refresh` Bash fence. That predicate is not pinned by `scripts/test-implement-structure.sh` (only a retired `**Execution-issues checkpoint**` forbid exists). A density pass can delete the trigger while keeping the fence and still pass listed harnesses, violating zero-behavior-change acceptance and either skipping metadata projection refresh on branches that need it or running refresh without the ISSUE_NUMBER guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the trigger sentence and fence to Item 3 byte-stable preserve list, Edge cases, Failure modes, and Acceptance checks (or an explicit do-not-delete note in the post-driver skeleton section).
  - From Cursor-Requirements: Add the trigger sentence (and `python/cli.py execution-issues refresh --implement-tmpdir "$IMPLEMENT_TMPDIR" --best-effort` pairing) to the Step 8+ byte-stable preserve inventory and Edge cases, alongside the existing fence-shape rule.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Testing strategy omits `make test-render-cost-line-callsites` despite pre-edit inventory listing that harness
- **Description**: Testing strategy omits `make test-render-cost-line-callsites` despite pre-edit inventory listing that harness. Scenario: Approach tells implementers to inventory pins from `scripts/test-render-cost-line-callsites.sh`, but the Testing strategy and acceptance bullets never run it. Edits confined to the three named zones are unlikely to break Step 16-18 grep pins, and `/implement` relevant-checks pairs the harness with `skills/implement/SKILL.md`, so CI still catches regressions; local sign-off can nonetheless claim completeness after only the listed make targets.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

