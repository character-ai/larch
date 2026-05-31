Structured aggregator output from the supplied reviewer slots. Positive parity attestations (input FINDING_36, 37, 38, 41, 42, 43, 46) are omitted as non-actionable. Input FINDING_27 and FINDING_33 are merged. Input FINDING_12 and FINDING_22 stay separate (in-scope vs `[OUT_OF_SCOPE]`).

### FINDING_1: Parallel Markdown retitle/replace paths in changelog
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Parallel Markdown retitle/replace implementations in `_write_md_entry` and `_retitle_version_heading_md` used only by `commit_changelog`. A commit-time retitle fix (e.g. when the target version heading already exists) can diverge from `write_changelog_entry` behavior; parity tests may still pass if they only exercise one path. Extract a shared retitle/replace helper or route `commit_changelog` retitle through the same function as `write_changelog_entry`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Duplicate `_redact_outbound` in Phase 2 modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Duplicate `_redact_outbound` in both Phase 2 modules despite plan routing diagnostics through `redact.py`. Newline-preservation or redaction rule changes must be edited twice; one copy can drift. Add `redact_outbound` (or equivalent) to `redact.py` and import from `version_bump` and `changelog`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Hardcoded `origin/main` plugin.json path in `apply_bump`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply_bump` hardcodes `origin/main` plugin.json path instead of `config.PLUGIN_JSON_PATH`. If `PLUGIN_JSON_PATH` changes, race/regression detection still reads the old hardcoded path and mis-handles collisions. Use `f"origin/main:{config.PLUGIN_JSON_PATH}"` and align test fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Duplicated `ProcRunner` / `StubRunner` test doubles
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicated `ProcRunner` and `StubRunner` test doubles across Phase 2 test files. Future Runner API tweaks require multi-file edits; subtle `StubRunner` differences (porcelain alias) are easy to miss. Introduce a shared test helper module imported by both test files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Large nested `apply_bump` routine
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply_bump` nests multiple inner functions in one large routine. Harder to unit-test rollback and retry branches in isolation without standing up full integration fixtures. Hoist backup, rollback, and retry-loop steps to module-level private helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: `sorted_changed_files` UTF-8 vs bash `LC_ALL=C` sort
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `sorted_changed_files` uses UTF-8 byte sort; bash drop scripts use `LC_ALL=C`. Custom `LARCH_BUMP_FILES` with non-ASCII path segments could fail guard-4 equality vs bash (drop refused or allowed incorrectly). Match `LC_ALL=C` sorting or restrict/document ASCII-only bump file paths with a fixture test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Monolithic `changelog.py` module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Single large module combines RST/MD text ops and git orchestration. Phase 7 wiring increases merge conflict risk and review burden when touching one concern affects unrelated code. Consider splitting pure text transforms from git wrappers if more callers arrive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Phase 1 `test_redact` imports Phase 2 `version_bump`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test_redact` imports `version_bump` for `apply_bump` redaction coverage. Phase 1 redact tests depend on Phase 2 module import graph. Move bump error redaction test to `test_version_bump.py` or a small shared contract module.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] No repo-wide pytest conftest for Runner doubles
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: No shared pytest conftest/helpers for Runner doubles repo-wide. Other phases may repeat the same duplication pattern. Add conftest/helpers when multiple modules need identical Runner fakes (pre-existing gap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: RST `write_changelog_entry` wrong path when `replaces_version != version`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_write_rst_entry` skips duplicate guard when `replaces_version != version` and always insert-at-anchor plus drop `replaces_version` only. Changelog already has Version 1.2.0; `write_changelog_entry(version=1.2.0, replaces_version=1.1.0, fmt=RST)` with no 1.1.0 section inserts a second 1.2.0 block instead of updating the existing section (Markdown/lib-changelog replace in place). Mirror `_write_md_entry`: replace existing RST release section for `version` when present; anchor-insert only when absent; raise code 4 on multiple version headings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: `classify_bump` treats failed `git diff` as empty PATCH
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `classify_bump` treats failed `git diff --name-status` as empty diff and defaults to PATCH. Transient git error during classify yields PATCH and wrong `new_version` despite MAJOR/MINOR skill/agent changes in BASE..HEAD. Fail closed on diff failure (`ShipError`) or surface error to caller; consider aligning bash later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: `commit_changelog` Markdown-only (document limitation)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `commit_changelog` is Markdown-only while plan mentions full RST for changelog operations. RST CHANGELOG commit path cannot use `commit_changelog` until extended (no current bash counterpart). Document limitation or add RST commit wrapper when Phase 7 needs it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: Drop-changelog success parity does not assert commit or `DROPPED`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_parity_drop_changelog_success` drops via bash before copytree so Python runs on post-drop repo; commit success not asserted. Bash `DROPPED=true` while Python `DROPPED=false` on divergent repos or both false if commit failed — success drop parity never enforced. Use twin repos; assert commit `COMMITTED=true`; compare bash vs Python drop on identical pre-drop state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Use twin repos; assert commit COMMITTED=true; compare bash vs Python drop on identical pre-drop state

### FINDING_14: No bash-parity test for successful `drop-bump-commit.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No bash-parity test for successful `drop-bump-commit.sh` at HEAD with plugin.json-only diff. Phase 7 could diverge on default drop path while CI stays green via noop/allow-changelog-only parity. Add twin-repo parity test seeding Bump version commit and comparing DROPPED plus plugin.json.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add twin-repo parity test seeding Bump version commit and comparing DROPPED plus plugin.json

### FINDING_15: No tests that `auto_resolve` returns False on mismatch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No tests that `auto_resolve` returns False on heading/tail mismatch. Conflicting changelogs with different first sections could be auto-merged incorrectly without test failure. Add StubRunner `:2:`/`:3:` fixtures asserting False and no file write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add StubRunner :2:/:3: fixtures asserting False and no file write

### FINDING_16: `test_parity_commit_changelog_idempotent` has no git repository
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test_parity_commit_changelog_idempotent` has no git repository. Both sides return `COMMITTED=false` and parity passes without exercising commit path. Add git init/commit setup or remove in favor of twin-repo commit parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add git init/commit setup or remove in favor of twin-repo commit parity

### FINDING_17: Classify-bump parity lacks live MAJOR/MINOR diff scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `classify-bump.sh` parity lacks live MAJOR/MINOR diff scenarios beyond idempotency harness. Classifier logic for real skill diffs could drift from bash with only StubRunner coverage. Add minimal temp-repo subprocess parity for delete→MAJOR and add→MINOR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal temp-repo subprocess parity for delete→MAJOR and add→MINOR

### FINDING_18: Missing tests for token-set cancellation and `agents/**` classify scope
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Missing tests for token-set cancellation and `agents/**` classify scope. Reordered argument-hint wording or agent file changes might mis-classify with no regression signal. Add StubRunner/git fixtures for unchanged flag token sets and `agents/*.md` D/A/R/M.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add StubRunner/git fixtures for unchanged flag token sets and agents/*.md D/A/R/M

### FINDING_19: No unit test for `drop_changelog_commit` below HEAD
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No unit test for `drop_changelog_commit` when target commit is below HEAD. Rebase-onto drop path for changelog commits untested though bump drop has coverage. Mirror `test_drop_rebase_onto_when_bump_below_head` for changelog drop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mirror test_drop_rebase_onto_when_bump_below_head for changelog drop

### FINDING_20: `bump_worktree` helpers lack direct unit tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `bump_worktree` helpers lack direct unit tests. `find_commit_depth` or rebase-abort error handling regressions only surface via integration drops. Add focused StubRunner tests for depth search and `drop_replay_commit` failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add focused StubRunner tests for depth search and drop_replay_commit failures

### FINDING_21: CI workflow does not document git/bash/gawk for parity tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python-tests` job does not document git/bash/gawk dependency for parity tests. Future CI image without bash/git could skip most parity tests silently. Add comment or sanity which step in workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add comment or sanity which step in workflow

### FINDING_22: [OUT_OF_SCOPE] `commit_changelog` Markdown-only vs Phase 7 RST
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `commit_changelog` Markdown-only matches bash, not Phase 7 RST commit needs. Out of scope unless RST CHANGELOG commits required before Phase 7. Defer or extend when RST commit path is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Defer or extend when RST commit path is required

### FINDING_23: [OUT_OF_SCOPE] Phase 2 config constants not in `documented_constants_exist`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Phase 2 config constants not in `documented_constants_exist` test. Pre-existing test pattern not amplified by this branch. Optionally extend `test_config` when touching config again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optionally extend test_config when touching config again

### FINDING_24: `check_bump_version_pre` arms sentinel outside session root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `check_bump_version_pre` touches `.bump-version-armed` in any existing `implement_tmpdir` without session-root containment. Phase 7 caller passes attacker-influenced tmpdir; sentinel arms Stop-hook resolution outside the real session directory. Validate `implement_tmpdir` under session root before touch (match ship-pr plan-file containment).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate implement_tmpdir under session root before touch (match ship-pr plan-file containment)

### FINDING_25: `write_changelog_entry` does not validate semver on version strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `write_changelog_entry` does not validate semver on version/categories before structural insert. Untrusted version string with embedded newlines injects extra `##` headings into CHANGELOG. Apply `SEMVER_RE` at public text-transform entry points or enforce trusted input only at driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply SEMVER_RE at public text-transform entry points or enforce trusted input only at driver

### FINDING_26: `major_reasons` / `minor_reasons` omit redact on return
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `major_reasons`/`minor_reasons` omit redact while reasoning is redacted. Caller logs tuple fields to CI/journal and leaks absolute paths from git porcelain. Redact reason strings before return or document reasoning-only as log-safe surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact reason strings before return or document reasoning-only as log-safe surface

### FINDING_27: `bump_worktree.py` untracked — import failure on clean checkout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `bump_worktree.py` is imported and documented but not committed at HEAD (untracked). Fresh checkout of this branch raises `ModuleNotFoundError` on import; `py-test` and stdlib import smoke test fail before any Phase 2 logic runs. Acceptance criterion for passing Python Tests is not met. Add and commit `python/bump_worktree.py` (or merge helpers into planned modules and remove the import); verify with git archive or clean-clone import smoke test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add and commit python/bump_worktree.py; verify with git archive or clean-clone import smoke test.
  - From cursor-specialist-plan-fidelity-output.txt: Add and commit python/bump_worktree.py, or merge its helpers into the planned modules and remove the import.

### FINDING_28: Success paths use `git.rev_parse` raising `ShipError` after commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Success paths call `git.rev_parse` which raises `ShipError` instead of returning result records. After a successful commit, rev-parse failure escapes as `ShipError` while the commit already exists, breaking the ApplyResult/DropResult/CommitResult contract for Phase 7. Use `try_rev_parse` on success paths and return result records with empty sha plus diagnostic, or catch `ShipError` at module boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use try_rev_parse on success paths and return result records with empty sha plus diagnostic, or catch ShipError at module boundary.

### FINDING_29: `commit_changelog` writes disk before commit with no rollback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `commit_changelog` writes CHANGELOG to disk before add/commit with no rollback on failure. `git add` or commit failure leaves a modified unstaged CHANGELOG; re-run hits dirty-tree guards or may commit partial state. Write via temp file and replace only after commit succeeds, or restore from snapshot on add/commit failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Write via temp file and replace only after commit succeeds, or restore from snapshot on add/commit failure.

### FINDING_30: `drop_replay_commit` leaves repo mid-rebase when abort fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `drop_replay_commit` returns an error string when rebase `--abort` fails after a failed rebase `--onto`. Repo can remain mid-rebase; subsequent rebase/bump/drop operations fail unpredictably with no recovery signal. Surface distinct stuck-rebase status for Phase 7 driver; document recovery in error message; add abort-failure unit test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Surface distinct stuck-rebase status for Phase 7 driver; document recovery in error message; add abort-failure unit test.

### FINDING_31: Some drop error strings skip `_redact_outbound`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Some drop error strings skip `_redact_outbound` while adjacent paths redact. Inconsistent with plan convention that all outbound diagnostics go through `redact.py`. Route all user-visible drop error strings through `_redact_outbound`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Route all user-visible drop error strings through _redact_outbound.

### FINDING_32: [OUT_OF_SCOPE] Bash classify also defaults failed diff to PATCH
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bash and Python both treat failed `git diff --name-status` as empty diff defaulting to PATCH. Git errors silently produce PATCH instead of failing loud; pre-existing bash behavior not introduced by this branch. Fix in a future phase if fail-loud classification is desired; not a regression from this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fix in a future phase if fail-loud classification is desired; not a regression from this diff.

### FINDING_33: `_insert_md_at_anchor` blank-line order vs bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: In `_insert_md_at_anchor`, when closing an `## [Unreleased]` block at the next `## [` heading, Python appends the new entry block and then a blank line before the following heading (`out.extend(block)` then `out.append("")`). `scripts/lib-changelog.sh` `write_changelog_entry` does the opposite on that path: it prints a blank line first, then the entry lines (`print ""` then `for … print e[i]`), then the next heading. That changes blank-line spacing between Unreleased content and the inserted version section relative to bash; `test_parity_write_changelog_entry` is the right guard, but the control-flow order is visibly inverted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: In the `in_unreleased and line.startswith("## [")` branch, match bash by emitting `out.append("")` before `out.extend(block)` (keep the trailing `out.append(line)` for the next heading unchanged). The `END` path at `389-392` already uses blank-then-block and should stay as-is.

### FINDING_34: RST `_write_rst_entry` false duplicate guard on single existing version
- **Reviewer(s)**: dyn-rst-section-parser-output.txt
- **Severity**: important
- **Concern**: `_write_rst_entry` rejects whenever `duplicate_version_heading_count(...) > 0` and `replaces_version` is empty or equals `version`, but `scripts/lib-changelog.sh` `write_changelog_entry` only exits 4 when the scan sees the target heading a **second** time (`match_count > 1` at `lib-changelog.sh:106-108`), and `_write_md_entry` replaces a single existing `## [version]` block on first match (`changelog.py:420-440`). A changelog that already has one `Version X.Y.Z` section therefore cannot be refreshed via `write_changelog_entry(..., version="X.Y.Z", ...)` on RST, even though Markdown/bash allow it; Phase 7 rebump paths that rely on re-writing an existing release would hit a false `ChangelogError(code=4)`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rst-section-parser-output.txt: Align RST with Markdown/bash: drop the upfront `> 0` guard and either mirror `_write_md_entry`'s walk-and-replace/skip logic for matching `Version {version}` titles, or only raise when `duplicate_version_heading_count(...) > 1` (and when `replaces_version` names a different version, keep the existing drop+insert path).

### FINDING_35: `_rst_section_end_index` splits release body on subsection fallback
- **Reviewer(s)**: dyn-rst-section-parser-output.txt
- **Severity**: important
- **Concern**: `_rst_section_end_index` falls through to `_rst_title_indices` when there is no **next release** section after `anchor`. If `_rst_merge_first_index` returns a release title (typical when the file has a document title plus `Version …` but no `Unreleased` section), the next structural title is often a subsection adornment (e.g. `Fixed` / `Changed` under that release). `insert_at` then lands **inside** the current release block, so `_insert_rst_after` splits the version heading/underline from its body. `_extract_rst_body` / `_drop_rst_section` use release-only boundaries and do not have this split; only insert uses `_rst_section_end_index`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rst-section-parser-output.txt: When `anchor` is in `_rst_release_section_indices(lines)`, set the section end to the next release index or `len(lines)` only—do not use the generic `_rst_title_indices` fallback for that anchor. Reserve the title-index fallback for non-release anchors (e.g. `Unreleased`), where skipping non-release subsections before the first release is intentional (`test_rst_insert_after_unreleased_keeps_pending_under_unreleased`).

### FINDING_36: [OUT_OF_SCOPE] No RST parity test for `auto_resolve` with subsection under Unreleased
- **Reviewer(s)**: dyn-rst-section-parser-output.txt
- **Severity**: nit
- **Concern**: `_auto_resolve_rst` uses `_rst_second_title_index`, so RST changelogs with a subsection directly under `Unreleased` (as in `RST_SAMPLE` lines 62–65) merge only the lines before that subsection; this mirrors `scripts/auto-resolve-changelog.sh:249-266`, but there is no parity test with that subsection shape—only flat `Unreleased` → bullets → `Version` fixtures (`python/test_changelog.py:269-314`).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_37: [OUT_OF_SCOPE] RST lacks Markdown-style Semantic Versioning intro anchor
- **Reviewer(s)**: dyn-rst-section-parser-output.txt
- **Severity**: nit
- **Concern**: RST has no Markdown-style “Semantic Versioning” intro anchor fallback in `_write_rst_entry` (only `_rst_merge_first_index`); that is a broader Phase 2 policy gap, not introduced by the section-end helper alone.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_38: `test_git.py` does not cover new `git.commit` / `git.add` helpers
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `test_git.py` does not exercise new `git.commit` or `git.add` helpers listed in the plan. A mistaken argv change to `commit --only` or `git add` could pass module-level integration tests but slip past `test_git.py`. Add StubRunner argv assertions for `git.commit` (with `only=`) and `git.add` matching the other new-helper tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add StubRunner argv assertions for git.commit (with only=) and git.add matching the other new-helper tests.

---

**Merge notes (for voters, not machine fields):**

| Subsumed / omitted input | Reason |
|--------------------------|--------|
| FINDING_33 (plan-fidelity) | Merged into output FINDING_27 |
| FINDING_36–38, 41–43, 46 (dyn) | Positive parity or duplicate of FINDING_12/22; no separate fix |
| FINDING_2 vs FINDING_31 | Same redaction theme; different fixes (centralize vs apply on drop strings) — kept separate |
| FINDING_10 vs FINDING_34 | Related RST write paths; `replaces_version != version` insert bug vs single-heading false code-4 — kept separate |
| FINDING_11 vs FINDING_32 | In-scope Python fix vs OOS pre-existing bash — kept separate per OOS rule |
| FINDING_12 vs FINDING_22 | In-scope doc vs OOS defer — kept separate |
