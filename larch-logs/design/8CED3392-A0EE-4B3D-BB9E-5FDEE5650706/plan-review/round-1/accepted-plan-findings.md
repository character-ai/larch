### FINDING_1: `--manual-gate-b` rejection tests expect the wrong exit path
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity
- **Severity**: important
- **Concern**: Planned `--manual-gate-b` empty/missing tests use helpers that require exit 2, but the current parser uses Bash `${2:?...}` expansion, which exits before the script’s explicit `larch_err`/`exit 2` path. The proposed tests can fail on return code even when stderr matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Revise the plan to update the --manual-gate-b parser to an explicit value check using ${2-}, larch_err, and exit 2 before assigning MANUAL_GATE_B, then keep the proposed tests
  - From Cursor-Edge, Codex-Edge: Change --manual-gate-b parsing to an explicit missing-or-empty value check that emits the existing error text through larch_err and exits 2 before assigning MANUAL_GATE_B
  - From Cursor-Innovation: New cases will fail at [[ "$rc" == 2 ]] Use the test-wait-for-reviewers.sh assert_reject pattern (expect exit 1 and grep stderr for --manual-gate-b requires a value) or add a minimal rc==1 helper; do not reuse assert_rejected_with without changing the writer
  - From Codex-Innovation: Revise the plan either to make write-run-params.sh validate --manual-gate-b with the existing explicit exit-2 pattern before adding these tests, or to assert only non-zero plus stderr for these two current-behavior cases
  - From Cursor-Pragmatic: Switch --manual-gate-b parsing to the explicit if [[ $# -lt 2 ]]; then larch_err ...; exit 2; fi pattern used for --reason, or drop assert_rejected_with for these two cases and assert non-zero exit with the same stderr substring
  - From Codex-Pragmatic: Either drop these extra failure-path cases from the SIMPLE plan, or add scripts/write-run-params.sh to the plan and handle --manual-gate-b with the same explicit $# check plus exit 2 pattern used by nearby optional value flags
  - From Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity: Update the boolean flag parser to use explicit value checks or `take_value` before adding the tests, at least for `--manual-gate-b` and preferably for the sibling boolean flags for consistency.


### FINDING_2: SKILL.md drift pin does not fully protect the jq merge expression
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity
- **Severity**: important
- **Concern**: The proposed SKILL.md drift pin checks only the partition assignment substring, so later changes to the brainstorm/manual merge assignments could pass the structural test while breaking the runtime semantics the harness claims to protect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge, Codex-Innovation: Pin the full jq expression or add targeted contains checks for .brainstorm_requested = (.brainstorm_requested == true or $merge_b) and .manual_gate_b = $merge_m
  - From Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity: Pin the full jq filter from skills/design/SKILL.md, or at minimum add separate pins for the brainstorm and manual assignments, and narrow the safety prose to what the pins actually prove.


### FINDING_3: Recovery harness misses the write-failure recovery path
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned Step 0b recovery harness covers successful `write-run-params.sh` output followed by merge, but not the requested path where the initial write fails and jq recovery still preserves or restores router flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add one harness case that seeds run-params.json, simulates a failed rewrite (or omits the writer call), runs the Step 0b merge with manual_requested=true, and asserts manual_gate_b persists true; or narrow the issue/feature acceptance text if success-path merge coverage is intentionally sufficient.
  - From Codex-Requirements: Add one minimal manual-only failure case: seed an existing run-params file, invoke write-run-params.sh with a forced validation failure, assert nonzero, then run the same recovery merge and assert manual_gate_b becomes true


### FINDING_4: Planned manual-clear recovery case is unreachable in runtime shape
- **Reviewer(s)**: Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity
- **Severity**: important
- **Concern**: The plan describes `merge_run_params()` as a verbatim runtime copy, but planned case 2 omits the runtime outer guard and calls the jq merge with all current flags false. Runtime recovery only enters when at least one router flag is true, so the case tests a path Step 0b would not execute.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sync-pin-fidelity, Codex-dyn-sync-pin-fidelity: Copy the outer guard into the harness or change case 2 to a reachable recovery condition, such as another current flag true with manual false, then update comments so the test claims only that manual is overwritten when recovery runs.


### FINDING_5: Degraded-mode structural pin is duplicated
- **Reviewer(s)**: Codex-Requirements
- **Severity**: nit
- **Concern**: The plan adds a degraded-mode contains check that already exists, increasing duplicate structural checks without covering a distinct requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Drop the planned duplicate contains line for the degraded-mode prose and keep the new stale-prose absent checks plus any genuinely new jq-merge pin


### FINDING_6: Stale-prose lint claims exceed the planned scan scope
- **Reviewer(s)**: Cursor-dyn-lint-scope-coverage, Codex-dyn-lint-scope-coverage
- **Severity**: important
- **Concern**: The planned stale-prose checks scan only `APPROVAL_MD` and `SKILL_MD`, but the plan text claims broader protection for Gate B prose in canonical docs such as `docs/configuration-and-permissions.md`, `docs/workflow-lifecycle.md`, or `SECURITY.md`. Those paths could regress without failing the proposed lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-lint-scope-coverage: Rewrite the failure mode: only approval-gates.md and SKILL.md are linted; stale phrases in other docs (including AGENTS.md canonical sources) regress silently unless manually caught; drop the over-match scenario for out-of-scope paths
  - From Codex-dyn-lint-scope-coverage: Narrow the plan claim to runtime Gate B surfaces and correct the failure-mode text; add SECURITY.md and docs/configuration-and-permissions.md to the absent scan only if canonical-doc Gate B prose must be CI-blocked.

