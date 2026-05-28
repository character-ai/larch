### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-run-params.sh:95-97; scripts/test-write-run-params.sh:21-34
- **Concern**: Plan adds --manual-gate-b empty/missing tests that require exit 2, but the current parser uses Bash ${2:?...} expansion which exits the shell before the script's exit-2 error path. Scenario: The proposed assert_rejected_with cases will fail on rc mismatch before they can lock the intended failure-path contract
- **Proposed resolution**: Revise the plan to update the --manual-gate-b parser to an explicit value check using ${2-}, larch_err, and exit 2 before assigning MANUAL_GATE_B, then keep the proposed tests

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-run-params.sh:95-97
- **Concern**: Plan adds assert_rejected_with tests that require exit 2, but --manual-gate-b still uses Bash ${2:?...}, which exits 1 for missing or empty values. Scenario: The proposed manual-gate-b-empty and manual-gate-b-missing cases fail immediately instead of locking the intended rejection contract
- **Proposed resolution**: Change --manual-gate-b parsing to an explicit missing-or-empty value check that emits the existing error text through larch_err and exits 2 before assigning MANUAL_GATE_B

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:124-129
- **Concern**: The proposed SKILL.md drift pin only checks the partition substring, not the manual_gate_b overwrite semantic the new harness is meant to protect. Scenario: SKILL.md can later change .manual_gate_b = $merge_m to a preserving or OR-merge expression while the new harness still passes against its local copy
- **Proposed resolution**: Pin the full jq expression or add targeted contains checks for .brainstorm_requested = (.brainstorm_requested == true or $merge_b) and .manual_gate_b = $merge_m

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-write-run-params.sh:51-60
- **Concern**: Proposed manual-gate-b empty/missing cases use assert_rejected_with which requires exit 2. Scenario: write-run-params.sh uses ${2:?--manual-gate-b requires a value} at line 96; verified invocations with --manual-gate-b "" or trailing --manual-gate-b exit 1 with stderr containing the message, not 2
- **Proposed resolution**: New cases will fail at [[ "$rc" == 2 ]] Use the test-wait-for-reviewers.sh assert_reject pattern (expect exit 1 and grep stderr for --manual-gate-b requires a value) or add a minimal rc==1 helper; do not reuse assert_rejected_with without changing the writer

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-write-run-params.sh:21-34; scripts/write-run-params.sh:95-97
- **Concern**: Planned --manual-gate-b empty/missing tests reuse assert_rejected_with, but the current ${2:?...} expansion exits with status 1, not 2. Scenario: The new tests fail immediately even though the stderr substring is present
- **Proposed resolution**: Revise the plan either to make write-run-params.sh validate --manual-gate-b with the existing explicit exit-2 pattern before adding these tests, or to assert only non-zero plus stderr for these two current-behavior cases

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-write-run-params.sh:52-60
- **Concern**: Proposed assert_rejected_with cases require exit 2 but write-run-params.sh exits 1 on empty/missing --manual-gate-b. Scenario: ${2:?--manual-gate-b requires a value} aborts with bash exit 1; assert_rejected_with hard-fails unless rc==2, so new manual-gate-b-empty and manual-gate-b-missing cases fail CI even when stderr matches
- **Proposed resolution**: Switch --manual-gate-b parsing to the explicit if [[ $# -lt 2 ]]; then larch_err ...; exit 2; fi pattern used for --reason, or drop assert_rejected_with for these two cases and assert non-zero exit with the same stderr substring

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-run-params.sh:95-97
- **Concern**: Plan adds --manual-gate-b empty and missing tests that expect exit 2, but the parser still uses Bash ${2:?...} expansion for that flag. Scenario: Missing or empty --manual-gate-b exits via Bash parameter-expansion failure instead of the harness helper's expected rc 2, so the proposed scripts/test-write-run-params.sh cases fail unless the parser changes too
- **Proposed resolution**: Either drop these extra failure-path cases from the SIMPLE plan, or add scripts/write-run-params.sh to the plan and handle --manual-gate-b with the same explicit $# check plus exit 2 pattern used by nearby optional value flags

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-step0b-router-flag-recovery.sh:110-116
- **Concern**: Recovery harness only exercises post-success merge, not write-run-params failure plus jq recovery. Scenario: Issue #3008 item (3) and the filed OOS text require coverage when initial write-run-params fails but Step 0b still jq-merges router flags (e.g. --manual with a pre-existing run-params.json). The new harness always calls write-run-params successfully before merge_run_params, so a regression that skips merge on write failure would not be caught.
- **Proposed resolution**: Add one harness case that seeds run-params.json, simulates a failed rewrite (or omits the writer call), runs the Step 0b merge with manual_requested=true, and asserts manual_gate_b persists true; or narrow the issue/feature acceptance text if success-path merge coverage is intentionally sufficient.

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-step0b-router-flag-recovery.sh:1-69 (proposed)
- **Concern**: The planned recovery harness does not exercise a write-run-params failure before jq recovery. Scenario: The feature asks for coverage of write-run-params.sh failure with --manual-only argv followed by the four-arm jq-merge recovery, but the planned cases all create valid files with successful writer calls and then run a local merge function, so a regression where the failure path skips recovery can still pass
- **Proposed resolution**: Add one minimal manual-only failure case: seed an existing run-params file, invoke write-run-params.sh with a forced validation failure, assert nonzero, then run the same recovery merge and assert manual_gate_b becomes true

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-design-structure.sh:556-557
- **Concern**: The plan adds a degraded-mode contains pin that already exists. Scenario: Adding the same defaulting-to-auto-apply pin again increases duplicate structural checks without covering a distinct requirement, which conflicts with the SIMPLE minimum-change lane
- **Proposed resolution**: Drop the planned duplicate contains line for the degraded-mode prose and keep the new stale-prose absent checks plus any genuinely new jq-merge pin

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:34-39; <TMPDIR>/plan.txt:214-234; scripts/test-design-structure.sh:21-30; skills/design/SKILL.md:332-340
- **Concern**: The proposed SKILL.md pin only checks the partition assignment substring while the plan claims it locks the Step 0b merge expression.. Scenario: A SKILL.md edit can keep `.partition_requested = (.partition_requested == true or $merge_p)` but change or drop the brainstorm/manual merge structure; grep -F still passes and the harness can keep testing its stale local copy.
- **Proposed resolution**: Pin the full jq filter from skills/design/SKILL.md, or at minimum add separate pins for the brainstorm and manual assignments, and narrow the safety prose to what the pins actually prove.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:92-105; <TMPDIR>/plan.txt:118-125; skills/design/SKILL.md:332-340
- **Concern**: `merge_run_params()` is described as a verbatim runtime copy, but the planned case 2 omits the runtime outer guard and invokes the jq merge with all current flags false.. Scenario: Runtime Step 0b recovery only enters when partition, brainstorm, or manual is true; the planned manual-clear case passes in the harness while testing a path the runtime recovery does not execute.
- **Proposed resolution**: Copy the outer guard into the harness or change case 2 to a reachable recovery condition, such as another current flag true with manual false, then update comments so the test claims only that manual is overwritten when recovery runs.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:47-65; scripts/test-write-run-params.sh:21-34; scripts/write-run-params.sh:87-97
- **Concern**: The planned `assert_rejected_with` cases assume `--manual-gate-b` empty or missing exits 2, but the current parser uses raw `${2:?...}` for that flag.. Scenario: The helper at scripts/test-write-run-params.sh:21-34 requires rc 2; Bash parameter-expansion errors from scripts/write-run-params.sh:95-97 bypass the script's explicit `exit 2` path, so the new tests can fail without any runtime behavior change.
- **Proposed resolution**: Update the boolean flag parser to use explicit value checks or `take_value` before adding the tests, at least for `--manual-gate-b` and preferably for the sibling boolean flags for consistency.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-lint-scope-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:223-227
- **Concern**: Failure-mode text says stale-prose lint fails when docs/configuration-and-permissions.md or docs/workflow-lifecycle.md quote banned phrases, but the proposed absent checks only read $APPROVAL_MD and $SKILL_MD. Scenario: Operators or reviewers treat the failure mode as proof CI guards canonical docs; a PR that reintroduces stale Gate B phrases only in docs/configuration-and-permissions.md (or SECURITY.md) would pass test-design-structure.sh
- **Proposed resolution**: Rewrite the failure mode: only approval-gates.md and SKILL.md are linted; stale phrases in other docs (including AGENTS.md canonical sources) regress silently unless manually caught; drop the over-match scenario for out-of-scope paths

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-lint-scope-coverage
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:17-24,223-227; scripts/test-design-structure.sh:5-8; AGENTS.md:19,30,47; docs/configuration-and-permissions.md:233-239
- **Concern**: The proposed stale-prose lint scans only APPROVAL_MD and SKILL_MD while the plan claims stale Gate B prose regression is closed and treats docs/configuration-and-permissions.md as intentionally excluded.. Scenario: A future edit can add one of the banned stale phrases to SECURITY.md or docs/configuration-and-permissions.md and make lint still passes because no planned absent check reads those files.
- **Proposed resolution**: Narrow the plan claim to runtime Gate B surfaces and correct the failure-mode text; add SECURITY.md and docs/configuration-and-permissions.md to the absent scan only if canonical-doc Gate B prose must be CI-blocked.
