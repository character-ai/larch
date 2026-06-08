# scripts/cleanup-implement-logs.py

**Purpose**: Retroactive cleanup of committed `larch-logs/implement/` run dirs.
Applies the Phase 1 publish-time rules (PR #3722 / issue #3708) to all
historical run dirs so the working-tree artifact set matches what new runs
will produce going forward.

**Callers**: One-shot operator command — not called by any CI job or runtime
script. Run once after Phase 1 merges; commit the resulting working-tree diff
as a dedicated log-only PR (see `docs/run-logs.md` bulk-edit guidance).

## Actions

| # | Action | Guard |
|---|--------|-------|
| 1 | Delete `round-N/dyn-*-prompt.md` | None needed; always redundant |
| 2 | Delete `round-N/aggregator-output.txt` | Only when `cmp -s` with `findings.md` passes |
| 3 | Delete `scout-round*-manifest.json.raw` | None needed; cooked `.json` is canonical |
| 4 | Delete refresh sidecars (`token-report-refresh.json`, `timing-report-refresh.json`, `session-transcript-refresh.*`) | None needed |
| 5 | Delete `cursor-specialist-*-output-{phase*,retry}.txt` | Keep `*-ns-retry*` |
| 6 | Upgrade `session-transcript.jsonl` v1 → v2 | Skip when header `v >= 2` |
| 7 | Consolidate `breadcrumbs/larch-quiet-*.log` → `breadcrumbs/quiet.log` | Skip when `quiet.log` already exists |
| 8 | Drop `body` field from `code-review-tally.json` | Skip when `body` absent |
| 9 | Remove `python/larch-logs/` tree | Skipped when `--run-dir` is set |

For actions 1, 3, 4, 5: sibling `.meta` and `.json` sidecar files are also
deleted when present (same directory, same basename plus `.meta` / `.json`).

## v1 → v2 transcript upgrade

The v2 schema differs from v1 in two ways:

- `Edit`/`Write`/`NotebookEdit` tool_call `input` is replaced with
  `{"file_path": "...", "input_bytes": N}` (content lives in the PR diff).
- Other tool_call `input` values whose serialized size exceeds 1 KB are
  replaced with `{"elided_input_bytes": N}`.

The retroactive transform reads the already-rendered v1 JSONL, applies these
rules, and overwrites in place with the header bumped to `v: 2`.  The raw
session JSONL (not committed) is not needed for this transform.

## Usage

```sh
# Dry-run (safe, shows counts only)
python3 scripts/cleanup-implement-logs.py

# Execute
python3 scripts/cleanup-implement-logs.py --execute

# Spot-check a single run dir first
python3 scripts/cleanup-implement-logs.py --run-dir larch-logs/implement/<UUID> --execute
```

## Edit-in-sync

Changes to the Phase 1 publish rules in `scripts/lib-larch-log.sh` or
`python/run_logs.py` that add new file-type denials should be mirrored here
as a new action so the retroactive cleanup stays aligned.

## Regression harness

No automated harness — the script is a one-shot cleanup tool.
Verification steps are in the issue body (#3709):

- `/report-tokens --skill=implement` scans clean after the PR.
- `audit-scan-run.sh --skill implement` passes on a sample of surviving dirs.
- `bash scripts/relevant-checks.sh` passes.
- Spot-check one multi-round run: chain intact, re-rendered transcript parses.
