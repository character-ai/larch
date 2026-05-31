### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:18-27,49-51,41-46
- **Concern**: `bullets_path` is required by `_stage_rebump_bullets` / `_commit_changelog_after_rebump` but `rebase_and_rebump` omits it and step 2 calls staging without a path. Scenario: Bash uses `$IMPLEMENT_TMPDIR/.rrr-rebump-bullets.md`; a stateless Phase 3 module has no tmpdir, so implementers may pick cwd-relative paths and break multi-call idempotency or leak bullets across runs
- **Proposed resolution**: Add `bullets_path: Path` (or `work_dir` + fixed filename) to `rebase_and_rebump`; thread the same path through step 2 and step 6; document caller ownership/cleanup

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:24-27
- **Concern**: drop_bump_commit uses allow_changelog_only=False. Scenario: scripts/ship-pr.sh:3244 passes --allow-changelog-only; legacy bump+CHANGELOG-only commits refuse to drop and the path stalls before rebase
- **Proposed resolution**: Pass allow_changelog_only=True (and max_depth=20) to match run_rebase_rebump

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:24-27
- **Concern**: drop_bump_commit omits max_depth=20. Scenario: Default DROP_BUMP_MAX_DEPTH is 10 (python/config.py:68); ship-pr uses --max-depth 20, so deeper stale bumps are missed and replay loops persist
- **Proposed resolution**: Pass max_depth=20 on drop_bump_commit in step 2

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:18-27
- **Concern**: rebase_and_rebump has no bullets_path / tmpdir parameter. Scenario: Bash stages rebump bullets at $IMPLEMENT_TMPDIR/.rrr-rebump-bullets.md (scripts/ship-pr.sh:617-618); step 2 calls _stage_rebump_bullets without bullets_path while the helper signature requires it
- **Proposed resolution**: Add bullets_path (or implement_tmpdir) to rebase_and_rebump and thread it through _stage_rebump_bullets / _commit_changelog_after_rebump

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:20-23
- **Concern**: REBASE_MAX_ATTEMPTS cap has no git-derived algorithm. Scenario: Bash uses persisted REBASE_COUNT (scripts/ship-pr.sh:3173-3178); plan says derive from git but gives no signal, so tests for attempt-cap exhaustion are undefined and the cap may be a no-op
- **Proposed resolution**: Specify the counter (e.g., driver-passed attempt, env, or documented git/reflog heuristic) or defer the cap to ship.py and drop it from this module

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:55-58
- **Concern**: Deterministic pre-pass omits version.go and go.sum. Scenario: Bash and conflict-resolution.md auto-resolve these with upstream checkout (scripts/ship-pr.sh:3317-3320); plan only says auto-generated
- **Proposed resolution**: Name version.go and go.sum explicitly in the pre-pass (upstream :2: checkout + stage), same as plugin.json

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:59-64
- **Concern**: Fixer waterfall omits resolve-conflict role and --conflict-files. Scenario: launch-*-ci.sh requires --role resolve-conflict and validated --conflict-files (scripts/launch-cursor-ci.sh:32,116); wrong role or missing CSV breaks the launcher or fixer context
- **Proposed resolution**: Set config.FIXER_ROLE to resolve-conflict; build launch_fn via agents.launch_tier / build_launch_argv with conflict-files from the current unmerged set

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:33-35
- **Concern**: Non-conflict git rebase failure cleanup not specified. Scenario: rebase-push.sh aborts on non-conflict failure (scripts/rebase-push.sh:252); leaving .git/rebase-merge causes later Stalled/detached states
- **Proposed resolution**: After failed git.rebase without unmerged paths, call git.rebase(runner, --abort) then raise Stalled

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:41-46
- **Concern**: _post-bump changelog tail lacks ship_pr_changelog_ready_after_rebump parity. Scenario: Bash accepts COMMITTED=false when ## [new] exists and CHANGELOG.md is clean (scripts/ship-pr.sh:603-614,787-790); commit_changelog alone can Stalled on benign no-diff replay (#3102)
- **Proposed resolution**: Mirror ship_pr_changelog_ready_after_rebump in _commit_changelog_after_rebump before raising Stalled on committed=False

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:263-274
- **Concern**: Plan step 4 enumerates unmerged paths with git diff --diff-filter=U but the UPDATED git.py section lists only five other helpers and existing diff_name_only(base, head) cannot express --diff-filter=U. Scenario: _resolve_conflicts gets wrong/missing conflict paths or reuses the wrong diff API
- **Proposed resolution**: M add an unmerged_paths(runner, *, cwd) helper (git diff --name-only --diff-filter=U) to the planned git.py edits and test_git.py

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:24-25
- **Concern**: Plan calls drop_bump_commit(..., allow_changelog_only=False) without max_depth=20; default is config.DROP_BUMP_MAX_DEPTH (10) while bash passes --max-depth 20. Scenario: Bump/changelog commits deeper than 10 are not dropped; stale bump replays and Guard-1 stalls diverge from run_rebase_rebump
- **Proposed resolution**: Pass max_depth=config.DROP_CHANGELOG_MAX_DEPTH (20) to drop_bump_commit (and document the same for drop_changelog_commit)

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:38-40
- **Concern**: Re-bump step calls version_bump.classify_bump with no pre-sync and classify_bump hardcodes fetch origin main and merge-base prefers local main (version_bump.py:251-253, 156-159) while rebase uses base_remote/base_ref. Scenario: Fork/upstream rebases classify against stale local main or wrong remote; version regression/correction diverges from ship-pr.sh:3013-3046
- **Proposed resolution**: Add a small sync-local-main port (or git branch -f main to base_remote/base_ref) using the caller base_remote/base_ref before classify; extend classify_bump to accept base_remote/base_ref or document a rebump-only wrapper

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:56-58
- **Concern**: Deterministic pre-pass lists CHANGELOG/plugin.json/LARCH_BUMP_FILES/auto-generated but omits version.go and go.sum that ship-pr.sh auto-resolves with git checkout --ours (scripts/ship-pr.sh:3317-3321). Scenario: Go-module rebases leave trivial conflicts for the fixer waterfall or NeedsUserInput instead of auto-resolving like bash
- **Proposed resolution**: Add version.go and go.sum to the trivial upstream checkout path (git checkout --ours parity)

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:27-28
- **Concern**: Stage-rebump bullets path is unspecified: bash uses $IMPLEMENT_TMPDIR/.rrr-rebump-bullets.md (scripts/ship-pr.sh:617-618) but rebase_and_rebump has no tmpdir/bullets_path and line 27 calls _stage_rebump_bullets without bullets_path while line 49 requires it. Scenario: Bullets are written/read from the wrong place or the helper signature is ambiguous
- **Proposed resolution**: Add bullets_path: Path | str (default from config.ENV_IMPLEMENT_TMPDIR) to rebase_and_rebump; align both _stage_rebump_bullets call sites

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rebase.py:61-63
- **Concern**: Plan routes fixer conflicts through agents.launch_tier via launch_fn but agents.build_launch_argv has no --conflict-files (python/agents.py:129-169) while launch-*-ci.sh requires it for resolve-conflict. Scenario: Fixer launches run without the conflict CSV; agents cannot resolve the intended paths
- **Proposed resolution**: Extend build_launch_argv/launch_tier with optional conflict_files and have launch_fn pass the remaining unmerged CSV

### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:22-23
- **Concern**: derive the attempt count from git state is required for REBASE_MAX_ATTEMPTS but no counting rule is specified (bash uses persisted REBASE_COUNT in scripts/ship-pr.sh:3173-3178). Scenario: Implementers invent incompatible caps; attempt-cap tests encode the wrong behavior
- **Proposed resolution**: Define the counter explicitly (e.g. count rebump-marker commits or document that the cap is enforced only by the future ship.py driver until Phase 7)

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/rebase.py:24-25
- **Concern**: allow_changelog_only=False diverges from bash run_rebase_rebump --allow-changelog-only (scripts/ship-pr.sh:3244). Scenario: Legacy in-flight branches whose bump commit is CHANGELOG-only get DROPPED=false and Stalled instead of continuing
- **Proposed resolution**: Match bash with allow_changelog_only=True for the rebump drop call, or document the intentional divergence and add a targeted unit test

### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:18-52
- **Concern**: `rebase_and_rebump` omits `tmpdir` / rebump bullets path while helpers require `bullets_path`. Scenario: Bullet staging/commit tail cannot mirror `ship_pr_rebump_bullets_path` (`$IMPLEMENT_TMPDIR/.rrr-rebump-bullets.md`); steps 2 and 6 cannot run
- **Proposed resolution**: Add `tmpdir: str` (or explicit `bullets_path`) to `rebase_and_rebump`; derive `{tmpdir}/.rrr-rebump-bullets.md` in `_stage_rebump_bullets` / `_commit_changelog_after_rebump`; thread through orchestration

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:20-23
- **Concern**: Attempt cap says "derive from git state" but defines no git-derived counter. Scenario: Implementers cannot honor locked decision #1 / `REBASE_MAX_ATTEMPTS` without inventing ad hoc logic or reintroducing persisted `REBASE_COUNT`
- **Proposed resolution**: Specify the counter (e.g. document the git signal and comparison) or defer the cap to the future `ship.py` driver with an explicit Phase 3 note

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:39-40
- **Concern**: Re-bump "version-regression guard" is one line; bash compares classify output to `${base_remote}/${base_ref}` plugin version and recomputes via `bump_type`. Scenario: Stale conflict resolution can yield `NEW_VERSION` below published base; force-push rebases a regressed semver (`scripts/ship-pr.sh` ~3034-3071)
- **Proposed resolution**: Spell out parity: read base plugin version from `git show_file` on `{base_remote}/{base_ref}`; if `new_version` < base and bump_type != NONE, recompute with `_apply_bump_type`; then `apply_bump`; cover in `test_rebase.py`

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:59-63
- **Concern**: python/agents.py:129-169. Scenario: Fixer waterfall cites `agents.launch_tier` but `build_launch_argv` has no `--conflict-files`; resolve-conflict launchers need the CSV in the prompt (`scripts/launch-cursor-ci.sh` ~116-122)
- **Proposed resolution**: Real `launch_fn` may run agents without conflict paths; fixer cannot target unmerged files Extend `build_launch_argv`/`launch_tier` with optional `conflict_files` or document that `rebase.py` appends `--conflict-files` when building argv; stub tests should assert CSV forwarding

### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:41-46
- **Concern**: `_commit_changelog_after_rebump` omits bash stall when staged bullets exist but `duplicate_version_heading_count(new_version) > 0`. Scenario: Concurrent same-version merge: bullets are deleted and operator loses release notes (`scripts/ship-pr.sh` ~721-730)
- **Proposed resolution**: Add `duplicate_version_heading_count` check: if bullets staged and count > 0, raise `Stalled`; add stub test case
