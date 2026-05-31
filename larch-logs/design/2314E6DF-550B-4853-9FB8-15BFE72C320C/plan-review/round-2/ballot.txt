Normalizing the 22 reviewer slots into merged findings with stable IDs, max severity per merge, and verbatim revision bullets.


### FINDING_1: `rebase_and_rebump` omits rebump bullets path / tmpdir
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `_stage_rebump_bullets` and `_commit_changelog_after_rebump` require `bullets_path`, but `rebase_and_rebump` does not accept or thread a path (or `tmpdir` / `IMPLEMENT_TMPDIR`). Bash stages at `$IMPLEMENT_TMPDIR/.rrr-rebump-bullets.md` (`scripts/ship-pr.sh:617-618`). Step 2 can call staging without a path while helpers require one. A stateless Phase 3 module has no tmpdir, so implementers may use cwd-relative paths, breaking multi-call idempotency, leaking bullets across runs, or making steps 2 and 6 unrunnable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `bullets_path: Path` (or `work_dir` + fixed filename) to `rebase_and_rebump`; thread the same path through step 2 and step 6; document caller ownership/cleanup
  - From Cursor-Innovation: Add bullets_path (or implement_tmpdir) to rebase_and_rebump and thread it through _stage_rebump_bullets / _commit_changelog_after_rebump
  - From Cursor-Pragmatic: Add bullets_path: Path | str (default from config.ENV_IMPLEMENT_TMPDIR) to rebase_and_rebump; align both _stage_rebump_bullets call sites
  - From Cursor-Requirements: Add `tmpdir: str` (or explicit `bullets_path`) to `rebase_and_rebump`; derive `{tmpdir}/.rrr-rebump-bullets.md` in `_stage_rebump_bullets` / `_commit_changelog_after_rebump`; thread through orchestration

### FINDING_2: `drop_bump_commit` uses `allow_changelog_only=False` vs bash
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan / rebump path calls `drop_bump_commit` with `allow_changelog_only=False`. Bash `run_rebase_rebump` passes `--allow-changelog-only` (`scripts/ship-pr.sh:3244`). Legacy bump+CHANGELOG-only commits may refuse to drop, yielding `DROPPED=false` and `Stalled` instead of continuing the rebump path before rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass allow_changelog_only=True (and max_depth=20) to match run_rebase_rebump
  - From Cursor-Pragmatic: Match bash with allow_changelog_only=True for the rebump drop call, or document the intentional divergence and add a targeted unit test

### FINDING_3: `drop_bump_commit` default `max_depth` (10) vs bash (20)
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan calls `drop_bump_commit` without `max_depth=20`; default is `config.DROP_BUMP_MAX_DEPTH` (10) (`python/config.py:68`) while bash uses `--max-depth 20`. Bump/changelog commits deeper than 10 are not dropped; stale bump replays and Guard-1 stalls diverge from `run_rebase_rebump`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass max_depth=20 on drop_bump_commit in step 2
  - From Cursor-Pragmatic: Pass max_depth=config.DROP_CHANGELOG_MAX_DEPTH (20) to drop_bump_commit (and document the same for drop_changelog_commit)

### FINDING_4: `REBASE_MAX_ATTEMPTS` cap lacks a specified git-derived counter
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan requires deriving attempt count from git state but defines no algorithm. Bash uses persisted `REBASE_COUNT` (`scripts/ship-pr.sh:3173-3178`). Implementers may invent incompatible caps; attempt-cap tests are undefined and the cap may be a no-op or fail locked decision #1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify the counter (e.g., driver-passed attempt, env, or documented git/reflog heuristic) or defer the cap to ship.py and drop it from this module
  - From Cursor-Pragmatic: Define the counter explicitly (e.g. count rebump-marker commits or document that the cap is enforced only by the future ship.py driver until Phase 7)
  - From Cursor-Requirements: Specify the counter (e.g. document the git signal and comparison) or defer the cap to the future `ship.py` driver with an explicit Phase 3 note

### FINDING_5: Deterministic pre-pass omits `version.go` and `go.sum`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The deterministic pre-pass lists CHANGELOG / plugin.json / LARCH_BUMP_FILES / auto-generated but omits `version.go` and `go.sum`. Bash auto-resolves these with upstream checkout (`scripts/ship-pr.sh:3317-3321`). Go-module rebases may leave trivial conflicts for the fixer waterfall or `NeedsUserInput` instead of matching bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name version.go and go.sum explicitly in the pre-pass (upstream :2: checkout + stage), same as plugin.json
  - From Cursor-Pragmatic: Add version.go and go.sum to the trivial upstream checkout path (git checkout --ours parity)

### FINDING_6: Fixer waterfall missing `resolve-conflict` role and `--conflict-files`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The fixer waterfall routes through `agents.launch_tier` / `build_launch_argv`, but `build_launch_argv` has no `--conflict-files` (`python/agents.py:129-169`) while `launch-*-ci.sh` requires `--role resolve-conflict` and validated `--conflict-files` (`scripts/launch-cursor-ci.sh:32,116-122`). Wrong role or missing CSV breaks the launcher or fixer context; agents cannot target unmerged files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Set config.FIXER_ROLE to resolve-conflict; build launch_fn via agents.launch_tier / build_launch_argv with conflict-files from the current unmerged set
  - From Cursor-Pragmatic: Extend build_launch_argv/launch_tier with optional conflict_files and have launch_fn pass the remaining unmerged CSV
  - From Cursor-Requirements: Real `launch_fn` may run agents without conflict paths; fixer cannot target unmerged files Extend `build_launch_argv`/`launch_tier` with optional `conflict_files` or document that `rebase.py` appends `--conflict-files` when building argv; stub tests should assert CSV forwarding

### FINDING_7: Non-conflict `git rebase` failure cleanup unspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Non-conflict git rebase failure cleanup is not specified. Bash aborts on non-conflict failure (`scripts/rebase-push.sh:252`). Leaving `.git/rebase-merge` can cause later `Stalled` / detached states.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After failed git.rebase without unmerged paths, call git.rebase(runner, --abort) then raise Stalled

### FINDING_8: Post-rebump changelog tail lacks `ship_pr_changelog_ready_after_rebump` parity
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_commit_changelog_after_rebump` lacks parity with bash `ship_pr_changelog_ready_after_rebump`. Bash accepts `COMMITTED=false` when `## [new]` exists and `CHANGELOG.md` is clean (`scripts/ship-pr.sh:603-614,787-790`). `commit_changelog` alone can `Stalled` on benign no-diff replay (#3102).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror ship_pr_changelog_ready_after_rebump in _commit_changelog_after_rebump before raising Stalled on committed=False

### FINDING_9: Plan / `git.py` missing `unmerged_paths` helper for `--diff-filter=U`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan step 4 enumerates unmerged paths with `git diff --diff-filter=U`, but the planned `git.py` edits list only other helpers; existing `diff_name_only(base, head)` cannot express `--diff-filter=U`. `_resolve_conflicts` may get wrong/missing conflict paths or reuse the wrong diff API.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: M add an unmerged_paths(runner, *, cwd) helper (git diff --name-only --diff-filter=U) to the planned git.py edits and test_git.py

### FINDING_10: Re-bump `classify_bump` without pre-sync to `base_remote` / `base_ref`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Re-bump calls `version_bump.classify_bump` with no pre-sync; `classify_bump` hardcodes fetch `origin main` and merge-base prefers local `main` (`version_bump.py:251-253, 156-159`) while rebase uses `base_remote` / `base_ref`. Fork/upstream rebases may classify against stale local main or wrong remote; version regression/correction diverges from `ship-pr.sh:3013-3046`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a small sync-local-main port (or git branch -f main to base_remote/base_ref) using the caller base_remote/base_ref before classify; extend classify_bump to accept base_remote/base_ref or document a rebump-only wrapper

### FINDING_11: Version-regression guard underspecified for re-bump
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The re-bump “version-regression guard” is one line in the plan; bash compares classify output to `${base_remote}/${base_ref}` plugin version and recomputes via `bump_type`. Stale conflict resolution can yield `NEW_VERSION` below published base; force-push rebases a regressed semver (`scripts/ship-pr.sh` ~3034-3071).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Spell out parity: read base plugin version from `git show_file` on `{base_remote}/{base_ref}`; if `new_version` < base and bump_type != NONE, recompute with `_apply_bump_type`; then `apply_bump`; cover in `test_rebase.py`

### FINDING_12: Missing stall when staged bullets collide with duplicate version heading
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: `_commit_changelog_after_rebump` omits bash behavior when staged bullets exist but `duplicate_version_heading_count(new_version) > 0`. Scenario: concurrent same-version merge—bullets are deleted and the operator loses release notes (`scripts/ship-pr.sh` ~721-730).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `duplicate_version_heading_count` check: if bullets staged and count > 0, raise `Stalled`; add stub test case

---

**Merge summary**: 22 input slots → **12** normalized findings. Subsumed groupings: bullets path (4 slots), `allow_changelog_only` (2), `max_depth` (2), rebase attempt cap (3), `version.go`/`go.sum` (2), fixer `--conflict-files` (3). `FINDING_10` (classify pre-sync) and `FINDING_11` (explicit version-regression guard) stay separate because they need different fixes on different code paths. No `### OOS_N:` inputs; no empty-merge attestation (output contains `### FINDING_N:` blocks).
