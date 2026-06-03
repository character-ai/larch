### FINDING_1: SECURITY.md documents removed post-bump PostToolUse hook
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: SECURITY.md still describes a Plugin-shipped PostToolUse Skill hook running `hook-post-bump-version.sh`, but Phase 5 removed the hook registration and deleted the script. Operators/auditors may believe bump-resume hygiene is hook-enforced when shipped `hooks.json` no longer does that.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: SECURITY.md postbump trust-boundary docs still mention removed changelog inputs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: SECURITY.md still documents `--changelog-bullets-file` and changelog fail-closed postbump behavior that was removed from `implement-finalize.sh`. Readers may implement, audit, or call a non-existent postbump input surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Research eval set still asks about deleted rebase-rebump procedure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/research/references/eval-set.md` eval-7/eval-15 still reference the removed rebase-rebump sub-procedure, so eval scoring can reward answers grounded in deleted behavior instead of CI-fix rebase/conflict-resolution docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: git-sync-local-main contract still frames caller as classify-bump re-bump
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/git-sync-local-main.md` still describes classify-bump/re-bump usage, which can confuse maintainers about why the helper runs during ship-pr CI-fix rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: git-force-push contract still references re-bump sub-procedure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/git-force-push.md` still documents Re-bump Sub-procedure and rebase+re-bump call sites, creating stale maintainer guidance for CI-fix force-push behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Postbump state contract retains unused or ghost bump keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Postbump state still requires or emits bump-era keys such as `BUMP_REASONING_FILE`, `MANIFEST_PATH`, `TOOL_LABEL`, and `HAS_BUMP` even though current postbump logic no longer reads/validates them. Future edits and debugging may treat these as meaningful contract fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Semver leading-zero arithmetic lacks full 10# handling/regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `classify-bump.sh` NEW_VERSION computation does not consistently force all semver components through `10#` decimal arithmetic, and tests lack leading-zero coverage. Versions with leading-zero components could mis-increment; one source scoped this as pre-existing/out-of-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] refresh-run-logs docs still say “after re-bump”
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/refresh-run-logs.md` Trigger A prose still references re-bump, a pre-existing doc drift not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] merge-pr version_already_published errors still mention rebase/re-bump
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/merge-pr.sh` error strings still mention rebase and re-bump, causing stale operator guidance after per-PR bump removal; source marked it pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] classify-bump CHANGELOG transparency/idempotency path remains untested and potentially stale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `classify-bump.sh` and Python version-bump logic still contain CHANGELOG-only transparent-walk/idempotency behavior while tests for that path were removed. Direct classifier callers or legacy branches with historical CHANGELOG-only commits could misclassify; multiple sources scoped this as pre-existing/out-of-scope for direct CLI use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: linting docs assign test-classify-bump to wrong harness shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `docs/linting.md` says `test-classify-bump` belongs to `test-harnesses-10`, but the Makefile assigns it to `test-harnesses-20`, so shard debugging/rebalancing follows stale documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: ship-pr rebase harness does not guard against deleted changelog script references
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ship-pr-rebase.sh` only forbids `classify-bump.sh` references and would not catch a partial revert that re-sources deleted changelog helper scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: classify-bump uses predictable TMPDIR fallback reasoning filename
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: When `IMPLEMENT_TMPDIR` is not writable, `classify-bump.sh` falls back to a fixed `bump-version-reasoning.md` path under `TMPDIR`, creating a possible symlink race on multi-user systems.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] release-prepare classifier override accepts any executable path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_RELEASE_PREPARE_CLASSIFY_BUMP` can point `release-prepare.sh` at any executable with only `-x` validation, allowing mistaken or compromised env overrides to execute attacker-controlled code; source marked this as pre-existing hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: ship-pr legacy CHANGELOG conflicts lost deterministic auto-resolve behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Removing deterministic CHANGELOG auto-resolve from the CI-fix rebase prepass can make legacy branches with CHANGELOG commits stall or fall into broader conflict-resolution paths without targeted guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Alias skill still says /implement includes version bump
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `skills/alias/SKILL.md` still lists version bump as part of the `/implement` pipeline, implying alias-driven implement runs still bump per PR despite the Phase 1/5 contract moving versioning to `/release`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
