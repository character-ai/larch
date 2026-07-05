---
name: gc-run-logs
description: "Use when slimming or deleting aged larch run-log directories to cap repo growth. Applies age retention and creates a log-only PR for operator merge."
allowed-tools: Bash
---

# gc-run-logs

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Age-based retention policy for committed larch run-log directories.

Run dirs in `larch-logs/design/`, `larch-logs/implement/`, and `larch-logs/review/` whose run date is older than the threshold are either **slimmed** (round-level forensic files removed, consumer-core keep set preserved) or **deleted** (entire dir removed; content remains in git history).

**Consumer-core keep set** (preserved by slim; `--delete` removes everything):

- All skills: `manifest.json`, `final-summary.md`, `difficulty-rating.json`
- implement: `token-report.json`, `timing-report.json`, `review-findings-full.jsonl`, `execution-issues.ndjson`, `run-statistics.md`
- design: `token-report-final.json`, `timing-report-final.json`, `run-params.json`, `plan.txt`

This preserves `/report-tokens` cost-trend history indefinitely while shedding round-level forensic detail for aged runs.

## NEVER

- Never run GC when the working tree is dirty or an active `/implement`/`/design` session is detected — the script refuses automatically.
- Never invent the PR URL, DIRS_SLIMMED, or DIRS_DELETED counts if the script exits non-zero or omits any required stdout key.
- Never merge the PR on the operator's behalf — the log-only PR is operator-merge only.

## Flags

- `--older-than DAYS` (optional, default `90`): process run dirs whose run date is older than DAYS. Run date resolves from `manifest.json::started_at`; falls back to the dir's first-commit date; dirs with no resolvable date are skipped with a warning.
- `--delete` (optional, off by default): fully delete qualifying run dirs instead of slimming. Content remains recoverable via `git show <sha>:<path>`.
- `--dry-run` (optional): print the per-dir plan (slim/delete/skip + qualifying count) without making any changes or creating a PR.

## Guards (applied per dir)

- Dirs containing `pause-state.txt` are skipped (resumable design sessions).
- Dirs with a `gc-slimmed` marker are skipped (already processed).
- Dirs with no resolvable run date are skipped with a warning.

<!-- step:1 — Run gc-run-logs -->

Script contract: `python/cli.py gc-run-logs run`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" gc-run-logs run <flags>
```

Parse `STATUS`, `DIRS_SCANNED`, `DIRS_QUALIFYING`, `DIRS_SLIMMED`, `DIRS_DELETED`, `DIRS_SKIPPED`, `BYTES_FREED`, `DRY_RUN`, and `PR_URL` from stdout and relay them to the user.

<!-- step:2 — Verify and report -->

On `STATUS=ok`:

- If `DRY_RUN=true`: report the qualifying-dir count and the per-dir plan. No changes were made.
- If `DRY_RUN=false` and `DIRS_QUALIFYING=0`: report that no dirs qualify and nothing was done.
- If `DRY_RUN=false` and a PR was created: report `PR_URL`, dir counts, and approximate `BYTES_FREED`. Remind the operator to review and merge.

On `STATUS=error` or non-zero exit: surface the error verbatim; do not fabricate counts or a PR URL.
