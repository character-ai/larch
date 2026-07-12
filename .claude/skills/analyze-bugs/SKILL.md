---
name: analyze-bugs
description: "Use when auditing recent [BUG] issues with a low-cost cached verification funnel. Dev-only; report-only unless follow-up filing is approved."
argument-hint: "[-n COUNT] [--deep-max M] [--deep-model sonnet|opus|fable] [--refresh] [--sample K] [--repo owner/name]"
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
- `--repo OWNER/REPO`: explicit GitHub repo. Default: `gh repo view`.

Reject unknown flags before spending Task tokens.

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

Render the report from the same explicit paths:

```bash
python3 "$PWD/python/cli.py" analyze-bugs report \
  --run-dir "$RUN_DIR" \
  --manifest "$MANIFEST_PATH" \
  --ledger-path "$LEDGER_PATH"
```

Print the markdown report and the `ANALYZE_BUGS_COST_ESTIMATE=...` line. The estimate is marked estimated when Task token usage is unavailable.

The Issues table names the final evidence tier as `MECH`, `TRIAGE`, or `DEEP`. The report then shows chronic zones, directional fix chains, baseline-extending fixes, and the delta since the prior valid run snapshot. A verified issue has a final non-pending verdict from one of those evidence tiers. Sample calibration always prints the sample size, sampled failures, and triage false-pass rate. When chronic zones exist, the report suggests `/learn-from-bugs` scoped to those zones.

## Follow-up filing gate

If the report names a follow-up body file, ask for approval before filing. On rejection, stop after printing the report. Do not call `gh issue create` directly.

On approval, invoke `/issue` via the Skill tool once with that generated body file.
