### FINDING_1: ShellCheck SC2016 failures in planned jq literals
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Planned jq filter literals contain `$merge_*` inside single quotes without SC2016 waivers, so ShellCheck can fail `make lint` on the new harness and full-filter grep pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add # shellcheck disable=SC2016 # jq filter literal immediately before the planned jq -c command and before the new full-filter grep, matching the existing literal jq pins

### FINDING_2: Write-failure recovery harness tests unreachable Step 0b behavior
- **Reviewer(s)**: Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Concern**: The proposed case 5 exercises recovery after `write-run-params.sh` fails, but the real Step 0b contract treats that writer failure as an abort before the later recovery merge can run. The harness can pass while proving behavior `/design` will not execute.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic: Update the plan to test the actual Step 0b control flow and either change SKILL.md to capture the writer rc and run the recovery merge before the abort/continue decision, or remove the write-failure recovery acceptance claim.
  - From Cursor-Innovation, Codex-Innovation: For SIMPLE scope, drop case 5 and the write-failure recovery claims, or explicitly update SKILL.md so recovery is invoked around a failed writer before aborting

### FINDING_3: Parser plan overreaches and misstates sibling flag behavior
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Cursor-dyn-parser-sibling-consistency, Codex-dyn-parser-sibling-consistency
- **Severity**: important
- **Concern**: The planned parser edit expands beyond the stated `--manual-gate-b` gap to sibling flags, while also citing `--review-budget`/`--workflow-path` as the model even though those flags do not share the same empty-value behavior. This can land untested behavior changes and preserve inconsistent empty-string handling under an inaccurate contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Narrow the writer parser edit to --manual-gate-b only; keep sibling flags unchanged unless this PR also adds matching missing/empty tests for them
  - From Cursor-dyn-parser-sibling-consistency, Codex-dyn-parser-sibling-consistency: Revise the plan to name the actual current state: convert only the three ${2:?...} router boolean cases to an explicit larch_err/exit 2 block with flag-name error and shift 2; do not cite --review-budget/--workflow-path as the empty-value model unless those cases are also intentionally normalized.

### FINDING_4: Step 0b recovery guard false branch remains untested
- **Reviewer(s)**: Cursor-dyn-harness-guard-fidelity, Codex-dyn-harness-guard-fidelity
- **Severity**: important
- **Concern**: The harness claims to exercise the Step 0b outer guard, but every proposed case enters the true branch. An always-triggered or loosened recovery guard would still pass because there is no documented all-false argv no-op case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-guard-fidelity, Codex-dyn-harness-guard-fidelity: Add one minimal all-false no-op case, or explicitly narrow the plan's coverage claim and document the omitted false-branch as an accepted gap
