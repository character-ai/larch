### FINDING_10: panel [code-review/accepted]

## code-quality: scripts/lint-bash32.md:3

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract says tracked-only shell files but git enumeration includes untracked non-ignored scripts. A contributor expects only staged paths to matter and is surprised when an untracked local .sh fails lint. Align wording with git ls-files --cached --others --exclude-standard semantics.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: scripts/collect-agent-results.sh:1140-1146

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Section 3.7 NS retry requires SUBSTANTIVE_VALIDATION=true but structured validation can run alone. Caller passes only --structured-reviewer-validation; 3.6 emits NOT_SUBSTANTIVE with NS_RETRY_MODE=structured but 3.7 never runs; no retry despite metadata implying one. Extend 3.7 guard, require paired flags, or drop NS_RETRY_MODE when substantive validation is off.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: scripts/lint-bash32.sh:81

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Case-conversion awk only matches ^^ and ,, not single ^ or ,. ${var^} or ${var,} slips past lint-bash32 while still requiring Bash 4+. Extend regex, BASH_AUTHORING.md, and test-lint-bash32.sh for single-caret/comma forms.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## correctness: scripts/lint-bash32.sh:85

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Named-coproc-only regex misses anonymous coproc forms. A Bash-4-only anonymous coproc slips past lint and breaks on macOS Bash 3.2 at runtime. Extend detection or explicitly document the unsupported coproc subset.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: scripts/test-collect-agent-results.sh (C_IT1 OUT_IT1 heredoc per diff hunk @@ -238,27 +260,71 @@)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] C_IT1 fixture body replaced with meta prose and an example TSV block unrelated to collector behavior Fixture no longer encodes a deliberate substantive-output scenario; future validation changes may bake accidental content into expectations Restore an intentional synthetic reviewer output (or co-update tests and documentation if the scenario changed on purpose)
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## risk-integration: scripts/launch-claude-review.sh:105-111 and scripts/dispatch-code-voters.sh (voter wiring)

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Voter role no longer receives diff/plan/scope context files forwarded to the subprocess. Voter asked to verify ballot claims against the diff never sees that diff while dispatch accepts symlink/large diff paths; votes can look valid but be ungrounded. Restore bounded diff context for voters or document the intentional loss of diff-grounded verification in voter contracts.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## architecture: implementation_plan scope vs branch diff (scripts/collect-agent-results.sh, scripts/dispatch-code-voters.sh, scripts/launch-claude-review.sh, skills/review/scripts/*.sh and tests)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Large unrelated collector retry, voter dispatch, Claude launcher role, and review harness changes bundled with Bash 3.2 lint work Reviewers expect a bash32-only PR; mixed semantics increase regression and rollback risk and violate the stated implementation_plan file list Split unrelated changes into their own PR or update the authoritative plan/requirements to include them
- **Suggested revision**: Address the concern above.

