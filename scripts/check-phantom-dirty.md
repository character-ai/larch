# check-phantom-dirty.sh

**Purpose**: detect non-ignored untracked files that appear after the
`/implement` session untracked baseline was captured. It is a thin wrapper
around `scripts/check-mid-run-dirty-tree.sh --mode baseline`; it does not
reimplement baseline comparison.

**Primary callers**: `skills/implement/SKILL.md` probe instructions at key
step boundaries after external implementation dispatch, post-rebase
checkpoints, and immediately before `/bump-version`.

## Interface

```bash
check-phantom-dirty.sh \
  --baseline <nul-delimited-baseline> \
  --step <step-id> \
  --phantom-paths-dir <dir>
```

`--step` must match `^[A-Za-z0-9_.-]+$`. Invalid tokens emit
`STATUS=unknown` with `REASON=bad-step` before any path construction.

## Output Contract

- `STATUS=clean`: no tracked changes and no new untracked paths.
- `STATUS=phantom`: new non-ignored untracked paths appeared since the
  baseline. The output also includes `PHANTOM_COUNT=<n>` and
  `PHANTOM_PATHS_FILE=<path>`.
- `STATUS=tracked-only`: the tree is dirty only because of staged or unstaged
  tracked paths. This is silent for `/implement` phantom probes because tracked
  mutations are expected at some boundaries.
- `STATUS=unknown`: classification was inconclusive. The output includes
  `REASON=<token>` when available.

The `PHANTOM_PATHS_FILE` is copied to
`<phantom-paths-dir>/phantom-paths-<step-id>.z` and is NUL-delimited. Callers
surface only the file path in session-local diagnostics; public anchors do not
include the path contents.

## Scope

"Phantom" strictly means new non-ignored untracked files as reported by
`git ls-files --others --exclude-standard`. Ignored build artifacts are outside
this detector's scope.

This session-wide baseline answers "which untracked files are new since
`/implement` started?". It is intentionally distinct from
`pre-review-untracked.txt` and `skills/implement/scripts/check-review-changes.sh`,
which answer "which untracked files are new since `/review` started?" for
review-change detection.

Rebase probes can report legitimate residue such as conflict leftovers. The
detector records those paths for operator inspection; it never restores, cleans,
or deletes them.

## Harness

`scripts/test-check-phantom-dirty.sh`, wired by
`make test-check-phantom-dirty`.

## Edit-in-sync

Update `scripts/test-check-phantom-dirty.sh`, `skills/implement/SKILL.md`, and
`docs/linting.md` when changing this contract.
