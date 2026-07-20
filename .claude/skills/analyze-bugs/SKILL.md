---
# larch-run-lifecycle: shared-v1 skill=analyze-bugs
name: analyze-bugs
description: "Use when verifying whether recent filed [BUG] issues were fixed. Dev-only; report-only unless follow-up filing is approved."
argument-hint: "[-n COUNT] [--deep-max M] [--runtime-max M] [--deep-model sonnet|opus|fable] [--refresh] [--sample K] [--repo owner/name]"
allowed-tools: Bash, Read, Task, AskUserQuestion
---

**MANDATORY: Follow the complete shared lifecycle contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `analyze-bugs`.**

# /analyze-bugs

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

Dev-only workflow for verifying whether filed `[BUG]` issues were fixed in `main`.
It is report-only by default and may file one combined follow-up only after
explicit approval. It does not inspect merged changes for new unfiled bugs;
use `/validate-merged` for that separate, more expensive workflow.

## Flags and preflight

Parse `$ARGUMENTS` before any command or Task dispatch.

Accept only `-n` / `--count`, `--deep-max`, `--runtime-max`, `--deep-model`,
`--refresh`, `--sample`, and `--repo`. `-n N` means the newest `N` filed
`[BUG]` issues. Lowering it never deletes reusable ledger history; raising it
backfills older issues absent from a valid cache record.

Before dispatch, require a clean checkout on `main` synchronized with
`origin/main`. `analyze-bugs prefetch` keeps immutable evidence bundles under
`$XDG_CACHE_HOME` and returns a mutable `LEDGER_PATH` under
`$XDG_STATE_HOME/larch/analysis-state/<repo>/analyze-bugs/`. Use only that
printed ledger path in later stages. The first run imports the legacy cache
ledger when present. Never commit, push, or open a PR for analyzer state.

## Workflow

Run `analyze-bugs prefetch`, then `ledger`, read-only `bug-fix-triage` and
`bug-fix-verifier` Tasks, `runtime`, and the one `report` command using the
explicit paths each command prints. Preserve the existing fail-closed evidence
token and ingest boundaries: pass triage agents only batch paths, and never
relay evidence tokens or bundle contents in prompts. Runtime verification is
bounded by `--runtime-max`; it executes targeted tests or mapped harnesses when
available, so this workflow can run tests.

The report renders fixed verdicts, uncertified evidence, introduced-risk and
class-completeness checks, calibration, chronic zones, fix chains, and one
approval-gated combined follow-up body. Ask before filing it through `/issue`.
