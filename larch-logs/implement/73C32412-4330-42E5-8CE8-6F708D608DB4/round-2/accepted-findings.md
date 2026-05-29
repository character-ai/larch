### FINDING_1: lib-quiet.md still uses Family B terminology
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Stage 4 removed shim docs but the Invariants section still labels callers as Family B scripts. Contributors editing lib-quiet after the rip-out may think Family-B pairing rules still apply to larch_err progress lines. Reword to long-running quiet scripts (or list ship-pr/ci-wait/collect-agent-results) and remove Family B terminology.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_2: SECURITY.md bullet 1 still titled “Live streams”
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Bullet 1 still titled Live streams after live monitor machinery was deleted. Security reviewers may believe FD-3 live breadcrumb streaming remains a runtime surface. Retitle bullet 1 to session breadcrumb directories and match docs/run-logs.md quiet-log publication wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_7: Structure harness gaps for fence-collapsed skill docs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Stage 4 absence assertions exist only for brainstorm.md and implement SKILL.md, not for other fence-collapsed skill docs the plan names. A contributor reintroduces Family-B fence prose in research-phase.md or plan-review.md; make lint and existing structure harnesses stay green until manual grep at PR close. Port the #3119 hex-encoded grep-absence block (or a shared function) to every orchestrator .md file listed in the plan, starting with research-phase.md, validation-phase.md, plan-review.md, and heavy-worker.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: test-collect-agent-results.sh C_OK vs C_DONE label mismatch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Case comment says C_OK but assert_line label still says C_DONE. Failed harness output shows C_DONE while the case comment says C_OK, slowing triage on collector regressions. Align assert_line label with C_OK (or revert the case id everywhere).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


