# Review Round 5

- Mode: `diff`
- 6 accepted, 7 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Dev permissions still reference deleted bump-version skill
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `.claude/settings.json` still allows `Skill(bump-version)` and dead bump-version script paths after the skill tree was deleted, while `/release` lacks corresponding Skill/script allowances for plugin contributors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_10: verify-skill-called lost git_error coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-verify-skill-called.sh` still claims `git_error` coverage after deleting the test that exercised it, leaving `verify-skill-called --commit-delta` vulnerable to regressing error handling without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: LARCH_BUMP_FILES behavior changed too quietly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `docs/configuration-and-permissions.md` describes `LARCH_BUMP_FILES` after its semantics changed from drop-bump behavior to conflict-path aliasing, leaving existing consumer env vars with little warning that old behavior vanished.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Version-bump rule points to deleted /bump-version
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `.claude/rules/version-bump-reserved-message.md` still instructs users to invoke non-existent `/bump-version` guidance when editing `plugin.json`, instead of current `/release` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: Stale ship-pr comment references removed replay logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` contains a stale comment about drop/rebase replay logic removed in this phase, which may mislead maintainers searching for removed drop-bump behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: release-prepare default-path test allows stub classifier to pass
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/release/scripts/test-release-prepare.sh` Case 14 only verifies that `BUMP_TYPE=` and `NEW_VERSION=` exist, so a wrong default `CLASSIFY_BUMP` path or stub classifier could pass while bare `/release` fails in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


