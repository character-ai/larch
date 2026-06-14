## Goal
Implement issue #4352: [IMPLEMENTING] [BUG] (URGENT) design-log-publish fails when plan-review revise/ contains .token-record or .stderr-tail sidecars.

## Implementation Plan
## Context

`design-log-publish.sh` walks every file under `$DESIGN_TMPDIR/plan-review/round-*/revise/` and calls `python/cli.py plan-review round-revise-artifact-excluded --name <basename>` for each one. If a file is neither in the included list (always empty) nor the excluded list, the script emits `design-log-publish: unexpected file under plan-review (see python/plan_review.py): <rel>` and exits `PUBLISH_OK=false`.

## Root cause

`round_revise_artifact_excluded` in `python/plan_review.py` (line ~1226) has a hard-coded tuple of known-safe suffixes to exclude. Two suffixes written by the Cursor and Codex autofix launchers during `plan revise-waterfall` are **not** in the list:

- **`.token-record`** — written by `python/agents.py` alongside `cursor-output.txt` during Cursor autofix runs (see `agents.py` line ~2818). Appears as `cursor-output.txt.token-record` in every `round-N/revise/` directory where Cursor ran autofix.
- **`.stderr-tail`** — written by `python/agents.py` and `python/checks.py` when a Codex autofix agent fails (see `agents.py` line ~1262, `checks.py` line ~953). Appears as `codex-output.txt.stderr-tail`.

Both suffixes are recognized elsewhere in the codebase (e.g. `design-log-publish.md` line 48-50 mentions `.stderr-tail` as a sidecar to exclude at other levels), but they were never added to the `revise/` directory allowlist in `plan_review.py`.

## Reproduction

Run `/design` on any issue that triggers Cursor autofix in plan review (i.e. the autofix validator returns defects and Cursor runs as the first available vendor). After the run completes, attempt `design-log-publish.sh`. The script fails on the first `.token-record` file in any `round-*/revise/` directory. Every round that ran Cursor autofix produces a `.token-record` file; every round where Codex autofix fails produces a `.stderr-tail` file.

Observed on run `8B916465-DE73-42D4-87BF-9B5DFE820EC2` (issue #4340) where all 5 review rounds produced `cursor-output.txt.token-record`, and rounds 2, 4, 5 produced `codex-output.txt.stderr-tail`.

## Suggested fix

In `python/plan_review.py`, extend the `suffixes` tuple in `round_revise_artifact_excluded` (line ~1242):

```python
        ".stderr",
        ".token-record",   # cursor/codex autofix token usage sidecar
        ".stderr-tail",    # codex autofix failure stderr tail
```

Same edit needed in the plugin cache copy at `$CLAUDE_PLUGIN_ROOT/python/plan_review.py` until the plugin is refreshed.

Also add a regression test to `python/test_plan_review.py` asserting that `round_revise_artifact_excluded("cursor-output.txt.token-record")` and `round_revise_artifact_excluded("codex-output.txt.stderr-tail")` return `True`.

## Affected files

- `python/plan_review.py` — `round_revise_artifact_excluded` function (one-line fix each for two suffixes)
- `python/test_plan_review.py` — add two regression assertions

## Workaround

Apply the fix to the local `python/plan_review.py` before retrying `design-log-publish.sh`. The `.token-record` and `.stderr-tail` files in `round-*/revise/` are already ingested into the token ledger and failure-diagnostics systems; excluding them from the published log bundle does not lose information.

## Test plan
(no test plan section in plan-file)
