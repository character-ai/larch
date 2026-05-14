# Larch Run Logs

On a default `/implement --merge` run, a directory of structured log files is committed alongside the PR. These committed files are the single source of truth for full run content — voting tallies, rejected findings, version-bump reasoning, OOS observations, execution issues, run statistics, token/timing reports, and the session transcript. The tracking issue and PR body carry only slim projections.

Exceptions: `--design-only --no-issues` and `repo_unavailable=true` produce no committed log at all (`$IMPLEMENT_TMPDIR/execution-issues.md` is the only audit trail and is removed at cleanup). Fork dry-run mode (`--forked`) does not create a tracking issue. In all cases, session-derived content in `larch-logs/` passes through secrets and tmpdir-path redaction, but redaction is best-effort — operators should avoid pasting sensitive content into `/implement` prompts.

## Directory structure

```
larch-logs/
  implement/
    <RUN_ID>/
      manifest.json
      plan-goals-test.md
      plan-review-tally.json
      code-review-tally.json
      review-findings-full.md
      version-bump-reasoning.md
      oos-issues.ndjson
      run-statistics.md
      token-report.json
      timing-report.json
      execution-issues.ndjson
      session-transcript.jsonl
  review/
    <RUN_ID>/
      manifest.json
      review-context.md
      review-panel-manifest.ndjson
      review-findings.ndjson
      review-tally.md
      review-round-summary.md
```

`<RUN_ID>` is the UUID assigned at the start of each `/implement` session. Batch payload files under a run directory are redacted for secrets and tmpdir paths before commit. `manifest.json` schema version 2 records `operator_cwd` and `operator_repo_root` as local absolute paths for provenance; those fields are JSON-escaped but not path-redacted.

`/review` uses the same `larch-logs/<skill>/<RUN_ID>/` layout when a run ID is provided. Review phase names are encoded in flat batch slugs, not subdirectories: `review-context` for gathered context, `review-panel-manifest` for launched slots, `review-findings` for collected finding records, `review-tally` for vote results, and `review-round-summary` for the human-readable round summary.

## manifest.json

Created by `scripts/larch-log.sh init` at Step 0.5 when the tracking issue is first resolved. Updated by `larch-log.sh manifest` calls throughout the run. Contains: skill name, run ID, operator CWD, operator repo root, tracking-issue number, PR number (once created), final run status, and optional routing flags such as `coder_fallback=true` when omitted-`--coder` routing fell past Codex. Authoritative contract: `scripts/larch-log.md`.

## Batch files

### plan-goals-test.md

**Mode**: replace (one file per run). **Written**: Step 1, after the design plan is finalized.

Contains the implementation plan: goal statement, files to modify, approach, edge cases, and testing strategy. In normal mode the content comes from `/design`'s exported `plan.txt`; in quick mode it is the inline plan produced by the orchestrator.

### plan-review-tally.json

**Mode**: replace (JSON object). **Written**: Step 1 tail, after the plan-review voting tally is exported.

One JSON object per `/implement` session. The canonical fields are
`schema_version`, `phase`, `batch`, `mode`, `rounds`, `accepted_count`,
`rejected_count`, and `body`. The `body` contains the plan-review voting outcome
(accepted count, rejected count, round summaries) plus any rejected plan-review
findings under a `## Rejected Plan Review Findings` sub-header. In quick mode
the body contains `"Quick mode — no plan review voting."`.

### code-review-tally.json

**Mode**: replace (JSON object). **Written**: Step 5, after `/review` returns (normal mode) or the quick-mode review loop completes.

One JSON object per `/implement` session with the same tally envelope fields as
`plan-review-tally.json`. The body contains the code-review voting outcome and
a round-by-round summary. It also includes rejected code-review findings under a
`## Rejected Code Review Findings` sub-header — making this the load-bearing
source for rejected findings (the terminal session transcript only prints a
breadcrumb, not the full content).

### review-findings-full.md

**Mode**: replace (markdown sections). **Written**: Step 5, immediately after the `code-review-tally` batch.

Per-finding payloads for plan-review accepted, plan-review rejected, and code-review rejected entries. Each section heading carries finding id, reviewer, phase, and outcome, followed by the redacted prose body. Accepted code-review findings are not yet captured here; `scripts/compose-review-findings.sh` only reads plan-review and code-review rejection artifacts, not the accepted-code-review path.

### version-bump-reasoning.md

**Mode**: replace. **Written**: Step 8, after `ship-pr.sh` completes the version-bump phase.

Markdown explanation of the version bump classification: which bump type was chosen (PATCH / MINOR / MAJOR), which changed files drove the decision, and the reasoning applied. Useful for auditing unexpected version jumps.

### oos-issues.ndjson

**Mode**: append (NDJSON records). **Written**: Step 9a.1, after out-of-scope issue filing.

Two sub-blocks per record: accepted OOS observations that were filed as GitHub issues (each entry includes the filed issue URL), and rejected / out-of-scope observations that were voted down or not filed (each entry includes the rejection reason). Security findings are never filed via this path.

### run-statistics.md

**Mode**: replace. **Written**: Step 9a.1 alongside `oos-issues`.

Summary statistics for the run: number of accepted and rejected OOS items, filed-issue URLs, round counts, and other aggregate metrics.

### token-report.json

**Mode**: replace. **Written**: Step 7a tail (pre-bump log flush) and refreshed at Step 9a.1. Each CI retry in the Rebase + Re-bump Sub-procedure also refreshes the batch so the merged PR carries the most recent data.

Structured per-step Claude and external-vendor token usage for the session. The pre-bump flush captures cost up through implementation and review.

### timing-report.json

**Mode**: replace. **Written**: same lifecycle as `token-report.json`.

Structured per-step elapsed-time data for the session, measured from the timing ledger marks at each step entry. Useful for identifying slow steps (e.g., long Codex spawns, extended CI waits).

### execution-issues.ndjson

**Mode**: append (NDJSON records). **Written**: Step 2 (Q/A entries, progressive), Step 11 (final flush of `execution-issues.md`).

Log of noteworthy events during the run, grouped by category: `Pre-existing Code Issues`, `Tool Failures`, `Permission Prompts`, `External Reviewer Issues`, `CI Issues`, `Warnings`, and `Q/A`. Entries from Step 2's Q/A loop are appended progressively; all remaining entries from `$IMPLEMENT_TMPDIR/execution-issues.md` are flushed at Step 11 after CI passes. This batch is the durable audit trail for follow-up work and operational events.

### session-transcript.jsonl

**Mode**: replace. **Written**: Step 18, terminal cleanup.

The redacted Claude Code session transcript (`.jsonl` format) captured for post-hoc auditability. Redacted for tmpdir paths and secrets. Allows replaying the full session reasoning, tool calls, and assistant turns after the run completes. Step 18 records `SESSION_TRANSCRIPT_STATUS` in the execution-issues `Warnings` section for every capture outcome.

## Tracking issue comments

The tracking issue for each run carries four slim marker-keyed summary comments maintained by `/implement` as the run progresses. These are projections only — their content points at the committed `larch-logs/` files rather than embedding bulky payloads inline, with one exception: `larch:diagrams` embeds Mermaid diagram bodies directly (Architecture Diagram + Code Flow Diagram) rather than pointing at a batch file.

### `larch:metadata`

Written at Step 0.5 when the tracking issue is adopted or created.

Content: run ID, log directory path (`larch-logs/implement/<RUN_ID>/`), agent (implementer coder), and larch plugin version.

### `larch:plan`

Written at Step 1 tail after the plan is finalized.

Content: a slim pointer to `larch-logs/implement/<RUN_ID>/plan-goals-test.md` plus the current plan-review tally status (voting outcome or quick-mode note).

### `larch:diagrams`

Written at Step 7a for full implementation runs. For `--design-only` runs with a tracking issue, this comment is posted at Step 1 tail alongside `larch:plan` (implementation steps including 7a are skipped).

Content: the Architecture Diagram (from `/design`) and Code Flow Diagram (generated at Step 7a from the committed implementation diff), both embedded as Mermaid fences. Diagrams are embedded directly in this comment rather than written as a larch-log batch.

### `larch:final-summary`

Written at Step 18 during terminal cleanup.

Content: final run status (`STALL_TRACKING` value), PR URL, and log directory path.

## Authoritative sources

- `scripts/larch-log.md` — `larch-log.sh` verb contracts, log-root resolution, redaction rules
- `scripts/larch-log-batches.md` — canonical batch slug table (extension, mode, sanitizer)
- `skills/implement/references/summary-comment-template.md` — marker literals and comment contracts
