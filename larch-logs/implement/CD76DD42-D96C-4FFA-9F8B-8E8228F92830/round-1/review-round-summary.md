# Review Round 1

- Mode: `diff`
- 3 accepted, 11 rejected (11 exonerated)

## Accepted Findings

### FINDING_14: Refusal banner hardcodes `~/.cache` instead of the actual marker path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The banner tells operators to delete a `~/.cache` path even though the helper uses `$HOME`; with a non-tilde `HOME`, the operator may delete the wrong file and remain blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use design_reentry_marker_path / DESIGN_REENTRY_MARKER_PATH in banner text; update Check 26 literal accordingly.


### FINDING_19: Guard-hit reference Bash omits the final summary invocation
- **Reviewer(s)**: dyn-integration-contract-output.txt, dyn-prompt-orchestrator-output.txt
- **Severity**: important
- **Concern**: The guard-hit reference block says to run the final summary but only contains a comment before printing the refusal banner and exiting. An orchestrator following that fence literally will skip the structured cancelled-reentry summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-integration-contract-output.txt: Replace the comment with the full Final summary fence body (or a direct `render-final-summary.sh --outcome cancelled-reentry-guard --post-publish-only` call) between the exports and the stderr banner, and align prose/reference ordering so summary render precedes banner emission.
  - From dyn-prompt-orchestrator-output.txt: Inline the same `render-final-summary.sh --post-publish-only` callsite from the `### Final summary block` fence (lines 330–345) into the guard-hit branch before the `printf` banner, or delete the partial reference fence and point only at the shared fence like sub-step 2.5 refuses do; add a structural check that the Step 0b guard-hit path references `render-final-summary.sh` / `cancelled-reentry-guard` between `design_reentry_marker_hit` and the session-cache banner.


### FINDING_3: Sourced re-entry guard library is missing from dead-script excludes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/lib-design-reentry-guard.sh` is sourced-only but is not excluded in `agent-lint.toml`, so `make lint` / pre-commit can flag it as dead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add lib to agent-lint.toml exclude with comment mirroring lib-title-eligibility.
  - From cursor-specialist-testing-output.txt: Add scripts/lib-design-reentry-guard.sh (and .md if needed) to agent-lint.toml exclude alongside lib-title-eligibility.sh.
  - From cursor-specialist-plan-fidelity-output.txt: Add scripts/lib-design-reentry-guard.sh to exclude with sourced-only comment mirroring lib-title-eligibility.sh.


