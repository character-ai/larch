Normalized aggregator output from the supplied reviewer slots. Scout attestations with no actionable defect (dyn-port-fidelity FINDING_56–58, dyn-format-parser FINDING_65/67, dyn-file-mutation FINDING_72–73) are omitted. Merged blocks use the maximum severity across sources.

### FINDING_1: Missing version_bump unit/parity coverage (classify, drop, post)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-port-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan and acceptance require StubRunner and bash-parity tests for classify_bump (D/A/R/M, transparent walk, depth cap, CHANGELOG subject spoof), drop_bump_commit guard refusals and successful drop/reset/rebase paths, and check-bump-version.sh --mode post. Current CI covers only a subset (e.g. classify NONE at HEAD, drop noop parity), so classify/drop/post-verify regressions can ship green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Add classify/idempotency unit tests and test_parity_check_bump_post
  - From cursor-specialist-testing-output.txt: Add scripted StubRunner tests for each classify edge case per plan
  - From cursor-specialist-testing-output.txt: Add temp-repo fixture comparing verify_bump_commit_count to --mode post KV output
  - From cursor-specialist-testing-output.txt: Add StubRunner and git-fixture tests for guards reset at HEAD and rebase below HEAD
  - From cursor-specialist-testing-output.txt: Add fixture branches with skill/agent diffs and full KV parity vs classify-bump.sh
  - From cursor-specialist-edge-cases-output.txt: Add StubRunner tests and check-bump --mode post bash parity
  - From cursor-specialist-plan-fidelity-output.txt: Add temp-git fixture + subprocess --mode post comparing all KV fields to verify_bump_commit_count
  - From cursor-specialist-plan-fidelity-output.txt: Add StubRunner tests for D/A/R/M frontmatter flags transparent guards depth cap and NONE
  - From cursor-specialist-plan-fidelity-output.txt: StubRunner tests for guard-4 refusal reset at HEAD and rebase --onto below HEAD

### FINDING_2: Incomplete changelog test matrix and lib-changelog bash parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Only first_version_heading (or one of four lib-changelog.sh functions) has bash parity; duplicate count, extract body, write_changelog_entry, RST retitle/duplicate/extract, auto-resolve, and git-wrapper paths lack planned unit or parity coverage. MD/RST transform drift from awk/bash baselines may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add skipif parity per lib-changelog function and RST expected-text tests for retitle/extract/duplicate.
  - From cursor-specialist-correctness-output.txt: Add per-operation lib-changelog parity and bash output compare for auto-resolve
  - From cursor-specialist-testing-output.txt: Add bash wrapper parity tests for remaining lib-changelog functions
  - From cursor-specialist-testing-output.txt: Add pure unit tests for each missing operation and format
  - From cursor-specialist-plan-fidelity-output.txt: Expand fixtures for all operations both formats plus StubRunner commit_changelog/drop_changelog_commit
  - From cursor-specialist-plan-fidelity-output.txt: Add RST :2:/:3: fixture with subprocess .sh parity
  - From cursor-specialist-plan-fidelity-output.txt: Add bash wrapper parity for duplicate count extract body and write_changelog_entry

### FINDING_3: changelog imports version_bump (circular-import risk)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: changelog imports version_bump for DropResult and git drop helpers. Phase 7 wiring could create circular imports; the changelog text layer should not depend on bump orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared drop/worktree helpers and DropResult to a neutral module used by both.

### FINDING_4: Triplicated Markdown anchor-insertion logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Anchor-insertion logic is triplicated across write/commit paths in changelog.py. Anchor bugs (Unreleased vs semver intro) already bit bash; three Python copies can diverge on fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Single shared _insert_md_version_anchor helper for write_changelog_entry and commit_changelog.

### FINDING_5: apply_bump uses raising git.status() instead of ApplyResult
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: apply_bump uses git.status(), which raises ShipError on git failure instead of returning ApplyResult(applied=False, …). Transient or corrupt .git during bump can abort with an exception rather than APPLIED=false KV parity with bash fail().
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use non-raising status_porcelain and map failures to ApplyResult like bash fail().
  - From cursor-specialist-correctness-output.txt: Use status_porcelain without _ensure_success and map failures to ApplyResult(applied=False, error=...)
  - From cursor-specialist-edge-cases-output.txt: Use non-raising status_porcelain and return ApplyResult(applied=False error=...)

### FINDING_6: commit_changelog omits git commit --only path parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: commit_changelog commits without git commit --only, unlike commit-changelog.sh. Staged non-CHANGELOG paths can be bundled into the Update CHANGELOG commit if the porcelain guard has a gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Call git.commit(..., only=path, cwd=cwd)
  - From cursor-specialist-edge-cases-output.txt: Pass only=path to git.commit like bash
  - From cursor-specialist-plan-fidelity-output.txt: Use git.commit(runner, msg, only=path, cwd=cwd)

### FINDING_7: porcelain_tracked_only treats git status failure as clean worktree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: porcelain_tracked_only returns an empty list when git status fails, treating the worktree as clean; drop_* may run destructive reset/rebase when status is unknown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Refuse drop when status_porcelain returncode != 0

### FINDING_8: RST changelog helpers inconsistent (title parse, duplicate, extract/drop)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-format-parser-correctness-output.txt
- **Severity**: important
- **Concern**: RST read/write helpers disagree on what counts as a version title (`Version X.Y.Z (date)` from _write_rst_entry vs bare semver / Markdown `##` checks). duplicate_version_heading_count can miss real duplicates or count body lines; _extract_rst_body / first_version_heading / drop use mismatched matchers; _rst_title_indices treats subsection adornments as release boundaries, truncating extract/drop. Second writes and extract can silently misbehave on valid RST sections.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict duplicate detection to RST section title indices
  - From cursor-specialist-edge-cases-output.txt: Unify RST version title parsing across first_version_heading duplicate_version_heading_count extract drop and write; add RST_SAMPLE tests after insert
  - From dyn-format-parser-correctness-output.txt: Align RST duplicate detection with `_drop_rst_section` / `_extract_rst_body` title rules (e.g. `line.startswith(f"Version {version}")`, semver in brackets, bare semver title) and drop the Markdown `##` check from the RST branch; add a unit test on `RST_SAMPLE` in `python/test_changelog.py` that expects count ≥ 1 for `1.0.0`.
  - From dyn-format-parser-correctness-output.txt: Port bash `rst_second_title_index`’s `fh + 2` search start and/or restrict boundaries to same-level section titles (e.g. only `Version …` / semver release lines), matching how release sections are authored in `_write_rst_entry`; extend RST extract/drop tests to assert full release bodies including subsections.
  - From dyn-format-parser-correctness-output.txt: Share one helper for RST version title matching and use it in extract, drop, duplicate count, and `first_version_heading` (which at `python/changelog.py:127-133` also omits `Version …` titles).

### FINDING_9: _auto_resolve_rst body slice off-by-one vs bash
- **Reviewer(s)**: dyn-format-parser-correctness-output.txt
- **Severity**: important
- **Concern**: `_auto_resolve_rst` uses `end2 = second2 - 1`, excluding the last body line before the next RST section, while Markdown uses `end2 = second2` and bash auto-resolve-changelog.sh maps to exclusive `second2`. Tail union can drop trailing blank or last bullet lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-format-parser-correctness-output.txt: Set `end2 = second2 if second2 > 0 else len(ours)` (and the same for `end3`), mirror the Markdown resolver, and add an RST `auto_resolve` unit test with a blank line before the second section title to lock parity with `scripts/auto-resolve-changelog.sh`.

### FINDING_10: drop_bump_commit accepts empty parsed LARCH_BUMP_FILES (bash fail-closed)
- **Reviewer(s)**: dyn-port-fidelity-output.txt
- **Severity**: important
- **Concern**: When `LARCH_BUMP_FILES` is set but parses to an empty list, Python sets `effective_bump_files = ()` and `_guard4_allows` can allow changelog-only drops that bash drop-bump-commit.sh refuses before membership checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-port-fidelity-output.txt: After parsing `LARCH_BUMP_FILES`, if the variable is present in the environment and the parsed segment list is empty, return `DropResult(dropped=False, …)` immediately (mirror the bash WARN + `DROPPED=false` path). Do not enter `_guard4_allows` with an empty configured bump-file set.

### FINDING_11: apply_bump partial failure leaves dirty tree (backup, rollback, ignored git.add)
- **Reviewer(s)**: dyn-file-mutation-safety-output.txt
- **Severity**: important
- **Concern**: rollback_before_commit copies plugin.json but leaves `.bump-backup`, blocking later apply_bump clean-tree guard; backup_rewrite_stage / retry early returns skip rollback and can leave bumped plugin.json, stale backup, or staged index; git.add return code is ignored so fetch/retry can proceed with unstaged rewrite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-file-mutation-safety-output.txt: Mirror bash: `backup_path.replace(plugin_path)` (or `unlink` after a successful restore) inside `rollback_before_commit`, and `unlink`/`rm -f` the backup in `backup_rewrite_stage` error paths; only leave the backup file transiently between backup and successful commit.
  - From dyn-file-mutation-safety-output.txt: On any `backup_rewrite_stage` failure, restore from `backup_path` if it exists, `git.unstage` `PLUGIN_JSON_PATH`, delete `backup_path` and any `.tmp` sibling, then return the error; never return `stage_err` while the worktree still reflects a partial stage.
  - From dyn-file-mutation-safety-output.txt: Check `add_result.returncode` (and optionally `git diff --cached --quiet` on `PLUGIN_JSON_PATH`); on failure invoke the same rollback/cleanup path as other stage errors and return `ApplyResult(applied=False, error=...)`.

### FINDING_12: User-visible errors not redacted (plan / gh.py precedent)
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: ApplyResult.error, BumpClassification.reasoning, and related outbound strings are not passed through redact.py. Phase 7 logging could persist tokens or home-directory paths from unmerged-file lists or skill paths into run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Run outbound string fields through redact.redact before return; add redact-vector unit tests on those fields.
  - From cursor-specialist-plan-fidelity-output.txt: Apply redact.redact to outbound error strings or document exemption

### FINDING_13: Weak apply/commit parity fixtures (no success assertions)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Apply and commit parity tests only match failure booleans; fixtures lack origin remote and full git init, so APPLIED/COMMITTED may both be false while tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend fixtures with origin/main remote and assert true success plus SHA or file state

### FINDING_14: commit_changelog parity test shares mutated repo with bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: commit_changelog parity runs bash then Python on the same mutated repo; Python sees post-bash state, so idempotent second-run divergences would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use twin repos or compare file/commit outputs from identical starting fixtures.

### FINDING_15: sorted_changed_files UTF-8 sort vs bash LC_ALL=C
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: drop guard 4 uses UTF-8 key sort instead of LC_ALL=C byte sort; non-ASCII paths in LARCH_BUMP_FILES could fail guard vs bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Match bash LC_ALL=C sort ordering for changed-file multiset equality

### FINDING_16: auto_resolve does not git add merged file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: auto_resolve writes the worktree file but does not stage it; a Phase 7 driver that omits add leaves conflict markers in the index (bash contract unchanged).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document required git add after True or stage in helper

### FINDING_17: commit_changelog partial failure leaves dirty CHANGELOG (bash parity)
- **Reviewer(s)**: dyn-file-mutation-safety-output.txt
- **Severity**: latent
- **Concern**: After write_text, failed git.add/commit leaves modified CHANGELOG on disk with no restore—matches commit-changelog.sh but is a real partial-failure surface for Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-file-mutation-safety-output.txt: If stricter than bash is desired, snapshot `read_text` before `write_text` and restore on add/commit failure (and `git reset HEAD` the path); otherwise document that callers must treat `committed=False` after a heading-changing `replaces_version` as a dirty-tree state requiring manual fix or re-run from git.

### FINDING_18: Path arguments lack repo-root containment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: conflict_path, changelog path, and implement_tmpdir joins lack repo-root containment; `../` paths could write outside the repo or touch `.bump-version-armed` outside session tmp.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve paths and require is_relative_to(repo_root); reject .. components at Phase 7 boundary.

### FINDING_19: LARCH_BUMP_FILES from environment widens destructive drop
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Untrusted LARCH_BUMP_FILES in CI could permit reset --hard on commits that modified files beyond the default plugin.json guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pass bump_files from trusted driver only, or validate env entries against a fixed allowlist without .. segments.

### FINDING_20: verify_bump_commit_count git_error path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: rev-list failure / git_error normalization for verify_bump_commit_count lacks unit coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub rev-list failure and assert verified=false status=git_error
  - From cursor-specialist-plan-fidelity-output.txt: Stub rev-list failure/non-integer and assert status git_error verified false

### FINDING_21: Missing tests for APPLY_BUMP_MAX_RETRIES and git.add/commit argv
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Retry cap exhaustion and git.add/git.commit helper argv are untested; regressions could slip until integration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add StubRunner tests for retry cap and commit/add argv
  - From cursor-specialist-plan-fidelity-output.txt: Add StubRunner argv tests for add and commit with/without only

### FINDING_22: config SEMVER_RE and DEFAULT_BUMP_FILES unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: SEMVER_RE and DEFAULT_BUMP_FILES are unused; semver is duplicated inline and drop guard does not use DEFAULT_BUMP_FILES as documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Wire config.SEMVER_RE and DEFAULT_BUMP_FILES into validation and _guard4_allows.

### FINDING_23: Duplicate unused _VERSION_HEADING_MD_EXACT regex
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Identical duplicate regex _VERSION_HEADING_MD_EXACT is never used—dead code from incomplete refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove unused duplicate or use it consistently.

### FINDING_24: rebase_onto merges full os.environ into git subprocess
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Tainted GIT_DIR/GIT_WORK_TREE in the environment could make rebase/drop helpers operate on the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use minimal sanitized env for git helpers or unset GIT_DIR/GIT_WORK_TREE overrides.

### OOS_1: [OUT_OF_SCOPE] README H1 still says Phase 1 only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: README title still says Phase 1 while body documents Phase 2 modules; contributors may assume version_bump/changelog are out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update heading to mention Phase 2 modules documented in the body.
  - From cursor-specialist-edge-cases-output.txt: Update heading to reflect Phase 2 scope
  - From cursor-specialist-plan-fidelity-output.txt: Optional rename heading to mention Phase 2

### OOS_2: [OUT_OF_SCOPE] StubRunner duplicated across test files
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: StubRunner is duplicated across three test files; argv expectation changes multiply maintenance (pre-existing Phase 1 pattern).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider shared conftest helper in a follow-up (pre-existing Phase 1 pattern).

### OOS_3: [OUT_OF_SCOPE] Defer redact.py to Phase 7 integration
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No redact.py usage yet for future diagnostics; Phase 7 may emit paths/tokens without redaction if not wired at integration time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Wire redact when adding user-visible error output in Phase 7.
  - From cursor-specialist-edge-cases-output.txt: Route outbound error strings through redact at Phase 7 integration

### OOS_4: [OUT_OF_SCOPE] proc.run forwards parent environment by default
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: proc.run forwards parent environment when env is None; same GIT_* hijack class for Phase 1 callers once wired to production (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Consider sanitized default env at proc layer (pre-existing).

### OOS_5: [OUT_OF_SCOPE] Bash auto-resolve lacks path root containment (parity baseline)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: scripts/auto-resolve-changelog.sh writes conflict_path without root containment; same traversal class as Python if conflict_path is attacker-controlled—harden together at Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address together when hardening Phase 7 path validation.

### OOS_6: [OUT_OF_SCOPE] lib-changelog parity skips on non-gawk awk (macOS)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The only lib-changelog parity test skips on macOS awk without match() capture; local developers may skip parity silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document gawk requirement or avoid match-capture in parity script
  - From cursor-specialist-plan-fidelity-output.txt: Prefer gawk in CI or fixture-only parity without awk capture

### OOS_7: [OUT_OF_SCOPE] Missing RST auto_resolve bash parity test (would not catch FINDING_9)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-format-parser-correctness-output.txt
- **Severity**: latent
- **Concern**: CI has Markdown auto_resolve bash parity only; RST adornment merge bugs and the `_auto_resolve_rst` off-by-one would not be caught against auto-resolve-changelog.sh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add RST :2:/:3: fixture compared to auto-resolve-changelog.sh output
  - From dyn-format-parser-correctness-output.txt: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] _extract_frontmatter delimiter parity (strip vs ^---$)
- **Reviewer(s)**: dyn-port-fidelity-output.txt
- **Severity**: nit
- **Concern**: Python uses `line.strip() == "---"`; bash classify-bump.sh requires `^---$` at column 0—unlikely drift on indented delimiter lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-port-fidelity-output.txt: Address the concern above.
