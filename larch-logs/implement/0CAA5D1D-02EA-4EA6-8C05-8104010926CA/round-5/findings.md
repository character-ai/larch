### FINDING_1: Dev permissions still reference deleted bump-version skill
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `.claude/settings.json` still allows `Skill(bump-version)` and dead bump-version script paths after the skill tree was deleted, while `/release` lacks corresponding Skill/script allowances for plugin contributors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_4: RebaseResult exposes always-empty new_version field
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/rebase.py` keeps `RebaseResult.new_version` as a public dataclass field even though it is always `None`, inviting future Python ship code to branch on a rebump result that no longer exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: classify-bump semver formatting misses full 10# normalization
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/classify-bump.sh` does not apply `10#` normalization to all MINOR/PATCH semver components, so rare leading-zero inputs could produce inconsistent `NEW_VERSION` formatting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] run_rebase_rebump name still implies rebump behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` retains `run_rebase_rebump` naming from the old rebump path, which may confuse maintainers even though the rename was intentionally deferred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Legacy .bump-version-armed sentinel naming remains
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/lib-resolve-implement-tmpdir.sh` still uses `.bump-version-armed` sentinel naming after bump-version skill deletion, which is confusing for operators/debugging but not functionally broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: release-prepare default-path test allows stub classifier to pass
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/release/scripts/test-release-prepare.sh` Case 14 only verifies that `BUMP_TYPE=` and `NEW_VERSION=` exist, so a wrong default `CLASSIFY_BUMP` path or stub classifier could pass while bare `/release` fails in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: ship-pr rebase test under-pins removed bump/changelog symbols
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-ship-pr-rebase.sh` pins classify-bump absence but not other deleted changelog/rebump basenames or call sites, so reintroducing removed prepass logic may not fail the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: verify-skill-called lost git_error coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-verify-skill-called.sh` still claims `git_error` coverage after deleting the test that exercised it, leaving `verify-skill-called --commit-delta` vulnerable to regressing error handling without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: verify-skill-called 5b accepts nonnumeric count_commits output
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-verify-skill-called.sh` section 5b only checks that sourcing from `/tmp` emits output, not that `count_commits` returns a numeric count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] python-tests do not smoke-test bash/git prerequisites
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `.github/workflows/ci.yaml` does not explicitly assert bash/git availability before `make py-test`, so parity tests could be silently skipped or degraded on a future runner image.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] classify-bump override remains arbitrary executable footgun
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/release-prepare.sh` still honors `LARCH_RELEASE_PREPARE_CLASSIFY_BUMP` as an arbitrary executable path without an explicit opt-in guard or SECURITY.md documentation; this predates the phase and only the default path changed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Removed bump hook reduces legacy halt protection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Removing the PostToolUse bump hook and `.bump-version-armed` stop guard reduces halt protection during legacy bump flows; the reviewer marks this as intentional Phase 5 operational risk, not a new confidentiality boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Rebase prepass no longer auto-resolves CHANGELOG conflicts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/ship-pr.sh` no longer auto-resolves CHANGELOG conflicts during feature-branch rebase, so branches rebasing onto upstream CHANGELOG changes may stall or route to the wrong conflict path instead of the former silent prepass fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: classify-bump --head does not require HEAD OID equality
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/classify-bump.sh --head` can accept a version match without verifying that `HEAD` equals `HEAD_COMPARE`, allowing direct `--head-only` use to classify the wrong commit tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: LARCH_BUMP_FILES behavior changed too quietly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `docs/configuration-and-permissions.md` describes `LARCH_BUMP_FILES` after its semantics changed from drop-bump behavior to conflict-path aliasing, leaving existing consumer env vars with little warning that old behavior vanished.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: subskill invocation docs misstate /implement and /release relationship
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/shared/subskill-invocation.md` contains stale Phase 1/5 wording suggesting `/implement` no longer nests or gates `/release`, rather than accurately saying per-PR bump/CHANGELOG gates were removed from the ship path and `/release` remains the external versioning path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
