# Ship Phase

Read `phase-common.md` in this directory in full before acting.

Read `$SESSION_TMPDIR/review-summary.md`. Require its final HEAD to match the clean current branch. Do not read the issue bodies, design brief, implementation diff, or repository source.

Run the standalone driver in ship mode:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" complete-umbrella ship-leaf \
  --mode ship \
  --repository "<REPOSITORY>" \
  --repo-root "$PWD" \
  --handoff-root "$SESSION_TMPDIR" \
  --umbrella "<UMBRELLA>" \
  --leaf "<LEAF>"
```

The driver owns the deterministic sequence: push, create or verify a PR with the leaf closing link, refresh CI once every 300 seconds, distill a failed run, squash-merge with `--admin --delete-branch` after green checks, verify the merge, retitle the closed leaf `[DONE]`, switch to `main`, fetch and rebase `origin/main`, delete the feature branch, and verify every postcondition.

Route only on `SHIP_STATUS`:

- `complete`: run the same command with `--mode verify`. Require another `SHIP_STATUS=complete`.
- `ci_failed`: require `CI_ERRORS_FILE` to be a regular file below `$SESSION_TMPDIR`. Spawn one fresh general-purpose Agent with only the identifiers from your prompt, the positive fix round, `CI_ERRORS_FILE`, and `PHASE_CONTRACT=$CLAUDE_PLUGIN_ROOT/skills/complete-umbrella/references/ci-fix.md`. Await its task notification. Require exactly `PHASE_STATUS=complete` and a contained `HANDOFF_FILE`, then rerun ship mode. The driver's persisted state enforces the fix-attempt cap.
- Any other value or nonzero exit: fail. Do not repair deterministic shipping state by hand.

Do not poll while the driver runs. Do not spawn a CI fixer when checks are pending or green.

After verified completion, write `$SESSION_TMPDIR/ship-summary.md` with only the PR number, PR URL, final issue state, final local HEAD, and `SHIP_STATUS=complete`.

End with:

```text
PHASE_STATUS=complete
HANDOFF_FILE=<absolute path to ship-summary.md>
```
