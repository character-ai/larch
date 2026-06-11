## Goal
Implement issue #4021: [IMPLEMENTING] [BUG] (URGENT) /implement Step 4: stale git-commit.sh prose + wrapper usage hint\n\n[BUG] (URGENT) /implement Step 4: stale git-commit.sh prose + wrapper usage hint.

## Implementation Plan
[BUG] (URGENT) /implement Step 4: stale git-commit.sh prose + wrapper usage hint

## Context

An `/implement` run (larch1 clone, plugin cache 49.0.16, session `claude-implement-larch1-89g515rg`) failed Step 4 "commit (impl)" twice in a row on the Claude-fallback commit path:

1. **Exit 127**: invoked `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/git-commit.sh`. That path does not exist and never has.
2. **Exit 2**: after `ls`-discovering the right script, invoked `commit-implementation.sh --stage-all`. The wrapper rejected the unknown option fail-closed (`COMMITTED=false`, `ERROR=unknown option: --stage-all`).

No commit or staging occurred; both calls failed before any git mutation. The 49.0.16 plugin cache is byte-identical to the repo for `skills/implement/SKILL.md`, so this is not a packaging or staleness problem.

## Root cause

Both failures are orchestrator improvisation. Each exposes a repo-side hardening gap:

1. **Stale prose seed.** The Step 4 external-implementer paragraph in `skills/implement/SKILL.md` says "Skip the `git-commit.sh` invocation." while the directed Claude-fallback invocation immediately below uses `commit-implementation.sh`. `git-commit.sh` is real but lives at root `scripts/git-commit.sh` and serves other flows. The likely trigger (inference): mid-run context compaction dropped the Step 4 block; the orchestrator retained the `git-commit.sh` token from the skip prose and synthesized a nonexistent path for it under `skills/implement/scripts/`. This is the stale-prose drift class `.claude/rules/drift-prone-prose-in-docs.md` warns about.
2. **Sibling-flag confusion with no disambiguation hint.** `--stage-all` is a real flag of the sibling `commit-review-fixes.sh` (Step 5 review-fix commits). `commit-implementation.sh` deliberately omits it: implementation commits must name specific files or use `--pathspec-from-file`, so unrelated working-tree content is never swept into the commit. The usage error is correct and fail-closed, but it offers no pointer toward the right script or shape, so a confused orchestrator's natural next move is another guess.

## Prescription

1. **Fix the stale prose** in `skills/implement/SKILL.md` Step 4: change "Skip the `git-commit.sh` invocation." to "Skip the `commit-implementation.sh` invocation." in the external-implementer paragraph. After this edit, the `/implement` SKILL.md contains zero `git-commit.sh` mentions.
2. **Add a disambiguation hint to the wrapper's usage-failure path.** In `skills/implement/scripts/commit-implementation.sh`, extend the unknown-option `fail_usage` branch to also emit one stderr hint line via `larch_err`, for example: `HINT: --stage-all belongs to commit-review-fixes.sh (Step 5 review fixes); implementation commits name specific files or use --pathspec-from-file.` Keep the existing machine grammar (`COMMITTED=false`, `SHA=`, `ERROR=...`) and exit code 2 unchanged. Mirror the contract change in `skills/implement/scripts/commit-implementation.md`.
3. **Pin both with harnesses.** Extend `skills/implement/scripts/test-commit-implementation.sh` with an unknown-option case asserting exit 2, `COMMITTED=false`, and hint emission. Extend `scripts/test-implement-structure.sh` to assert (a) the Step 4 skip prose references `commit-implementation.sh`, and (b) the literal `skills/implement/scripts/git-commit.sh` appears nowhere under `skills/implement/`.
4. **Sweep for other unqualified `git-commit.sh` prose** in `skills/**/SKILL.md` and `skills/**/scripts/*.md` (excluding `larch-logs/`); path-qualify any reference that does not already point at root `scripts/git-commit.sh`.

## Acceptance

- `git grep -n "git-commit" skills/implement/SKILL.md` returns no matches.
- In a scratch repo, `commit-implementation.sh --stage-all` exits 2 with `COMMITTED=false` and the new hint on stderr.
- `make lint` and the extended harnesses pass.

## Test plan
(no test plan section in plan-file)
