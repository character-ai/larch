### FINDING_13: implement structure harness greps were corrupted by removed bump files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: test-implement-structure.sh still expects retirement-stub/reference markers in the wrong places after bump-verification and rebase-rebump-subprocedure removal, causing make lint failure and misclassifying conflict-resolution.md as a retirement stub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: docs and eval references invented nonexistent check-release.sh
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Several docs/eval references replaced deleted check-bump-version.sh with nonexistent check-release.sh, causing operators or harnesses to look for a script that does not exist and validating the wrong surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: classify-bump relocation changed behavior beyond rename-only plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The relocate appears to have changed idempotency and reasoning-file path/default classify behavior beyond the plan’s byte-equivalent git-mv contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: AGENTS.md canonical source points to deleted bump-version skill
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: AGENTS.md still identifies .claude/skills/bump-version/SKILL.md as the authoritative classification source even though that path was deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: anti-halt harness docs claim coverage that no longer exists
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: scripts/test-implement-anti-halt.md claims post-/release Step 8 anti-halt pins, but the shell harness no longer asserts those checks and SKILL.md lost the unique needles. The documented regression boundary can pass while untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: classify-bump PATCH log text still states obsolete mandatory-bump policy
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: classify-bump.sh and python/version_bump.py still describe every PR as requiring at least PATCH, which misstates the release-classification default for operators reviewing bump decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_4: lib-resolve comments still imply removed bump hook machinery
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Comments around .release-armed still tie the resolver to removed post-/bump hooks and SessionStart behavior, risking future reintroduction of retired machinery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: sessionstart-health harness prose contradicts retired bump advisory behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: scripts/test-sessionstart-health.md still describes combined review+bump boundary advisories while the tests assert bump advisories are retired, inviting incorrect test or SessionStart changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


