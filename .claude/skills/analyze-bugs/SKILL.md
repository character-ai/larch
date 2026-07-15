---
name: analyze-bugs
description: "Use when auditing recent [BUG] issues with a low-cost cached verification funnel. Dev-only; report-only unless follow-up filing is approved."
argument-hint: "[-n COUNT] [--deep-max M] [--deep-model sonnet|opus|fable] [--refresh] [--sample K] [--sweep] [--sweep-max N] [--repo owner/name]"
allowed-tools: Bash, Read, Task, AskUserQuestion, Skill
---

# /analyze-bugs

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

Dev-only workflow for verifying whether recent `[BUG]` issues were fixed in `main`. The workflow is report-only by default. It files at most one combined follow-up issue, and only after explicit approval.

## Flags

Parse `$ARGUMENTS` and forward only these flags:

- `-n COUNT`, `--count COUNT`: number of newest issues whose title is `[BUG]` after stripping known lifecycle prefixes and matching case-insensitively. Default: `200`.
- `--deep-max M`: maximum deep verifier tasks. Default: `30`.
- `--deep-model sonnet|opus|fable`: model alias for deep checks. Default: `sonnet`.
- `--refresh`: ignore matching ledger skips for this run.
- `--sample K`: deterministic calibration sample from triage clear or likely rows. Default: `3`. Pass `--sample 0` to disable calibration.
- `--sweep`: inspect eligible first-parent `main` merges with the static finder/refuter funnel.
- `--sweep-max N`: cap selected sweep merges. Default: `20`; requires `--sweep` and must be a positive integer.
- `--repo OWNER/REPO`: explicit GitHub repo. Default: `gh repo view`.

Parse `--sweep` and `--sweep-max` before prefetch. Reject `--sweep-max` without `--sweep`, invalid or non-positive values, and unknown flags before spending Task tokens. Forward only the legacy prefetch flags (`-n` / `--count`, `--repo`, and their existing prefetch controls); never forward sweep controls to `analyze-bugs prefetch`.

## Preflight

Require a clean checkout on `main`, synced with `origin/main`, before any deep dispatch. Fail loudly when any check fails.

```bash
git fetch origin main
test "$(git rev-parse --abbrev-ref HEAD)" = main
test -z "$(git status --porcelain)"
test "$(git rev-parse main)" = "$(git rev-parse origin/main)"
```

## Stage 0: Prefetch

Run the Python coordinator from the repository root. Use `$PWD` paths.

```bash
PREFETCH_OUT=$(python3 "$PWD/python/cli.py" analyze-bugs prefetch [forwarded flags])
```

Parse only whole-line `KEY=value` records from stdout:

- `RUN_DIR`
- `MANIFEST_PATH`
- `LEDGER_PATH`
- `TRIAGE_BATCH_PATHS`
- `DEEP_QUEUE_PATH`
- `EVIDENCE_REF`
- `BUGS_REQUESTED`
- `BUGS_SELECTED`

Abort if any required path key is missing. Do not guess an active run.

Each bundle records changed symbols from the fix diff and a `Consumers of changed
symbols` section. Consumers outside the touched files are tagged
`cross-language` when they are shell, skill Markdown, or hook surfaces. The
later-history and revert scans use the touched files plus successfully resolved
consumer paths; `touched_files` remains the analytics-only fix-file set.

Every required diff, consumer, later-history, and revert scan has an explicit
status in the bundle. A command failure is a failure stanza, never empty
evidence; only `git grep` exit `1` means a successful no-match. Incomplete
required evidence forces `NEEDS_DEEP` and cannot produce `FIXED_CLEAR`,
`FIXED_LIKELY`, or `CONFIRMED_FIXED`, including from cached results. The
widened file set and scan status are part of `later_history_hash`, which
invalidates existing successful cache entries once; incomplete scans bypass
cached certification evidence.

## Sweep stages (only with `--sweep`)

Run these stages after prefetch and before the ledger or deep stages. Every Python fence is a fail-closed boundary: a non-zero exit stops the skill before any following Task dispatch or legacy stage. The sweep does not write `sweep-state.json` here; Stage 3 writes it only after the final report and follow-up body succeed.

### S0: Prepare

```bash
python3 "$PWD/python/cli.py" analyze-bugs sweep prepare --run-dir "$RUN_DIR" --ledger-path "$LEDGER_PATH" --sweep-max "$SWEEP_MAX" [--repo OWNER/REPO]
```

Read only the command's whole-line KVs. Print `SELECTED_COUNT`, `SKIPPED_COUNT`, the pending-frontier count, and `COVERAGE_INCOMPLETE`. Do not dispatch a finder if prepare fails.

### S1: Finder and ingest

Read the prepared bundle-path manifest. Dispatch exactly one `sweep-bug-finder` Task in finder mode for each selected bundle, passing only its bundle path and requiring strict JSONL output. Append each response, unchanged, to the fixed `$RUN_DIR/sweep-finder.jsonl`; do not synthesize rows. If there are zero selected merges, skip finder dispatch and raw capture.

Then run this fence even for zero selected merges:

```bash
python3 "$PWD/python/cli.py" analyze-bugs sweep ingest-finder --run-dir "$RUN_DIR"
```

Require successful ingest and exact selected-merge coverage before any refuter dispatch, ledger work, or deep work. Read `REFUTER_QUEUE_PATH` and `REFUTER_QUEUE_COUNT` only from this command's KVs.

### S2: Refuter and ingest

For each JSONL row in `REFUTER_QUEUE_PATH`, dispatch exactly one `sweep-bug-finder` Task in refuter mode. Pass only that queue row and the queue path; require strict JSONL output. Append each response, unchanged, to the fixed `$RUN_DIR/sweep-refuter.jsonl`. If the queue count is zero, skip refuter dispatch and raw capture.

Then run this fence even for a zero-length queue:

```bash
python3 "$PWD/python/cli.py" analyze-bugs sweep ingest-refuter --run-dir "$RUN_DIR"
```

Require successful ingest and exact queue-key coverage before continuing. Malformed JSONL, rejected rows, missing coverage, Task failure, or a stale tip aborts without changing sweep state.

## Stage 1: Ledger and triage queue

Compute pending triage batches and the first deep queue from explicit paths.

```bash
LEDGER_OUT=$(python3 "$PWD/python/cli.py" analyze-bugs ledger \
  --run-dir "$RUN_DIR" \
  --ledger-path "$LEDGER_PATH" \
  --deep-max "$DEEP_MAX" \
  --deep-model "$DEEP_MODEL_ALIAS" \
  [--refresh] [--sample K])
```

Read `TRIAGE_BATCH_PATHS`, `DEEP_QUEUE_PATH`, `DEEP_MODEL`, and `DEEP_RATE_MODEL` from whole-line KVs. Python validates the deep-model alias before any Task spend.

For each triage batch path, launch `bug-fix-triage` with only that batch path plus instructions to read the batch file and then read each `bundle_path` listed in it. The triage batch JSONL must not include `evidence_token`.

Do not pass `MANIFEST_PATH`, manifest JSON, bundle markdown bodies, `bundle_path` lists copied from the batch, or any `evidence_token` values in the Task prompt. Do not Read manifest or bundle files during triage dispatch. Only the triage agent may obtain tokens by reading bundle files.

Save the agent JSONL output under `$RUN_DIR/triage-results-N.jsonl`. `analyze-bugs ledger --ingest-triage` rejects rows with missing or mismatched `evidence_token` values by parsing the canonical `evidence_token: <token>` line from each bundle markdown file on disk.

Ingest each triage result:

```bash
python3 "$PWD/python/cli.py" analyze-bugs ledger \
  --run-dir "$RUN_DIR" \
  --ledger-path "$LEDGER_PATH" \
  --ingest-triage "$TRIAGE_RESULT"
```

## Stage 2: Deep verification

Recompute the ledger after triage ingest so deep priority, sampling, and cap truncation reflect current evidence.

The coordinator risk-routes verified `FIXED_CLEAR` and `FIXED_LIKELY` rows to deep verification. Priority is chain-linked, chronic-zone, cross-language contract surface, then fixes adding more than 300 lines. This promotion requires verified triage evidence. The coordinator records every candidate dropped by `--deep-max` with its issue and routing reason.

```bash
LEDGER_OUT=$(python3 "$PWD/python/cli.py" analyze-bugs ledger \
  --run-dir "$RUN_DIR" \
  --ledger-path "$LEDGER_PATH" \
  --deep-max "$DEEP_MAX" \
  --deep-model "$DEEP_MODEL_ALIAS" \
  [--refresh] [--sample K])
```

If `$DEEP_QUEUE_PATH` is non-empty, launch `bug-fix-verifier` with Task `model` set to the echoed `DEEP_MODEL`. Pass the explicit queue path, manifest path, run dir, and read budget. Save output under `$RUN_DIR/deep-results.jsonl`.

Ingest deep results:

```bash
python3 "$PWD/python/cli.py" analyze-bugs ledger \
  --run-dir "$RUN_DIR" \
  --ledger-path "$LEDGER_PATH" \
  --ingest-deep "$DEEP_RESULT"
```

## Stage 3: Report

Render the report from the same explicit paths. When sweep is enabled, this is the sole final rendering step: it validates and merges `sweep-validated.json` only after ledger and deep work complete.

```bash
python3 "$PWD/python/cli.py" analyze-bugs report \
  --run-dir "$RUN_DIR" \
  --manifest "$MANIFEST_PATH" \
  --ledger-path "$LEDGER_PATH"
```

Print the markdown report and the `ANALYZE_BUGS_COST_ESTIMATE=...` line. With sweep, also print `ANALYZE_BUGS_SWEEP_COST_ESTIMATE=...`, selected, skipped, and pending-frontier counts, plus an incomplete-coverage notice when capped work remains. The estimate is marked estimated when Task token usage is unavailable.

The Issues table names the final evidence tier as `MECH`, `TRIAGE`, or `DEEP`. The report then shows chronic zones, directional fix chains, baseline-extending fixes, and the delta since the prior valid run snapshot. A validated sweep adds a `Sweep candidates` table and can create or extend the same follow-up body even when legacy follow-ups are empty. A verified issue has a final non-pending verdict from one of those evidence tiers. Sample calibration always prints the sample size, sampled failures, and triage false-pass rate. When chronic zones exist, the report suggests `/learn-from-bugs` scoped to those zones.

On a successful sweep report, `sweep-state.json` sits beside `ledger.jsonl`. It records the pinned discovery watermark and every unselected eligible SHA as a pending frontier, so capped work is retried rather than silently omitted. A first sweep covers only the prior 48 hours.

Static sweep can find contract breaks, wrong field or key names, and logic errors. It cannot establish that `main` is bug-free or detect timing failures, vendor CLI drift, GitHub-state failures, or other runtime-only defects.

## Follow-up filing gate

If the report names a follow-up body file, ask for approval before filing. On rejection, stop after printing the report. Do not call `gh issue create` directly.

On approval, invoke `/issue` via the Skill tool once with that generated body file. Do not pass `--no-dedup`.
