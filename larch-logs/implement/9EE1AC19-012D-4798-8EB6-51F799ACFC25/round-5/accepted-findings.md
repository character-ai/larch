### FINDING_1: Missing committed `python/bump_worktree.py` breaks imports/CI
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Committed modules (`version_bump`, `changelog`, tests) import `bump_worktree`, but `python/bump_worktree.py` is not on HEAD / not in the branch diff. Clean checkout, `make py-test`, and Python Tests CI fail with `ModuleNotFoundError` on import.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add and commit `python/bump_worktree.py` (or inline helpers into a committed module).
  - From cursor-specialist-testing-output.txt: `git add` and commit `python/bump_worktree.py`; add `test_bump_worktree.py` if desired.
  - From cursor-specialist-edge-cases-output.txt: Add and commit `python/bump_worktree.py` with the Phase 2 port commits.
  - From cursor-specialist-plan-fidelity-output.txt: Commit `python/bump_worktree.py` or remove the import by inlining shared helpers.


### FINDING_10: Frontmatter detection uses `strip()` instead of exact `---` lines
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Frontmatter opener uses `strip()` not `^---$`. A first line like ` ---` may be read as bogus frontmatter in Python while bash ignores it, causing MINOR/MAJOR flag classification to diverge from `classify-bump.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use `lines[0] == "---"` and closing line `== "---"` like `classify-bump.sh` awk.


### FINDING_11: No bash parity for `classify-bump` MAJOR/MINOR/PATCH from skill/agent diffs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No twin-repo bash parity for classify-bump from skill/agent diffs. Python `classify_bump` can diverge from `classify-bump.sh` while idempotency/NONE parity stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add twin-repo tests: seed skill changes, run bash `classify-bump.sh`, and compare `BUMP_TYPE`/`NEW_VERSION` to `classify_bump()`.


### FINDING_13: Drop-bump rebase-onto path lacks bash parity coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `drop_replay_commit` rebase branch could diverge from `drop-bump-commit.sh` without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `test_parity_drop_bump_below_head` mirroring plugin-only parity pattern.


### FINDING_15: `git.diff_tree_name_only` lacks StubRunner argv test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `git.diff_tree_name_only` has no StubRunner argv test; argv regression in idempotency path less likely to be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add StubRunner test for `diff-tree --name-only -r` invocation.


### FINDING_16: lib-changelog parity silently skips without `gawk`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Parity test skips when `gawk` is missing; minimal CI without `gawk` skips `first_version_heading` parity silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document gawk prerequisite or install gawk in python-tests workflow.


### FINDING_19: `LARCH_BUMP_FILES` parsing ignores colon-in-segment rule
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Mis-set env can split paths wrong and weaken Guard 4 drop safety vs documented contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject segments containing `:`; fail-closed like empty parse.


### FINDING_20: `commit_changelog` leaves staged index after failed commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: On `git commit` failure after successful `git add`, Python restores the worktree but does not unstage, leaving index/worktree mismatch. Bash does not produce that state. This also diverges from bash fail-closed semantics (bash leaves modified content on disk with `COMMITTED=false`); Python rollback without unstage can worsen inconsistent git state for retries/classify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: On commit (and add) failure: restore file and call `git.unstage(runner, path)` like `apply_bump` rollback.
  - From dyn-bash-parity-output.txt: Match bash fail-closed semantics (leave the modified file on disk, no rollback) or, if rollback is intentional, also call `git.unstage(runner, path)` and document the intentional deviation; add a parity test that forces commit failure and compares post-failure porcelain state.


### FINDING_22: `apply_bump` omits bash stderr WARN for tolerated untracked artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: When only larch-internal untracked artifacts are present, bash emits a `WARN:` line naming tolerated files; Python filters silently. KV may match, but operators and parity harnesses grepping stderr will not see the same signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit redacted WARN when skipping tolerated untracked lines.
  - From dyn-bash-parity-output.txt: Emit the same stderr `WARN: larch-internal untracked artifacts present (tolerated before bump): …` message when `_tolerated_untracked` lines are the sole porcelain entries, and add a unit/parity assertion on stderr content.


### FINDING_23: `commit_changelog` missing `Co-Authored-By` trailer vs `git-commit.sh`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python commits via `git.commit(runner, msg, only=path)` while bash `commit-changelog.sh` uses `git-commit.sh` staging plus `Co-Authored-By: Claude Code <noreply@anthropic.com>` trailer. Commit objects differ even when `COMMITTED=true` and subject match; parity tests only compare `COMMITTED` KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Route changelog commits through the same trailer/staging contract as `git-commit.sh` (either shell out to that script or replicate its `git add` + `interpret-trailers` + `git commit --file` sequence in Python) and add a parity assertion on `git log -1 --format=%B`.


### FINDING_25: `_rst_section_end_index` mis-inserts when Unreleased has subsections but no release section
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: important
- **Concern**: When `_rst_release_section_indices` is empty, fallback uses the next generic RST title after the anchor. For Unreleased with subsections (e.g. `Changed`) but no `Version X.Y.Z` yet, insert can land before subsection content instead of after the full Unreleased body. Existing test only covers downstream `Version` line present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-changelog-text-logic-output.txt: When the anchor is not in `release_indices`, treat the section end as the next *release* title if any exist; otherwise walk `_rst_title_indices` but only stop at titles at the same structural level as the anchor (e.g. same adornment rank as the anchor’s underline), or scan forward to EOF when no semver release exists—then add a unit test for “Unreleased + subsection, no Version yet” asserting the new entry lands after all Unreleased content.


### FINDING_9: `commit_changelog` parity tests lack `COMMITTED=true` / log-subject coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Bash parity tests for `commit_changelog` only cover `COMMITTED=false`. Future retitle/insert bugs could leave pytest green while `commit-changelog.sh` commits a different heading/subject on a real repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add twin-repo parity with pre-seeded heading or `--replaces-version` asserting `COMMITTED=true` and log subject.


