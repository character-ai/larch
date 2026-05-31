Normalized aggregator output from the supplied reviewer slots (merged by shared behavioral risk; first-seen ID order).

### FINDING_1: Missing committed `python/bump_worktree.py` breaks imports/CI
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Committed modules (`version_bump`, `changelog`, tests) import `bump_worktree`, but `python/bump_worktree.py` is not on HEAD / not in the branch diff. Clean checkout, `make py-test`, and Python Tests CI fail with `ModuleNotFoundError` on import.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add and commit `python/bump_worktree.py` (or inline helpers into a committed module).
  - From cursor-specialist-testing-output.txt: `git add` and commit `python/bump_worktree.py`; add `test_bump_worktree.py` if desired.
  - From cursor-specialist-edge-cases-output.txt: Add and commit `python/bump_worktree.py` with the Phase 2 port commits.
  - From cursor-specialist-plan-fidelity-output.txt: Commit `python/bump_worktree.py` or remove the import by inlining shared helpers.

### FINDING_2: `apply_bump` is an oversized function with nested closures
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `apply_bump` (~160 lines) embeds staging rollback and `origin/main` retry logic in nested closures. Same-version-race or regression fixes require editing one large function, increasing subtle-regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract stage/rollback and fetch-verify-retry helpers to module-level functions.

### FINDING_3: Duplicate Markdown/RST format detection paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `detect_format` and `_detect_conflict_format` duplicate format-detection rules with slight differences. Extensionless conflict paths may classify differently than commit/detect paths after a one-sided edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate into one shared format resolver used by `auto_resolve` and `detect_format`.

### FINDING_4: `sorted_changed_files` sort order may diverge from bash `LC_ALL=C`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `sorted_changed_files` sorts paths by UTF-8 bytes; bash `drop-bump-commit.sh` uses `LC_ALL=C sort`. For non-ASCII paths in `LARCH_BUMP_FILES`, Guard 4 exact-equality vs drop-bump behavior could diverge (unexpected changed-files string vs drop, or the opposite).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align with `LC_ALL=C` semantics or add a parity fixture with non-ASCII filenames.
  - From cursor-specialist-correctness-output.txt: Use `LC_ALL=C` byte-sort parity (subprocess `sort` or `locale.strxfrm`) or restrict/document ASCII-only bump paths.
  - From cursor-specialist-edge-cases-output.txt: Restrict to ASCII paths or use a documented C-locale byte-sort helper.

### FINDING_5: `changelog.py` is a large mixed-responsibility module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `changelog.py` combines pure transforms, git wrappers, and `auto_resolve` in one large file, making navigation and Phase 7 driver wiring review harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider splitting pure text helpers when next editing the module.

### FINDING_6: Duplicate `ProcRunner` test adapter across test modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test_version_bump` and `test_changelog` each define a duplicate `ProcRunner` test adapter; `Runner` protocol changes require duplicate edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share via `conftest` or a `test_helpers` module.

### FINDING_7: `commit_changelog` is Markdown-only; RST commit path missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `commit_changelog` only commits Markdown changelogs while RST text operations are implemented. Callers or Phase 7 wiring passing `CHANGELOG.rst` get `committed=False` / errors despite plan/README implying broader changelog surface; bash commit path is also MD-only today, but Python API and plan acceptance still leave an RST commit gap for Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep README deferral; implement RST commit when wiring live path.
  - From cursor-specialist-correctness-output.txt: Document in plan or defer RST commit explicitly until Phase 7 (README already notes deferral).
  - From cursor-specialist-edge-cases-output.txt: Phase 7: add RST commit path or document that only `write_changelog_entry` + manual commit is supported until then.
  - From cursor-specialist-plan-fidelity-output.txt: Implement RST path in `commit_changelog` or formally narrow Phase 2 plan acceptance away from "every operation."

### FINDING_8: [OUT_OF_SCOPE] Overlapping `status()` / `status_porcelain()` in `git.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Overlapping `status()` and `status_porcelain()` APIs in `git.py`; pre-existing; Phase 2 only adds `status_porcelain`. Consolidation belongs in a dedicated `git.py` cleanup outside this phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate in a dedicated `git.py` cleanup outside this phase.

### FINDING_9: `commit_changelog` parity tests lack `COMMITTED=true` / log-subject coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Bash parity tests for `commit_changelog` only cover `COMMITTED=false`. Future retitle/insert bugs could leave pytest green while `commit-changelog.sh` commits a different heading/subject on a real repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add twin-repo parity with pre-seeded heading or `--replaces-version` asserting `COMMITTED=true` and log subject.

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

### FINDING_12: `test_parity_apply_bump_clean_repo` may not prove successful apply parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Test uses a repo without `origin`; both sides likely `APPLIED=false`. Test can pass on mutual fetch failure without proving successful apply parity on a clean tree with `origin`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rename to document failure parity or use `_init_repo_with_origin` and assert `APPLIED=true` and version/commit fields.

### FINDING_13: Drop-bump rebase-onto path lacks bash parity coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `drop_replay_commit` rebase branch could diverge from `drop-bump-commit.sh` without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `test_parity_drop_bump_below_head` mirroring plugin-only parity pattern.

### FINDING_14: No colocated `test_bump_worktree.py`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No `test_bump_worktree.py`; shared drop helpers regress with only indirect coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `python/test_bump_worktree.py` for `sorted_changed_files` and `drop_replay_commit` edge cases.

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

### FINDING_17: `bump_branch_guard` stall messages skip `redact_outbound`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Stalled messages skip `redact_outbound`. Phase 7 may surface Stalled to operators with branch names or path-like secrets verbatim in logs/KV output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Wrap stall messages with `redact.redact_outbound` before raise `Stalled`; add regression test.

### FINDING_18: `check_bump_version_pre` touches sentinel at unvalidated `implement_tmpdir`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A compromised or mistaken `implement_tmpdir` (or symlinked directory) could create `.bump-version-armed` outside the intended session tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve and confine `implement_tmpdir` under trusted session root before touch; skip on escape.

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

### FINDING_21: `drop_replay_commit` stuck mid-rebase when abort fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When rebase `--onto` fails and `--abort` fails, repo is left in rebase state; drop returns error only. Phase 7 driver should treat as stall requiring manual `git rebase --abort`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Keep explicit error; Phase 7 driver should treat as stall requiring manual `git rebase --abort`.

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

### FINDING_24: `bump_worktree.py` missing from plan/README module inventory
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `bump_worktree.py` is not listed in the implementation plan but is required by the port; integrators may omit it when tracing Phase 2 deliverables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add `bump_worktree.py` to plan/README module inventory once committed.

### FINDING_25: `_rst_section_end_index` mis-inserts when Unreleased has subsections but no release section
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: important
- **Concern**: When `_rst_release_section_indices` is empty, fallback uses the next generic RST title after the anchor. For Unreleased with subsections (e.g. `Changed`) but no `Version X.Y.Z` yet, insert can land before subsection content instead of after the full Unreleased body. Existing test only covers downstream `Version` line present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-changelog-text-logic-output.txt: When the anchor is not in `release_indices`, treat the section end as the next *release* title if any exist; otherwise walk `_rst_title_indices` but only stop at titles at the same structural level as the anchor (e.g. same adornment rank as the anchor’s underline), or scan forward to EOF when no semver release exists—then add a unit test for “Unreleased + subsection, no Version yet” asserting the new entry lands after all Unreleased content.

### OOS_1: [OUT_OF_SCOPE] Phase 7 may assume RST `commit_changelog` works
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: RST `commit_changelog` deferred to Phase 7 while RST text ops exist; Phase 7 driver may assume `.rst` commit works when only Markdown commit path exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Track Phase 7 task for RST `commit_changelog` or document API limitation in module docstring.

### OOS_2: [OUT_OF_SCOPE] `python-tests` workflow does not pin bash/git/gawk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python-tests` does not explicitly install git/bash/gawk; future runner image change could skip many parity tests via `skipif`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add explicit apt install or smoke step asserting bash, git, gawk available.

### OOS_3: [OUT_OF_SCOPE] `ShipError` may include full git argv
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Uncaught `ShipError` could leak sensitive path literals in argv to stdout/stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact argv in operator-facing `ShipError` paths or avoid `_ensure_success` for sensitive ops.

### OOS_4: [OUT_OF_SCOPE] Bash leaves CHANGELOG modified on commit failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing bash behavior: `commit-changelog.sh` leaves CHANGELOG modified on commit failure (no restore). Python partial restore can worsen index vs worktree (see in-scope FINDING_20).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address via Python fix above; optional bash alignment separately.

### OOS_5: [OUT_OF_SCOPE] `apply_bump` git commit is not path-scoped (`--only`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-existing bash parity; mitigated by clean-tree precheck. No change required for Phase 2; optional `--only` in Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: No change required for Phase 2; optional `--only` in Phase 7.

### OOS_6: [OUT_OF_SCOPE] UTF-8 sort matches `LC_ALL=C` for ASCII bump paths
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: UTF-8 byte sorting matches `LC_ALL=C` for ASCII paths (common bump set) and is tested in `test_version_bump.py:999-1019`; non-ASCII edge cases remain theoretically locale-sensitive in bash-only callers.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Parity tests normalize boolean KV with `.lower()`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Parity tests bridge Python `True`/`False` and bash `true`/`false` correctly; not a defect.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] `_git_subprocess_env` mitigates locale for Guard 4 re-sort
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Environment setup covers rebase/reset parity; Guard 4 comparisons re-sort in Python before equality, mitigating locale concern for those paths.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Inherited exact-line dedupe in auto-resolve
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: nit
- **Concern**: `seen` line dedupe matches bash `auto-resolve-changelog.sh`; inherited semantics, not a Python regression.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] `_rst_second_title_index` sentinel `0` matches bash
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: nit
- **Concern**: Same sentinel as bash; callers guard with `second2 > 0`; no functional bug found.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_11: [OUT_OF_SCOPE] `idx > anchor + 1` skips anchor underline by design
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: nit
- **Concern**: Intentionally skips anchor underline when choosing next generic RST title; consistent with title-line indexing.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_12: [OUT_OF_SCOPE] `_write_md_entry` double-call path does not double-insert
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: nit
- **Concern**: Fallback does not stack two inserts on one buffer; no defect found.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Summary**: 25 in-scope merged findings; 12 out-of-scope (`OOS_1`–`OOS_12`). Highest-impact clusters: untracked `bump_worktree.py` (FINDING_1), RST/commit surface gaps (FINDING_7, FINDING_23), `commit_changelog` failure-path staging (FINDING_20), classify-bump and changelog commit parity test holes (FINDING_9, FINDING_11, FINDING_23), and RST insert logic without release sections (FINDING_25). Dyn-changelog “no bug” OOS notes are retained for voter context without suggested fixes where none were given.
