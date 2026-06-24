### [Plan Review] FINDING_1

### FINDING_1: Dirty-tree resume still uses removed routing-table semantics instead of BOOTSTRAP_NEXT
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan replaces the Step 0 eight-row routing table with fail-closed `BOOTSTRAP_NEXT` directive lookup, but dirty-tree recovery prose is not updated on that path. The dirty-tree table row (~295) still says to parse resumed wrapper stdout and re-evaluate the routing table. Resume step 3 (~310) only requires rebinding `IMPLEMENT_BAIL_REASON`, `BRANCH_NAME`, `BRANCH_ACTION`, and `PLAN_FILE` from resumed stdout and never requires parsing `BOOTSTRAP_NEXT` before branching. After operator cleanup and a successful resume bootstrap, an orchestrator can treat a cleared `IMPLEMENT_BAIL_REASON` as permission to enter Step 2 or follow deleted table semantics (`ROUTE`, legacy bail fields) instead of the fail-closed `BOOTSTRAP_NEXT` contract the plan mandates at Step 0 entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skills/implement/SKILL.md` dirty-tree recovery step 3, after the resume bootstrap fence succeeds, require the same fail-closed BOOTSTRAP_NEXT parse used at Step 0 entry (allowed set or abort exit 2). State that legacy ROUTE/IMPLEMENT_BAIL_REASON fields must not drive routing on this path. Add a matching pin in scripts/test-implement-structure.sh or scripts/test-plan-adequacy-audit.sh for the resume continuation prose.
  - From Cursor-Pragmatic: In the Step 0 dirty-tree recovery section, replace re-evaluating the routing table with parsing `BOOTSTRAP_NEXT` from resumed wrapper stdout using the same allowed-set fail-closed contract as initial Step 0. Add a matching pin in `scripts/test-implement-structure.sh` (and `scripts/test-plan-adequacy-audit.sh` if needed) so `make lint` rejects the stale routing-table wording.
  - From Cursor-Requirements: In the Step 0 SKILL.md update, replace routing-table resume language with: after dirty-tree resume, parse BOOTSTRAP_NEXT from wrapper stdout (allowed set or exit 2); branch only on that directive. Add a lint pin forbidding re-evaluating the routing table in dirty-tree recovery prose.


### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:147
- **Concern**: [SCOPE-REDUCTION] Edge-case bullet mislabels empty coder as a _step2_blockers case. Scenario: Step 2 blockers in code are only REPO_UNAVAILABLE, PLAN_FILE, and missing tmpdir plan.txt / feature-description.txt (python/bootstrap.py:1112-1122). Empty coder is gated by _continue_predicate (python/bootstrap.py:1338-1345), which sets continue_tail_attempted=false without touching _step2_blockers. Listing empty coder under step2-blocker cases contradicts plan.txt:38 (reuse _step2_blockers; do not re-encode inline) and can push implementers to extend _step2_blockers for empty coder.
- **Proposed resolution**: Revise the edge-case bullet: empty coder routes to cleanup via continue_tail_attempted=false and the step2 branch guard (non-empty coder), not via _step2_blockers. Keep _step2_blockers limited to repo/plan artifact checks.


