### FINDING_7: architecture: implementation_plan scope vs branch diff (scripts/collect-agent-results.sh, scripts/dispatch-code-voters.sh, scripts/launch-claude-review.sh, skills/review/scripts/*.sh and tests)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Large unrelated collector retry, voter dispatch, Claude launcher role, and review harness changes bundled with Bash 3.2 lint work Reviewers expect a bash32-only PR; mixed semantics increase regression and rollback risk and violate the stated implementation_plan file list Split unrelated changes into their own PR or update the authoritative plan/requirements to include them
- **Suggested revision**: Address the concern above.



