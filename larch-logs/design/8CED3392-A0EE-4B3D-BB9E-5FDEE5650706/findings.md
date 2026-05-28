### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-step0b-router-flag-recovery.sh (planned); scripts/test-design-structure.sh:395-406,505-507
- **Concern**: Planned jq filter literals contain $merge_* inside single quotes without SC2016 waivers. Scenario: ShellCheck reports SC2016, so make lint fails on the new harness and likely on the new full-filter grep pin
- **Proposed resolution**: Add # shellcheck disable=SC2016 # jq filter literal immediately before the planned jq -c command and before the new full-filter grep, matching the existing literal jq pins

### FINDING_2:
- **Reviewer(s)**: Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:314-327
- **Concern**: Proposed write-failure harness bypasses real Step 0b abort. Scenario: Case 5 calls recovery after a failed write-run-params.sh invocation, but SKILL.md runs the writer as a strict-mode Bash fence and then instructs the orchestrator to abort on non-zero. Real /design will not reach the recovery merge on that failure path, so the new harness can pass while the #3008 degraded write-failure path remains broken.
- **Proposed resolution**: Update the plan to test the actual Step 0b control flow and either change SKILL.md to capture the writer rc and run the recovery merge before the abort/continue decision, or remove the write-failure recovery acceptance claim.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:314-327; scripts/test-step0b-router-flag-recovery.sh:case5
- **Concern**: Proposed case 5 tests a write-failure recovery path that the Step 0b contract aborts before running. Scenario: `write-run-params.sh` failure is handled as contract drift with exit 1, so the later jq recovery block is not a real post-failure path; the new harness can pass while proving behavior `/design` will not execute
- **Proposed resolution**: For SIMPLE scope, drop case 5 and the write-failure recovery claims, or explicitly update SKILL.md so recovery is invoked around a failed writer before aborting

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/write-run-params.sh:87-97
- **Concern**: Plan expands the parser change to --partition-requested and --brainstorm-requested although the stated gap and planned tests only cover --manual-gate-b. Scenario: The SIMPLE-scope fix can land extra untested behavior for sibling flags; a typo or rc mismatch in those new branches would not be covered by scripts/test-write-run-params.sh and is outside the --manual/-m acceptance path
- **Proposed resolution**: Narrow the writer parser edit to --manual-gate-b only; keep sibling flags unchanged unless this PR also adds matching missing/empty tests for them

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-parser-sibling-consistency, Codex-dyn-parser-sibling-consistency
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/write-run-params.sh:71-96
- **Concern**: The plan models the router-flag change on a missing-or-empty pattern that --review-budget and --workflow-path do not use; they only check [[ $# -lt 2 ]] and then call take_value, while --partition-requested, --brainstorm-requested, and --manual-gate-b are the only hyphenated optional flags currently using ${2:?...}.. Scenario: Applying the snippet as "same pattern used by" adjacent cases leaves mixed empty-string behavior: budget/path empty values are accepted as absent, but the three router booleans reject empty with larch_err/exit 2, and the plan text misstates the sibling contract it says it is preserving.
- **Proposed resolution**: Revise the plan to name the actual current state: convert only the three ${2:?...} router boolean cases to an explicit larch_err/exit 2 block with flag-name error and shift 2; do not cite --review-budget/--workflow-path as the empty-value model unless those cases are also intentionally normalized.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-harness-guard-fidelity, Codex-dyn-harness-guard-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-step0b-router-flag-recovery.sh:132-189 (proposed); skills/design/SKILL.md:331-353
- **Concern**: Harness claims to exercise the Step 0b outer guard, but all proposed cases enter the true branch and no all-false argv no-op case is documented. Scenario: An always-triggered or loosened recovery guard would still pass the proposed assertions because every call has partition, brainstorm, or manual set true; this leaves the guard-entry condition untested despite the plan claiming outer-guard coverage
- **Proposed resolution**: Add one minimal all-false no-op case, or explicitly narrow the plan's coverage claim and document the omitted false-branch as an accepted gap
