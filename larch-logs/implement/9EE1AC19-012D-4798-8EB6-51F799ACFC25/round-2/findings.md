Structured aggregator output (plain text; merged duplicates; severity = max across sources).

### FINDING_1: Missing classify idempotency unit tests (transparent guards, depth cap, spoof)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-required unit tests for `_idempotency_transparent` / `_idempotency_ref` are absent: path-guard refusal, `IDEMPOTENCY_DEPTH=3`, bump-at-idem-ref `NONE`, and CHANGELOG subject-only spoof → MINOR. Regressions in transparent walk, depth cap, or spoof handling can ship with only HEAD-bump `NONE` parity covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add StubRunner tests for path-guard refusal, IDEMPOTENCY_DEPTH=3, bump-at-idem-ref NONE, and spoof→MINOR.
  - From cursor-specialist-testing-output.txt: Add StubRunner tests for _idempotency_transparent/_idempotency_ref per plan edge cases.
  - From cursor-specialist-edge-cases-output.txt: Add StubRunner/tmp_path git tests for spoof paths, depth=3 cap, and skills change under fake CHANGELOG subject.
  - From cursor-specialist-plan-fidelity-output.txt: Add StubRunner/tmp_path tests for IDEMPOTENCY_DEPTH, path guards, and spoof scenario.

### FINDING_2: Missing drop-helper tests (rebase --onto below HEAD; allow_changelog_only)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Drop helpers only exercise HEAD~0 reset paths. `rebase --onto` when the bump/changelog commit is below HEAD, and `allow_changelog_only` guard behavior, are untested; wrong drop strategy or guard acceptance could regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add fixture with bump/changelog at HEAD~1 and assert rebase_onto argv and history.
  - From cursor-specialist-plan-fidelity-output.txt: Two-commit history test for rebase_onto path; allow_changelog_only guard matrix.

### FINDING_3: Duplicated Markdown anchor-insertion logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_write_md_entry` and `_insert_md_version_anchor` duplicate anchor-insertion logic in `python/changelog.py`. Fixing Unreleased/SemVer anchor behavior in one path but not the other can make write vs commit behavior diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared _insert_md_at_anchor helper used by both code paths.

### FINDING_4: `sorted_changed_files` sort order vs bash `LC_ALL=C`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `sorted_changed_files` in `python/bump_worktree.py` sorts by UTF-8 codepoints, while `drop-bump-commit.sh` guard 4 uses `LC_ALL=C` byte order. Non-ASCII paths in a bump commit can make Python and bash disagree on the sorted multiset, so guard-4 exact compare fails and drop/refuse behavior diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use locale C sort or restrict/document ASCII-only bump paths.
  - From cursor-specialist-correctness-output.txt: Sort changed file names with C-locale byte order to match bash LC_ALL=C sort.
  - From cursor-specialist-edge-cases-output.txt: Match LC_ALL=C byte sort or restrict and test ASCII-only bump file sets.

### FINDING_5: Duplicate `_redact_outbound` in bump and changelog modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_redact_outbound` is duplicated in `python/version_bump.py` and `python/changelog.py`. Future redaction or trailing-newline behavior could diverge between bump and changelog error paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize in redact.py and import once.

### FINDING_6: `python/README.md` lags Phase 2 / omits `bump_worktree`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: README still titles Phase 1 only and does not list `bump_worktree.py` (once committed). Contributors may miss Phase 2 modules and the shared drop helper during onboarding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update README title and module list after bump_worktree is committed.
  - From cursor-specialist-correctness-output.txt: Add bump_worktree.py to the layout list after committing it.
  - From cursor-specialist-testing-output.txt: Update README header and module bullet list.
  - From cursor-specialist-edge-cases-output.txt: Update README phase label and module list.
  - From cursor-specialist-plan-fidelity-output.txt: Update heading to mention Phase 2 modules.

### FINDING_7: Duplicate ProcRunner test adapters
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/test_changelog.py` and `python/test_version_bump.py` each define similar ProcRunner test adapters; signature changes require duplicate updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional shared conftest ProcRunner fixture.

### FINDING_8: [OUT_OF_SCOPE] Very large dual-format `changelog.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The changelog module is very large for Phase 2 port scope; acceptable now but harder to maintain long term.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider format-specific submodules in a later refactor phase.

### FINDING_9: [OUT_OF_SCOPE] `commit_changelog` Markdown-only by design
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `commit_changelog` is Markdown-only, matching bash; RST-only repos cannot use it until extended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend only if product needs RST commit parity beyond lib transforms.

### FINDING_10: `bump_worktree.py` imported but not committed on branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-merge-dedup-output.txt
- **Severity**: important
- **Concern**: `version_bump.py` and `changelog.py` import `bump_worktree`, but `python/bump_worktree.py` is untracked / absent from `HEAD`. Clean clone or CI (`make py-test`) fails with `ModuleNotFoundError` before bump/changelog logic runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Commit bump_worktree.py or inline DropResult and helpers and remove the import.
  - From cursor-specialist-security-output.txt: Commit python/bump_worktree.py or revert the extraction into committed modules.
  - From cursor-specialist-edge-cases-output.txt: Add commit bump_worktree.py; document in python/README.md; verify make py-test on clean tree.
  - From cursor-specialist-plan-fidelity-output.txt: Commit bump_worktree.py and README entry, or revert refactor to keep DropResult/helpers in version_bump.py.
  - From dyn-merge-dedup-output.txt: Add and commit `python/bump_worktree.py` (or move those helpers back into `version_bump.py` / `changelog.py` and drop the import) so the branch is self-contained.

### FINDING_11: `_write_md_entry` missing blank line after version retitle vs `lib-changelog.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On `replaces_version` retitle, bash `entry_from_version_match` emits a blank line before the next `##` heading; Python `_write_md_entry` does not, so output can differ byte-for-byte from `lib-changelog.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track entry_from_version_match and out.append("") when skipping ends at the next ## [ heading.

### FINDING_12: No bash parity test for `write_changelog_entry`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No skipif parity test comparing Python `write_changelog_entry` to `lib-changelog.sh` (plan acceptance). Insert/retitle/duplicate drift (e.g. blank-line bug) would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add skipif parity test sourcing lib-changelog.sh write_changelog_entry vs Python write_changelog_entry.
  - From cursor-specialist-plan-fidelity-output.txt: Add skipif parity test sourcing lib-changelog.sh write_changelog_entry.

### FINDING_13: `test_parity_auto_resolve_markdown_fixture` does not subprocess bash script
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-merge-dedup-output.txt
- **Severity**: important
- **Concern**: Despite skipif/plan acceptance, the auto-resolve parity test only exercises Python via `StubRunner`; it does not run `scripts/auto-resolve-changelog.sh` or compare merged output. Python `auto_resolve` can diverge while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run scripts/auto-resolve-changelog.sh on a fixture repo/conflict and assert merged file matches Python; add RST parity using scripts/test-auto-resolve-changelog.sh vectors.

### FINDING_14: Thin `classify-bump.sh` parity (idempotency / D/A/R/M / spoof)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Classify parity is limited to NONE-at-HEAD; bash comparison for idempotency, D/A/R/M, and spoof paths required by plan is missing. `classify_bump` could mis-rank vs bash while only NONE parity passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add parity fixtures from scripts/test-classify-bump.sh or hand-built repos comparing KV output to classify-bump.sh.

### FINDING_15: Thin `drop-bump-commit.sh` parity (guards, rebase-onto, changelog-only)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Drop-bump parity covers noop only; Guard4, `LARCH_BUMP_FILES`, `allow_changelog_only`, and rebase-onto scenarios from `scripts/test-drop-bump-commit.sh` are not compared to bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port harness scenarios as twin-repo pytest parity tests subprocessing drop-bump-commit.sh.

### FINDING_16: Thin bash parity for changelog drop / lib-changelog write-drop paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Beyond noop/extract/first/duplicate, `drop_changelog_commit` rebase path and `write_changelog_entry` / `drop_version_section` lack bash parity wrappers; drift from `lib-changelog.sh` / `commit-changelog.sh` may go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add bash wrappers for write_changelog_entry drop_version_section and successful drop_changelog_commit.

### FINDING_17: Latent unit-test gaps for MD/RST editor paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: MD retitle/duplicate and several RST extract/retitle paths lack unit tests; subtle editor bugs could ship before Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add MD replaces_version and ChangelogError code-4 tests; RST extract present/blank and retitle fixtures.

### FINDING_18: `bump_branch_guard` omits master non-forked stall case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests omit master branch stall for non-forked runs; Python might not raise `Stalled` while bash `run_bump_phase` would stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend matrix with master/non-forked stall and forked proceed.

### FINDING_19: `first_version_heading` parity skips on BSD awk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: lib-changelog parity test skips on BSD awk; macOS developers may not see parity failures locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Tighten skipif to require gawk or avoid capture-dependent awk in wrapper.

### FINDING_20: Git subprocess env: `GIT_DIR` / `GIT_WORK_TREE` only sanitized for `rebase_onto`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Sanitization applies to `rebase_onto` while reset/fetch/commit/add inherit full `os.environ`. Poisoned `GIT_DIR` could make porcelain clean checks and `reset --hard` target a different repo within one drop/apply flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply _git_subprocess_env() (or equivalent) to all git subprocess invocations in Phase 2 modules.

### FINDING_21: `auto_resolve` writes conflict path without repo-root validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Merged conflict output is written via `conflict_path` without resolving or bounding under repo cwd; paths with `..` could write outside the repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve paths and reject any target not strictly under the repo root before write_text/mkdir.
  - From cursor-specialist-edge-cases-output.txt: Resolve paths and reject targets not under cwd before write_text.

### FINDING_22: `commit_changelog` stages/commits unvalidated path parameter
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Caller-supplied relative paths (e.g. `../`) joined to cwd can stage/commit files outside the intended changelog location without the same root-prefix check as `auto_resolve`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Same root-prefix check as auto_resolve; default path only after validation.

### FINDING_23: `check_bump_version_pre` touches `.bump-version-armed` without tmpdir boundary check
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A malicious `implement_tmpdir` could place the armed sentinel outside the expected session tmp hierarchy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve implement_tmpdir and require it under the expected IMPLEMENT_TMPDIR root before touch.

### FINDING_24: [OUT_OF_SCOPE] `proc.run` inherits full parent environment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing Phase 1 seam: when `env` is None, Phase 2 git wrappers inherit unsanitized parent env like before.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Consider centralized env sanitization at the Runner/proc layer in a future phase.

### FINDING_25: [OUT_OF_SCOPE] Bash `auto-resolve-changelog.sh` also uses unvalidated conflict path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Bash baseline has the same path-traversal scenario as the Python port; hardening should be joint at Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address jointly when hardening Phase 7 conflict resolution.

### FINDING_26: `classify_bump` treats failed `git show` as empty frontmatter
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Transient or real `git show base:path` failure for an `M` path can be treated as empty frontmatter, missing MAJOR/MINOR signals and under-bumping to PATCH instead of failing loud.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Raise ShipError or record skip reason when show_file fails for an M path in scope.

### FINDING_27: Missing classify unit tests for A/R/M name-status paths
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Only delete→MAJOR classify unit test exists; add/rename/modify classification paths are untested in pytest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add fixtures per name-status letter asserting bump_type and reasons.

### FINDING_28: Missing plan acceptance tests for RST extract / retitle / duplicate (code 4)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No unit tests for RST `extract_version_body`, write retitle, or duplicate `ChangelogError` code 4 despite acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add unit tests for extract_version_body RST, replaces_version retitle, ChangelogError code 4.

### FINDING_29: Classify-bump parity asserts only subset of KV fields
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Parity test compares only two KV fields; drift in `CURRENT_VERSION` / reasoning would not be detected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Expand parity assertions or add scenario matrix.

### FINDING_30: [OUT_OF_SCOPE] `bump_worktree` not in plan module list
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Extra shared module may be undiscoverable vs plan module list until documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document in README after commit or merge into version_bump.py.

### FINDING_31: [OUT_OF_SCOPE] `drop_changelog_commit` rebase path untested
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Rebase drop regression for changelog commit below HEAD is possible without integration coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add integration test with changelog commit below HEAD.

### FINDING_32: Changelog heading dates use UTC vs bash local `date +%Y-%m-%d`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python uses `datetime.now(tz=UTC).date()` for heading dates while bash uses local timezone. When local calendar day ≠ UTC day, `## [X.Y.Z] - YYYY-MM-DD` / RST version lines differ from shell scripts byte-for-byte.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Match bash by using local date (e.g. `datetime.now().astimezone().date().isoformat()`), or inject a shared `today` callable in tests and document that CI assumes UTC if you intentionally standardize on UTC everywhere.

### FINDING_33: Extensionless `auto_resolve` format detection inspects only `:2:` side
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python picks MD vs RST from `detect_format(ours)` only; bash considers both stages and refuses when `##` presence or first headings disagree. Python may merge on a different code path than `auto-resolve-changelog.sh` lines 182–195.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Port the extensionless branch from `auto-resolve-changelog.sh` (lines 182–195): consider both `:2:` and `:3:` for `md_has_any_l2_heading` / first-heading equality before choosing the merge mode.

### FINDING_34: RST `_insert_rst_after` splices inside Unreleased section
- **Reviewer(s)**: dyn-rst-parsing-output.txt
- **Severity**: important
- **Concern**: `_insert_rst_after` always inserts at `anchor + 2`. With `_rst_merge_first_index` on `Unreleased`, new `Version 1.1.0` lands between Unreleased header and its body, unlike MD behavior that inserts after the full Unreleased block. `test_rst_write_and_drop` only checks presence, not structure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rst-parsing-output.txt: Compute the insert index from the anchor section’s end (scan to the next `_rst_release_section_indices` entry, or the next `_rst_title_indices` title after `anchor + 2`), and splice there—before the first release section when the anchor is `Unreleased`/intro, and before the anchor title when inserting a newer release above an existing one. Add a unit test on `RST_SAMPLE` that `Changed` / `- Pending` remain directly under `Unreleased` and `Version 1.1.0` sits above `Version 1.0.0`.

### FINDING_35: RST writer uses `=` underlines; merge anchor misclassifies releases as doc title
- **Reviewer(s)**: dyn-rst-parsing-output.txt
- **Severity**: important
- **Concern**: `_write_rst_entry` uses `"=" * len(title)` while `_rst_merge_first_index` skips a leading all-`=` section as document title. A Python-written first release with no doc-title block can be mis-anchored on the next operation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rst-parsing-output.txt: Use the same adornment as existing release sections (e.g. `-` in `RST_SAMPLE`) for new entries, and/or restrict doc-title skip to a known document title (e.g. title line `Changelog` or only when `indices[0]` is not a `_rst_release_section_indices` hit); add a fixture with no doc-title block and two `Version …` sections to lock anchor behavior.

### FINDING_36: [OUT_OF_SCOPE] `commit_changelog` leaves modified CHANGELOG on failed commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Same as bash `commit-changelog.sh`; operator must reset manually on commit failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional: git checkout -- CHANGELOG.md on commit failure if parity allows.

### FINDING_37: [OUT_OF_SCOPE] `apply_bump` may commit unrelated staged files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Matches pre-existing bash `apply-bump.sh`; caller must keep index clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document or use git commit --only for plugin.json only.

### FINDING_38: [OUT_OF_SCOPE] `apply_bump` dirty-tree ERROR text shorter than bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: No phantom-file hint in ERROR text; `APPLIED=false` behavior matches bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: (No separate fix proposed beyond noting parity gap.)

---

**Subsumed (not emitted as separate findings):** Input items that only attest bash alignment or non-divergence (e.g. dyn-bash-parity FINDING_51–52, dyn-rst-parsing FINDING_57, dyn-merge-dedup FINDING_60–62, dyn-bash-parity FINDING_53 overlapping FINDING_1/14, dyn-rst-parsing FINDING_58 overlapping FINDING_34) were merged into the actionable findings above or dropped as non-actionable confirmations. `dyn-merge-dedup-output.txt` FINDING_63 overlaps FINDING_13 and was merged there.

**Count:** 38 structured blocks (30 in-scope `### FINDING_*`, 8 `[OUT_OF_SCOPE]`). No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).
