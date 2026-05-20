# Larch Run Logs

On a default `/implement --merge` run, a directory of structured log files is committed alongside the PR. These committed files are the single source of truth for full run content — voting tallies, rejected findings, version-bump reasoning, OOS observations, execution issues, run statistics, token/timing reports, and the session transcript. The tracking issue and PR body carry only slim projections.

Exceptions: `--design-only --no-issues` and `repo_unavailable=true` produce no committed log at all (`$IMPLEMENT_TMPDIR/execution-issues.md` is the only audit trail and is removed at cleanup). `--design-only` runs with a tracking issue can still commit partial `larch-logs/implement/<RUN_ID>/` directories, but they stop before Step 7a and therefore omit Step-7a-only batches such as `session-transcript.jsonl`. Fork dry-run mode (`--forked`) does not create a tracking issue. In all cases, session-derived content in `larch-logs/` passes through secrets and tmpdir-path redaction, but redaction is best-effort — operators should avoid pasting sensitive content into `/implement` prompts.

## Directory structure

```
larch-logs/
  implement/
    <RUN_ID>/
      manifest.json
      plan-goals-test.md
      parent-issue.md
      pre-review-head.txt
      pre-review-untracked.txt
      codex-impl-transcript.txt
      codex-impl-transcript-prompt.txt
      codex-commit-message.txt
      codex-impl-manifest-raw.json
      plan-review-tally.json
      code-review-tally.json
      review-findings-full.jsonl
      version-bump-reasoning.md
      oos-issues.ndjson
      run-statistics.md
      token-report.json
      timing-report.json
      execution-issues.ndjson
      session-transcript.jsonl
      round-<N>/
        findings.md
        accepted-findings.md
        rejected-findings.md
        review-round-summary.md
        review-summary.json
        voting-tally.md
        *-output.txt
        *-output.txt.meta
        *-output.txt.json
  review/
    <RUN_ID>/
      manifest.json
      review-context.md
      review-panel-manifest.ndjson
      review-findings.ndjson
      review-tally.md
      review-scout-manifest.json
      review-round-summary.md
```

`<RUN_ID>` is the UUID assigned at the start of each `/implement` session. Batch payload files under a run directory are redacted for secrets and tmpdir paths before commit. `manifest.json` schema version 2 keeps `operator_cwd` / `operator_repo_root` only as stable redacted placeholders (`"<OPERATOR_CWD>"`, `"<REPO_ROOT>"`) so committed logs preserve schema shape without exposing operator-local absolute paths.

`round-<N>/` directories are written by `larch-log.sh write-round` during
`/implement` code review. They preserve the per-round reviewer and voter
diagnostic artifacts that are otherwise lost with `$IMPLEMENT_TMPDIR` cleanup.
Only registered artifact names are copied. `.meta` files have `CMD_JSON=...`
removed when `CMD_JSON=` is the first non-whitespace token, included
`*-output.txt.json` / `*-output-*.txt.json` sidecars have their top-level
`.result` field removed, and all copied files still pass through the normal
tmpdir and secrets redaction. This trimming is specific to the committed round
artifacts; the session tmpdir may still hold raw sidecars for in-run retries.
If JSON trimming fails, `write-round` fails closed instead of copying the raw
sidecar into `larch-logs/`.

`/review` uses the same `larch-logs/<skill>/<RUN_ID>/` layout when a run ID is provided. Review phase names are encoded in flat batch slugs, not subdirectories: `review-context` for gathered context, `review-panel-manifest` for launched slots, `review-findings` for collected finding records, `review-tally` for vote results, `review-scout-manifest` for dynamic-reviewer scout status, and `review-round-summary` for the human-readable round summary.

## manifest.json

Created by `scripts/larch-log.sh init` at Step 0.5 when the tracking issue is first resolved. Updated by `larch-log.sh manifest` calls throughout the run. Contains: skill name, run ID, operator CWD, operator repo root, tracking-issue number, PR number (once created), the run status last recorded in that manifest snapshot, and optional routing flags such as `coder_fallback=true` when omitted-`--coder` routing fell past Codex. Authoritative contract: `scripts/larch-log.md`.

For current `/implement` runs, the committed manifest is normally an `"in-progress"` snapshot because the post-merge `"done"` update happens inside `$IMPLEMENT_TMPDIR` after the last log commit window. That is not an absolute invariant: older committed runs, tests, or manual/status-update flows can still produce committed manifests with `"done"` or other statuses. To assess completion, read `status` as one signal and correlate it with PR merge state plus the surrounding run-log artifacts.

## Batch files

### plan-goals-test.md

**Mode**: replace (one file per run). **Written**: Step 1, after the design plan is finalized.

Contains the implementation plan: goal statement, files to modify, approach, edge cases, and testing strategy. In normal mode the content comes from `/design`'s exported `plan.txt`; in quick mode it is the inline plan produced by the orchestrator.

### parent-issue.md

**Mode**: replace. **Written**: Step 1 and refreshed at the pre-bump flush when
present.

Tracking-issue sentinel with the adopted or created issue number and run ID.
This is the session-scope idempotency source for tracking issue recovery.

### pre-review-head.txt and pre-review-untracked.txt

**Mode**: replace. **Written**: Step 5 round 1 initialization.

`pre-review-head.txt` records the HEAD SHA before review starts.
`pre-review-untracked.txt` records the untracked-file snapshot used by the
review-change checks.

### codex-impl-transcript.txt and related Codex setup files

**Mode**: replace. **Written**: Step 7a pre-bump flush when present.

`codex-impl-transcript.txt` is the external implementer transcript,
`codex-impl-transcript-prompt.txt` is the prompt sidecar,
`codex-commit-message.txt` is the redacted commit message consumed by the
dispatcher, and `codex-impl-manifest-raw.json` is the pre-sanitized manifest
copy retained for diagnosis. These files are optional because non-Codex or
bailout paths may not produce them.

### plan-review-tally.json

**Mode**: replace (JSON object). **Written**: Step 1 tail, after the plan-review voting tally is exported.

One JSON object per `/implement` session. The tally envelope shape is shared with
`code-review-tally.json`: `schema_version`, `phase`, `batch`, `mode`, `rounds`,
`accepted_count`, `rejected_count`, `exonerated_count`, `neutral_count`, and
`body`. For plan review the extra counters are normally `0`. The `body` contains
the plan-review voting outcome (accepted count, rejected count, round summaries)
plus any rejected plan-review findings under a `## Rejected Plan Review Findings`
sub-header. In quick mode the body contains `"Quick mode — no plan review voting."`.

### code-review-tally.json

**Mode**: replace (JSON object). **Written**: Step 5, after `/review` returns (normal mode) or the quick-mode review loop completes.

One JSON object per `/implement` session with the same tally envelope fields as
`plan-review-tally.json`. `exonerated_count` covers findings voted `exonerated`
(valid but not worth implementing in this PR), `neutral_count` covers tie votes
with no clear consensus (finding-level result from `classify_result()`), and
`rejected_count` counts only findings where the panel voted strictly `rejected`
(voted down). The body contains the code-review voting outcome and a round-by-round
summary. It also includes rejected code-review findings under a
`## Rejected Code Review Findings` sub-header — only findings with outcome
`rejected` appear here. Exonerated and neutral findings are counted in the envelope
but not listed separately.

**Note**: `neutral_count` covers finding-level tied votes and is distinct from
`JUDGE_ERROR`, which is a per-judge-per-finding state (the parser fallback when a
voter's ballot did not contain a parseable vote line for that finding). `JUDGE_ERROR`
appears in the per-finding vote breakdown table under the `JERR` column header but
is not separately enumerated in the tally envelope counters.

### review-findings-full.jsonl

**Mode**: replace (line-delimited JSON). **Written**: Step 5, immediately after the `code-review-tally` batch.

Per-finding payloads for plan-review accepted, plan-review rejected, and code-review entries. One JSON object per line with keys `id`, `issue_number`, `phase` (`plan-review` | `code-review`), `outcome` (`accepted` | `rejected` | `out_of_scope`), `reviewer`, `round_num` (empty outside numbered review rounds), `category` (best-effort, extracted from a leading `## <cat>: ...` body line — may be empty), and `prose_body` (redacted). See `scripts/compose-review-findings.md` for the producer contract.

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

**Mode**: append (NDJSON records). **Written**: Step 2 (Q/A entries, progressive), Step 7a (pre-bump flush of `execution-issues.md`), later external-implementer / pre-push refreshes when new entries are added after Step 7a, and Step 18's safety net when the normal flush path was missed.

Log of noteworthy events during the run, grouped by category: `Pre-existing Code Issues`, `Tool Failures`, `Permission Prompts`, `External Reviewer Issues`, `CI Issues`, `Warnings`, and `Q/A`. Entries from Step 2's Q/A loop are appended progressively; the main flush happens at Step 7a before the bump so the audit log is part of the same PR tree that CI validates. If later steps append new execution issues, the shared external-implementer / pre-push flush paths append only the unflushed tail, and Step 18 remains the best-effort fallback. This batch is the durable audit trail for follow-up work and operational events.

### session-transcript.jsonl

**Mode**: replace. **Written**: Step 7a tail (pre-bump log flush) for runs that reach Step 7a. `--design-only` and other pre-Step-7a bailout paths do not write this batch. The transcript is truncated at the pre-bump boundary — Steps 8+ (version bump, PR creation, CI, merge, cleanup) are not included. On each CI retry `scripts/refresh-run-logs.sh` (Triggers A-C in `ship-pr.sh`) re-captures and refreshes the batch before each push, so the final merged PR carries the most up-to-date transcript available before merge.

A filtered, machine-readable rendering of the Claude Code session, produced by `scripts/render-session-transcript.py` from the raw session JSONL. The first line is a `{"v": 1, "source_basename": ..., "turns": N}` header; subsequent lines are per-turn objects with a `blocks` array. Blocks carry user-typed slash commands and text, assistant prose, `tool_call` entries with full input objects, and `tool_result` entries — full body when the result reported an error or warning (`is_error: true`, Bash `^Exit code [1-9]` / `^Error:`, or `warning:`), otherwise collapsed to an `elided_bytes` count. Assistant `thinking` blocks are kept only when at least one `tool_use` in the same turn produced an errored result. Harness-injected SKILL.md expansions, attachments, and housekeeping events are dropped. Redacted for tmpdir paths and secrets before commit. The `session-transcript` capture records `SESSION_TRANSCRIPT_STATUS` in the execution-issues `Warnings` section for every capture outcome, including refresh/deferred-commit `captured` outcomes and `render-failed` / `render-empty` when the renderer cannot produce a usable output (the run continues; nothing is committed). For runs that reach Step 7a, `session-transcript.jsonl` is part of the required-file completeness manifest; pre-Step-7a partial directories remain excluded by the verifier's step reachability rules. The recovery warning records only the discovered transcript basename, not the full operator-local path. See `scripts/render-session-transcript.md` for the complete schema.

### round-<N>/

**Mode**: directory replace-by-file. **Written**: first at the end of each
`review-core.sh` round during `/implement` Step 5, then optionally refreshed
later in the same round after the coder finishes if `review-and-fix.sh`
produces additional registered artifacts (for example coder-side files).

Contains a curated set of per-round artifacts: the aggregate `findings.md`,
accepted / rejected findings, OOS review markdown, voting tally and summary,
per-voter outputs (the byte-identical vote prompts and the raw per-specialist
reviewer outputs are excluded by `round_artifact_included` in
`scripts/larch-log.sh` because the aggregates already cover their content),
panel manifest, code-voter slots, collector/tally env files, coder dispatch
state (env, prompt, tool log, wrapper logs), and any later registered coder
artifacts. The `review-core.sh` flush is the first
snapshot for the round; `review-and-fix.sh` may run one more `write-round`
after coder application so the committed round directory reflects the full
round state before the later shared log-commit paths copy it into
`larch-logs/implement/<RUN_ID>/round-<N>/` in the repo. There is no per-round
commit.

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

Written in two phases for full implementation runs: first during Step 8+
PR creation, where `ship-pr.sh` renders and commits `final-summary.md` with
placeholder PR fields before `create-pr.sh` pushes the branch, and later
refreshed during Step 18 terminal cleanup. The tracking-issue comment may also
be refreshed immediately after PR creation with the live URL, without a second
log commit. For `--design-only` runs, Step 8+ and PR creation are skipped, but
the terminal cleanup path still runs and may refresh the tracking summary with
`PR: N/A`.

Content: final run status (`STALL_TRACKING` value), PR URL, and log directory path. The committed `final-summary.md` in the PR tree may carry placeholder `PR: N/A`; the tracking-issue comment is the canonical live source for the PR URL.

## Authoritative sources

- `scripts/larch-log.md` — `larch-log.sh` verb contracts, log-root resolution, redaction rules
- `scripts/larch-log-batches.md` — canonical batch slug table (extension, mode, sanitizer)
- `skills/implement/references/summary-comment-template.md` — marker literals and comment contracts
