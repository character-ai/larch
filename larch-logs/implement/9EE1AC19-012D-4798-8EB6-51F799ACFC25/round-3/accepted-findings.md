### FINDING_1: Duplicate MD anchor-insertion logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_write_md_entry` duplicates anchor-insertion logic from `_insert_md_at_anchor`. Fixing Unreleased/SemVer anchor behavior in one path leaves the other wrong; `write_changelog_entry` and commit paths can diverge silently. Reuse `_insert_md_at_anchor` or extract one shared anchor helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_11: Weak classify idempotency parity coverage (cases 3–4)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_parity_classify_idempotency_cases` test3/test4 omit harness fixtures; only assert Python equals bash on a bare repo. `larch-logs` transparent NONE and CHANGELOG-over-feature PATCH edges are never asserted; bash and Python can agree on the wrong PATCH. Port `test-classify-bump.sh` cases 3–4 fixtures; assert expected `BUMP_TYPE`, not only bash==py.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Missing bash-parity test for RST `auto_resolve`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No bash-parity test for RST `auto_resolve` vs `auto-resolve-changelog.sh` (plan acceptance). Only a private `_auto_resolve_rst` unit test exists. RST merge can diverge from awk/bash while CI passes; Phase 3 RST conflict resolution risk. Add skipif-guarded subprocess parity with identical `:2:`/`:3:` RST stages (or twin-repo fixture against `scripts/auto-resolve-changelog.sh`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_13: `test_parity_auto_resolve_subprocess` can skip without exercising parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test_parity_auto_resolve_subprocess` skips when merge or bash resolve fails. CI can stay green with zero subprocess parity runs if the fixture stops conflicting. Use a deterministic conflict fixture or fail when the parity path is not exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Missing test for drop_bump exact file-set guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Missing unit/integration test for `drop_bump` exact file-set guard (extra file refuses drop). Subset bug could drop bump commits that bash would refuse. Add test: bump changes `plugin.json` plus extra file; expect `dropped=False`; optional bash KV parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_23: `rebase --abort` result ignored after failed drop
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `rebase --abort` result ignored after failed `drop` `rebase_onto`. Repo may stay in rebase state after failed drop. Check abort return code; return explicit recovery error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_25: Untested RST blank/absent extract cases
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan requires extract blank/absent cases for Markdown and RST; RST blank extract is untested. Blank RST version sections could return wrong body without test failure. Add `test_rst_extract_blank_returns_none` (and optional absent-version case).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_27: `_rst_merge_first_index` diverges from bash `rst_merge_fh`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_rst_merge_first_index` only skips a leading `=`-underlined title when `lines[fh1] == "Changelog"` or that title is not in `_rst_release_section_indices`. Bash `auto-resolve-changelog.sh` `rst_merge_fh` skips any first section whose underline is all `=` (`ul ~ /^=+$/`), with no title check. A semver release block at the top with an `=` underline can be treated as the merge/insert anchor in Python while bash skips it — `auto_resolve`, `write_changelog_entry`, `drop_version_section`, and `extract_version_body` can diverge on the same file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_28: `_insert_rst_after` always appends trailing newline
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_insert_rst_after` always appends `"\n"` while `_write_md_entry`, `_drop_md_section`, and `_drop_rst_section` preserve whether the input ended with a newline. RST insert can add a newline to a previously newline-free file and change byte-level diffs on round-trip edit/drop vs Markdown/awk behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_3: Duplicated drop-commit walk/reset/rebase blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Near-identical drop-commit walk/reset/rebase blocks in `changelog.py` and `version_bump.py`. Bugfixes in drop mechanics (e.g. rebase abort, depth walk) must be duplicated; one module can drift from bash parity. Shared drop walker in `bump_worktree` with pluggable subject/file guards is suggested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: `bump_worktree` imported but not committed on branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Committed code imports `bump_worktree` but `python/bump_worktree.py` is not on the branch (untracked only / not in HEAD or branch diff). Clean checkout / CI: `make py-test` / pytest fails at import with `ModuleNotFoundError: bump_worktree` before Phase 2 tests run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: `classify_bump` fails hard on `git show` errors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `classify_bump` raises `ShipError` when `git show` fails for a modified public-surface file; bash `classify-bump.sh` continues with empty content. Example: `git show base:skills/foo/SKILL.md` fails while the path is listed in name-status — Python crashes classify; bash may still return PATCH/MINOR/MAJOR from other evidence or default PATCH. Match bash fail-soft (skip file) or document/test fail-loud policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


