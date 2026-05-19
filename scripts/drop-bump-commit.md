# drop-bump-commit.sh

**Purpose**: Drop the most recent "Bump version to X.Y.Z" commit found within the last `--max-depth` commits (default 10). Narrow primitive used by `/implement`'s Rebase + Re-bump Sub-procedure (step 1) to strip a stale version-bump commit before rebasing onto latest main. The script walks back from HEAD looking for the bump commit, so it handles the common `HEAD=larch-log-flush, HEAD~1=bump` shape without manual intervention.

**Invariant**: `LARCH_BUMP_FILES` defines the trust boundary for which commit shapes are safe to destructively reset (`git reset --hard HEAD~1`). The allowed-file set must match exactly what `apply-bump.sh` (and any consumer-repo equivalent) produces as bump artifacts. If the env var lists fewer files than the bump actually touches, Guard 4 refuses the drop (fail-closed). If it lists more, the extra entries are harmless (membership check, not exact match).

## Guards (all must pass for `DROPPED=true`)

1. **Clean worktree (tracked files)** — `git status --porcelain --untracked-files=no` must be empty. Untracked files are excluded because the drop operation does not affect them; excluding them prevents spurious `DROPPED=false` when larch-log writes are pending in the worktree.
2. **Bump found within depth** — walk HEAD, HEAD~1, … up to `--max-depth` commits; the first commit whose subject matches `^Bump version to [0-9]+\.[0-9]+\.[0-9]+$` is selected. If none found, `DROPPED=false` with a warning naming the walked depth.
3. **Parent of found commit exists** — `HEAD~(found_at+1)` must resolve.
4. **Allowed files** — every file in `git diff --name-only HEAD~(found_at+1) HEAD~found_at` must be in the allowed set:
   - **When `LARCH_BUMP_FILES` is unset**: exact two-string equality against `.claude-plugin/plugin.json` alone or `.claude-plugin/plugin.json` + `CHANGELOG.md` (byte-identical to pre-configuration behavior).
   - **When `LARCH_BUMP_FILES` is set**: colon-separated list parsed with whitespace trimming and empty-segment skipping. Replacement semantics — replaces the default `.claude-plugin/plugin.json`, not additive. `CHANGELOG.md` is always appended (allowed but never required). Two-gate membership check: (a) every changed file must appear in the allowed set, and (b) at least one configured bump file (not `CHANGELOG.md`) must be present in the diff. Fail-closed on empty parse and on empty/CHANGELOG-only diffs.

## Environment variable

- **`LARCH_BUMP_FILES`**: Colon-separated list of bump files. Paths must match `git diff --name-only` format (repo-root-relative, no `./` prefix). Paths must not contain `:`. See `docs/configuration-and-permissions.md` for full documentation.

## Output contract

- `DROPPED=true|false` (stdout, KEY=VALUE)
- `OLD_BUMP_SHA=<sha>` (stdout, only when `DROPPED=true`)
- `WARN: ...` lines on stderr explain which guard refused the drop

## Drop mechanism

- When the bump is at HEAD (`found_at=0`): `git reset --hard HEAD~1` (fast path, existing behavior).
- When the bump is deeper (`found_at>0`): `git rebase --onto HEAD~(found_at+1) HEAD~found_at` — replays the commits above the bump onto the bump's parent, effectively removing the bump commit from history.

## Exit codes

- `0` — success, including no-op cases (inspect `DROPPED`)
- `1` — git error during the drop (reset or rebase); rebase is aborted automatically before exit

## Test harness

`scripts/test-drop-bump-commit.sh` — offline regression harness wired into `make test-harnesses` (Makefile target `test-drop-bump-commit`). Creates isolated temp repos with controlled commit shapes.

## Edit-in-sync

When editing `scripts/drop-bump-commit.sh`:
- Update this file (`scripts/drop-bump-commit.md`) for any behavioral change.
- Update `scripts/test-drop-bump-commit.sh` for any Guard 4 logic change.
- Update `docs/configuration-and-permissions.md` `LARCH_BUMP_FILES` section for any env var contract change.
- Update `skills/implement/references/rebase-rebump-subprocedure.md` step 1 for any output-contract change.
- Update `skills/implement/references/bump-verification.md` for any `DROPPED=false` scenario change.
- Update `skills/implement/references/conflict-resolution.md` Phase 1 trivial-files and the plugin.json-conflicts note.
