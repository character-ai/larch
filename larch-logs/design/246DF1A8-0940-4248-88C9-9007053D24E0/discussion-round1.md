## Decision 1: PR shape — one hard-cutover PR
- **Question**: Land as a single atomic PR, or split repoint/delete across PRs?
- **Resolution**: One hard-cutover PR. Repoint every consumer, then delete the retired `.sh` + `.md` siblings + harnesses in the same PR. No shim/forwarding stubs.
- **Source**: issue-body (baked-in spec)

## Decision 2: Parity-gap handling
- **Question**: If a `cli.py` git/phantom verb is not a complete replacement (flags, exit codes, output), what happens?
- **Resolution**: Fix it in this slice. Extend `python/git.py` / `python/phantom.py` so every listed script still deletes atomically in one PR.
- **Source**: issue-body (Resolved decision 1)

## Decision 3: Test-coverage bar
- **Question**: Can a bash harness be deleted if its behavior is not covered by pytest?
- **Resolution**: No silent coverage loss. Before deleting each bash harness, confirm `python/test_git.py` / `python/test_phantom.py` cover its behavior; add pytest cases for any gap.
- **Source**: issue-body (Resolved decision 2)

## Decision 4: lib-phantom-probe.sh fate
- **Question**: Delete `lib-phantom-probe.sh`, or keep it as a repointed survivor?
- **Resolution**: Keep it. It is sourced by `scripts/rebase-checkpoint-probe.sh` and is not in the retire list. Repoint its internals from `check-phantom-dirty.sh` to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git phantom-probe`.
- **Source**: issue-body (Session notes 2026-06-19, codebase-verified)

## Decision 5: push/rebase verb ownership
- **Question**: Do the push verbs live in `git.py` or the `push` domain?
- **Resolution**: Push verbs live in the `push` domain (`python/push.py`): `git-push.sh` -> `cli.py push branch`, `git-force-push.sh` -> `cli.py push force`. Remaining git plumbing stays in the `git` domain (`python/git.py`), e.g. `git-rebase-abort.sh` -> `cli.py git rebase-abort`.
- **Source**: issue-body (Session notes 2026-06-19, codebase-verified)

## Decision 6: Out of scope
- **Question**: What is explicitly NOT in this slice?
- **Resolution**: No re-porting logic (native Python exists, parity-verified). Do not migrate non-listed scripts (`create-pr.sh`, `merge-pr.sh`, `lib-phantom-probe.sh`) beyond repointing their references. No shim/forwarding `.sh` stubs or new abstractions.
- **Source**: issue-body (Non-goals)
