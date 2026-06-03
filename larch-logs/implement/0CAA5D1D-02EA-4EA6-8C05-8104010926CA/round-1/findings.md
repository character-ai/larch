### FINDING_1: Phantom check-release references remain in docs/lint config
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Documentation and agent-lint comments/excludes still reference deleted `scripts/check-release.sh`, `check-release.md`, or `test-check-release.sh`, misleading contributors into expecting a release gate that no longer exists. The remaining contract should describe `lib-count-commits.sh` only as used by `verify-skill-called.sh` / its harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Installation docs describe a missing Skill PostToolUse hook
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `docs/installation-and-setup.md` claims `hook-post-release.sh` runs as a Skill `PostToolUse` hook, but `hooks/hooks.json` no longer registers that hook and the script is absent. Contributors may assume resume or bump hygiene is enforced when it is not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: Tmpdir resolver checks an unwritten release-armed sentinel
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `lib-resolve-implement-tmpdir.sh` now looks for `.release-armed`, but nothing writes that sentinel and existing tmpdirs may still contain `.bump-version-armed`. Resumed `/implement` sessions can fail tmpdir resolution, which can prevent Stop hook or SessionStart logic from binding to the active run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Python README still documents deleted bump/rebase modules and behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/README.md` still lists deleted `bump_worktree.py` and stale `rebase.py` rebump/changelog behavior. Contributors working on the Phase 7 Python port may search for or design against modules and capabilities that no longer exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Configuration docs truncate OOS cap sections and leave LARCH_VERSION_FILES empty
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `docs/configuration-and-permissions.md` lost the `OOS_ISSUES_PER_RUN_CAP` and `OOS_ISSUE_CAP_EXCERPT_MAX` sections and leaves `LARCH_VERSION_FILES` without a body. Operators lose the canonical documentation for OOS cap fail-closed behavior and version-file configuration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: LARCH_BUMP_FILES rename lacks compatibility or migration docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `LARCH_BUMP_FILES` was renamed to `LARCH_VERSION_FILES` without an alias, fallback, warning, or clear migration documentation. Existing consumer CI exporting the old variable can silently lose custom version-file conflict classification during `ship-pr` rebase handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: classify-bump NEW_VERSION arithmetic is inconsistent for leading-zero components
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/classify-bump.sh` uses partial `10#` arithmetic when formatting `NEW_VERSION`, which can diverge from release-prepare decimal handling for pathological leading-zero semver components.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Postbump state requires unused BUMP_REASONING_FILE
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-finalize.sh` writes/requires `BUMP_REASONING_FILE` in postbump state, but that key is not read later. Resume/debug readers may infer a post-Phase-5 dependency that does not exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] SECURITY.md still describes removed bump/release hook behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` still references removed bump/PostToolUse hook behavior, changelog/postbump inputs, and old bump resume sentinels. Operators or security reviewers may apply obsolete trust-boundary checks or recovery steps during implement stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Tmpdir resolver comment still references post-bump hooks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: A comment in `lib-resolve-implement-tmpdir.sh` references post-`/bump` hooks while the code now uses `.release-armed`, causing minor confusion when tracing tmpdir resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Python parity coverage gap after removing bump/changelog tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Removed bash↔Python and rebump/drop integration tests leave Phase 7 Python `ship-pr` behavior able to diverge from bash on rebase/conflict paths without CI detection until a later parity harness lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Rebase structural harness lacks negative pins for deleted changelog/bump scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ship-pr-rebase.sh` pins absence of `classify-bump` but not deleted changelog/auto-resolve script basenames. A mistaken re-add of removed sources could pass the structural test and fail only at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: CHANGELOG conflicts now fall through to vendor rebase handling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Removing CHANGELOG auto-resolve from the rebase prepass means legacy branches with CHANGELOG conflicts can stall or consume fixer rounds where prior `auto-resolve-changelog.sh` behavior may have succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: classify-bump idempotency no longer treats CHANGELOG-only commits as transparent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Standalone `classify-bump` without `--base` may return `PATCH` instead of `NONE` on a bump plus CHANGELOG-only tip because CHANGELOG commits are no longer transparent in the idempotency walk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
