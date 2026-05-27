### FINDING_1: Voter 1 backfill uses `_wait_rc` after cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/dispatch-code-voters.sh` unsets `_wait_rc` before the Voter 1 synthetic `.done` backfill gate still depends on it. Reviewers describe failure modes including `set -u` aborts, incorrectly creating `.done` after wait helper failure, or failing to backfill valid output, which can misclassify Voter 1 before tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: Branch contains unrelated work outside the implementation plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch includes orphan-script, Codex telemetry, parser, security, and test changes outside the #2973 implementation plan. This broadens review, release-note, rollback, and bisect risk beyond the planned voter-failure fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_13: Changelog omits the primary voter/stdin/sidecar fixes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `CHANGELOG.md` does not document the #2973 voter/stdin/sidecar fixes, while the visible 42.6.1 entry only mentions orphan-script work. Operators would not see the primary branch behavior in release notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: Timeout stderr harness case is undocumented
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-run-external-agent.md` does not document case 18 for capture-stdout-only timeout stderr behavior, making the harness coverage harder to discover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


