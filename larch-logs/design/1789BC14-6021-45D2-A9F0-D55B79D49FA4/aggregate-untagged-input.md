### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:306-319
- **Concern**: Dirty-tree resume omits BOOTSTRAP_NEXT handoff on resumed bootstrap stdout. Scenario: Step 0 replaces the routing table with fail-closed BOOTSTRAP_NEXT lookup, but the dirty-tree gate step 3 only tells the orchestrator to rebind IMPLEMENT_BAIL_REASON, BRANCH_NAME, BRANCH_ACTION, and PLAN_FILE from resumed stdout. It never requires parsing BOOTSTRAP_NEXT on that same exit-0 envelope before routing. An implementer can treat a cleared IMPLEMENT_BAIL_REASON as implicit permission to enter Step 2 and skip the directive lookup the issue requires.
- **Proposed resolution**: In `skills/implement/SKILL.md` dirty-tree recovery step 3, after the resume bootstrap fence succeeds, require the same fail-closed BOOTSTRAP_NEXT parse used at Step 0 entry (allowed set or abort exit 2). State that legacy ROUTE/IMPLEMENT_BAIL_REASON fields must not drive routing on this path. Add a matching pin in scripts/test-implement-structure.sh or scripts/test-plan-adequacy-audit.sh for the resume continuation prose.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:310
- **Concern**: Dirty-tree resume continuation still references the removed Step 0 routing table. Scenario: The plan replaces the Step 0 routing table with `BOOTSTRAP_NEXT` lookup and only says to enter dirty-tree recovery from `BOOTSTRAP_NEXT=dirty-recovery`. It does not require rewriting dirty-tree step 3, which still tells the orchestrator to parse resume stdout and re-evaluate the routing table. After operator cleanup, the orchestrator can follow deleted table semantics instead of fail-closed `BOOTSTRAP_NEXT` parsing.
- **Proposed resolution**: In the Step 0 dirty-tree recovery section, replace re-evaluating the routing table with parsing `BOOTSTRAP_NEXT` from resumed wrapper stdout using the same allowed-set fail-closed contract as initial Step 0. Add a matching pin in `scripts/test-implement-structure.sh` (and `scripts/test-plan-adequacy-audit.sh` if needed) so `make lint` rejects the stale routing-table wording.

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:295-310
- **Concern**: Dirty-tree resume prose still tells the orchestrator to re-evaluate the removed Step 0 routing table. Scenario: The plan replaces the 8-row table with BOOTSTRAP_NEXT lookup (plan.txt:113-120) but only says to keep the dirty-tree section and enter via BOOTSTRAP_NEXT=dirty-recovery (plan.txt:118). It does not require updating the dirty-tree row (~295) or resume step 3 (~310), which still say parse resume stdout before re-evaluating the routing table. After cleanup, the orchestrator can follow deleted table semantics instead of fail-closed BOOTSTRAP_NEXT parsing.
- **Proposed resolution**: In the Step 0 SKILL.md update, replace routing-table resume language with: after dirty-tree resume, parse BOOTSTRAP_NEXT from wrapper stdout (allowed set or exit 2); branch only on that directive. Add a lint pin forbidding re-evaluating the routing table in dirty-tree recovery prose.
