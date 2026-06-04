### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:40
- **Concern**: skills/implement/SKILL.md:40 vs plan oos-pipeline step 3. Scenario: NEVER #5 is preserved byte-stable and still requires the idempotent branch to run larch-log write for run-statistics, while the new reference step 3 says sentinel recovery must not write run-statistics and defers stats to post-checkpoint SKILL.md / step 7
- **Proposed resolution**: An orchestrator that loads oos-pipeline.md then follows NEVER #5 can write run-statistics before oos-disposition-checkpoint.sh, conflicting with NEVER #14, the Step 8+ OOS checkpoint block (~1042), and the plan’s pre-checkpoint-stats failure mode In the SKILL.md update, narrow NEVER #5 How-to-apply to oos-issues append (and terminal-summary refresh if needed) on sentinel recovery, or add an explicit precedence line in oos-pipeline.md Contract that post-checkpoint SKILL.md owns run-statistics and overrides NEVER #5 for that batch

### FINDING_2:
- **Reviewer(s)**: Codex-Arch, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:40
- **Concern**: Plan preserves NEVER #5 even though it still says the Step 9a.1 sentinel branch writes run-statistics. Scenario: The new oos-pipeline.md defers run-statistics until after oos-disposition-checkpoint.sh passes, but this preserved NEVER text would still instruct the opposite on sentinel recovery
- **Proposed resolution**: Revise the plan to minimally edit NEVER #5 so sentinel recovery writes only recovered oos-issues evidence and terminal summary content; keep run-statistics owned by the post-checkpoint Step 8+ block

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:40,1042
- **Concern**: Plan preserves a conflicting NEVER #5 run-statistics instruction. Scenario: NEVER #5 still tells the Step 9a.1 sentinel branch to write run-statistics, while the checkpoint block owns run-statistics only after oos-disposition-checkpoint.sh passes
- **Proposed resolution**: Update NEVER #5 minimally to remove the run-statistics write from sentinel recovery and state that only the oos-issues batch is written there; keep run-statistics in the post-checkpoint block

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:955
- **Concern**: Python oos-filing dispatch is not covered by the mandatory oos-pipeline.md load. Scenario: LARCH_SHIP_PR_IMPL=python returns needs_user_reason=oos-filing with OOS_PENDING still false, so the orchestrator can run the existing Step 9a.1 pipeline from this clause without loading the restored canonical procedure
- **Proposed resolution**: Add the same mandatory read directive to the oos-filing dispatch clause, or explicitly route that clause through the OOS checkpoint/pipeline block before invoking /issue

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:40; plan.txt:29-30,78-84
- **Concern**: NEVER #5 still pairs idempotent recovery with `run-statistics` writes while the new procedure forbids them in Step 9a.1. Scenario: An agent reconciling both surfaces may write `run-statistics` before `oos-disposition-checkpoint.sh`, reviving pre-checkpoint stats drift the plan’s failure modes call out
- **Proposed resolution**: In `oos-pipeline.md` step 3/7 (or **Contract**), state explicitly that idempotent recovery writes only the `oos-issues` batch here and that NEVER #5’s `run-statistics` half is satisfied solely by the existing post-checkpoint Step 8+ block after checkpoint exit 0

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/references/oos-pipeline.md (proposed Step 1); skills/implement/scripts/oos-disposition-gate.md:30-31
- **Concern**: Proposed security filter does not match the checkpoint counter. Scenario: The plan tells Step 9a.1 to exclude unfenced focus-area=security blocks, but the checkpoint only excludes dedicated - **focus-area**: security fields. A filtered block left in accepted markdown is still counted as non-security, so OOS_PENDING can fail after private routing.
- **Proposed resolution**: Align the new reference with the current gate rule, or add the minimal gate/awk/checkpoint or accepted-artifact cleanup step so security-routed blocks are not counted after Step 9a.1.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:40 / plan.txt:29-30,78-84
- **Concern**: Plan preserves NEVER #5 byte-stable while oos-pipeline step 3 forbids sentinel-recovery run-statistics writes. Scenario: Mandatory oos-pipeline.md load conflicts with NEVER #5 How-to-apply; an agent may write run-statistics before oos-disposition-checkpoint.sh
- **Proposed resolution**: Add explicit precedence in oos-pipeline.md step 3 or Contract: sentinel branch writes oos-issues only; run-statistics stays post-checkpoint per NEVER #14 and the Step 8+ block—or allow a minimal NEVER #5 How-to-apply edit removing the run-statistics clause

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:40
- **Concern**: The plan says to preserve NEVER #5 byte-stable, but that paragraph still says sentinel recovery writes run-statistics while the new oos-pipeline contract says run-statistics is post-checkpoint-owned.. Scenario: After the PR, SKILL.md and oos-pipeline.md would give conflicting ownership for run-statistics, weakening the ordering invariant the plan intends to pin.
- **Proposed resolution**: Make the minimal SKILL.md exception: update NEVER #5 to require only the recovered oos-issues log write on sentinel recovery, and state run-statistics remains owned by the post-checkpoint block.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-contract-cartographer
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:40-40 vs skills/implement/references/oos-pipeline.md (planned step 3)
- **Concern**: NEVER #5 still requires sentinel recovery to run `run-statistics` inside Step 9a.1, but the planned procedure forbids it there. Scenario: The plan says preserve NEVER #5 byte-stable while step 3 says "Do not write `run-statistics` here" and step 7 defers stats to post-checkpoint SKILL.md; implementers get contradictory orders on idempotent reruns
- **Proposed resolution**: Reconcile explicitly: either narrow NEVER #5 to `oos-issues` append only on sentinel recovery (stats only after `oos-disposition-checkpoint.sh` exit 0 per skills/implement/SKILL.md:1042-1042) or add a one-line exception in oos-pipeline step 3 that cites NEVER #5 — do not leave both texts unchanged

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-contract-cartographer
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:40,1042
- **Concern**: F1 Plan makes oos-pipeline.md post-checkpoint-owned for run-statistics but also says to preserve NEVER #5, whose text still requires the Step 9a.1 sentinel branch to run larch-log.sh write --batch run-statistics.. Scenario: The new reference and SKILL.md would be competing sources of truth; an implementer following NEVER #5 can durable-write run-statistics before oos-disposition-checkpoint.sh passes, contradicting the proposed Step 7 and the current OOS checkpoint block.
- **Proposed resolution**: Do not keep NEVER #5 byte-stable here; revise only its run-statistics clause so sentinel recovery writes the oos-issues batch/summary evidence and explicitly leaves run-statistics to the post-checkpoint block.

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-contract-cartographer
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/scripts/oos-disposition-gate.md:29-31; skills/implement/scripts/oos-non-security-block-count.awk:1-15; skills/implement/scripts/test-oos-disposition-gate.sh:165-199,241-257
- **Concern**: F2 Step 1 names a focus-area=security fenced/unfenced exclusion but does not anchor it to the checkpoint reader's actual predicate.. Scenario: Current gate excludes only a dedicated - **focus-area**: security field line and the harness pins prose focus-area=security in Description as non-security; if oos-pipeline filters by the shared voting token instead, it can skip filing a block that the checkpoint still counts or document a second security predicate.
- **Proposed resolution**: In oos-pipeline.md Step 1 cite oos-disposition-gate.md Counting rules or oos-non-security-block-count.awk and state the exact dedicated field-line predicate; do not use the broader shared voting token unless gate/tests are also changed.
