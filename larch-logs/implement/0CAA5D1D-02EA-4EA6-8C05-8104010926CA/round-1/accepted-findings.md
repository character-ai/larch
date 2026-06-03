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


