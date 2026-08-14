---
# larch-run-lifecycle: shared-v1 skill=validate-merged
name: validate-merged
description: "Use when inspecting recent merged changes for possible unfiled bugs. Dev-only; report-only unless a follow-up is approved."
argument-hint: "[--max-merges N] [--repo owner/name]"
allowed-tools: Bash, Read, Task, AskUserQuestion
---

**MANDATORY: Follow the complete shared lifecycle contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `validate-merged`.**

# /validate-merged

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

Inspect recent first-parent `main` merges for possible new, unfiled bugs. This
is separate from `/analyze-bugs`: it does not fetch `[BUG]` issues, run
bug-fix triage or deep verification, or execute fix-SHA runtime checks.

## Bounds and state

Parse `$ARGUMENTS` before any command or Task dispatch.

The default and maximum selected work for one invocation is 20 merges. On a
first run without a trustworthy state marker, inspect only the previous 48
hours and select at most 20 eligible merges. `--max-merges N` is the explicit
cost cap; every eligible merge over that cap stays in the pending
frontier. Do not accept `-n`, `--count`, or an unbounded history mode.

This is generally more expensive per selected merge than filed-bug verification:
it launches one finder per selected merge and one refuter per candidate. The
recommended first run is the default 48-hour, 20-merge window.

Read the `STATE_PATH` returned by `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" validate-merged prepare`. It lives under
`$XDG_STATE_HOME/larch/analysis-state/v2/<client-repo>/<storage-origin-id>/validate-merged/`. State contains only
compact merge frontier and unresolved candidate identities, never issue bodies,
diffs, transcripts, temporary paths, or raw agent output. Do not advance state
until every enabled stage and the final report pass.

## Workflow

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" validate-merged prepare --root "$PWD" --run-dir "$RUN_DIR" [--max-merges N]`.
For each bundle in its manifest, dispatch one `validate-merged-finder` Task in finder
mode and append its unchanged JSONL to the printed finder capture path. Run
`"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" validate-merged ingest-finder`; for every queue row, dispatch a refuter Task,
append unchanged JSONL, then run `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" validate-merged ingest-refuter`.

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" validate-merged report` with a temporary `--state-output`. It retains
unresolved candidates across runs. The report is the only user-facing result.
Offer one combined follow-up issue only after explicit approval.

After the report succeeds, run `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" validate-merged write-state` with the generated
state and the `STATE_DIGEST` returned by prepare as `--expected-digest`. A
concurrent update fails without overwriting either result. Never commit, push,
or open a PR for this marker.
