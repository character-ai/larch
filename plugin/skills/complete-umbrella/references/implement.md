# Implement Phase

**Consumer**: The second fresh general-purpose Agent spawned by the `/complete-umbrella` leaf orchestrator.

**Contract**: Implement from the bounded design and leaf inputs, run focused checks, commit the change, and persist the diff and summary handoffs.

**When to load**: **MANDATORY: READ ENTIRE FILE** only for the primary implement phase.

Read `phase-common.md` in this directory in full before acting.

Read only `$SESSION_TMPDIR/design-brief.md` and `$SESSION_TMPDIR/leaf-issue.md` as initial task inputs. Do not read the umbrella issue again. Do not repeat broad repository exploration. Open only the source, tests, and companion files named by the brief, plus narrow dependencies needed to edit them safely.

Require a clean worktree on `main`. Create branch `complete-umbrella/leaf-<LEAF>` from the synchronized `main` checkout. Stop if that branch name exists in an unexpected state.

Implement the brief completely. Follow the repository architecture and editing rules summarized in the brief. Add or update focused tests. Refresh every generated or projected companion named by the brief. Run the brief's changed-path checks with bounded output.

Review the working diff for accidental scope, secrets, and missing tests. Stage only intended paths. Commit once with a concise message. Require a clean worktree with at least one feature commit.

Write these artifacts below `$SESSION_TMPDIR`:

- `implementation.diff`: the complete `git diff main...HEAD`, redirected to the file instead of returned in tool output.
- `implementation-summary.md`: the branch, full commit SHA, changed paths, and checks run. Keep it below 2,000 tokens.

End with:

```text
PHASE_STATUS=complete
HANDOFF_FILE=<absolute path to implementation-summary.md>
```
