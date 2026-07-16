---
name: validate-merged
description: "Use when inspecting recent merged changes for possible unfiled bugs. Dev-only; report-only unless a follow-up is approved."
argument-hint: "[--max-merges N] [--repo owner/name]"
allowed-tools: Bash, Read, Task, AskUserQuestion
---

# /validate-merged

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

Inspect recent first-parent `main` merges for possible new, unfiled bugs. This
is separate from `/analyze-bugs`: it does not fetch `[BUG]` issues, run
bug-fix triage or deep verification, or execute fix-SHA runtime checks.

## Bounds and state

Parse `$ARGUMENTS` before any command or Task dispatch.

The default and maximum selected work for one invocation is 20 merges. On a
first run without a trustworthy committed marker, inspect only the previous 48
hours and select at most 20 eligible merges. `--max-merges N` is the explicit
cost cap; every eligible merge over that cap stays in the committed pending
frontier. Do not accept `-n`, `--count`, or an unbounded history mode.

This is generally more expensive per selected merge than filed-bug verification:
it launches one finder per selected merge and one refuter per candidate. The
recommended first run is the default 48-hour, 20-merge window.

Read `larch-logs/shared/validate-merged-state.json` from a clean checkout on
the synced default branch before optional local artifacts. State contains only
compact merge frontier and unresolved candidate identities—never issue bodies,
diffs, transcripts, temporary paths, or raw agent output. Do not advance state
until every enabled stage and the final report pass.

## Workflow

Run `validate-merged prepare --root "$PWD" --run-dir "$RUN_DIR" [--max-merges N]`.
For each bundle in its manifest, dispatch one `validate-merged-finder` Task in finder
mode and append its unchanged JSONL to the printed finder capture path. Run
`validate-merged ingest-finder`; for every queue row, dispatch a refuter Task,
append unchanged JSONL, then run `validate-merged ingest-refuter`.

Run `validate-merged report` with a temporary `--state-output`. It retains
unresolved candidates across runs. The report is the only user-facing result.
Offer one combined follow-up issue only after explicit approval.

To publish the marker, require a clean, synced default branch. Create a unique
state branch in the current checkout, run `validate-merged write-state` for the
generated state, stage and commit only
`larch-logs/shared/validate-merged-state.json`, push, open a state-only PR,
attempt an immediate `gh pr merge --squash --admin`, and restore/sync the
default branch. Never use `git worktree` or `git add -A`. If the marker changed
remotely after it was read, reconcile safely or stop without overwriting it.
Before PR creation, retain and report the recovery branch; after creation, the
PR is the recovery surface. State advances only when the merged default branch
contains the marker.
