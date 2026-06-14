# Larch Run Logs

On a default `/implement --merge` run, a directory of structured log files is committed alongside the PR. These committed files are the single source of truth for full run content — voting tallies, rejected findings, OOS observations, execution issues, run statistics, token/timing reports, and the session transcript. The tracking issue and PR body carry only slim projections. **Phase 1 (#3364):** `/implement` no longer writes `version-bump-reasoning.md` on the ship path; use `/release` or manual bump flows when version reasoning must be committed.

Exceptions: `repo_unavailable=true` produces no committed log at all (`$IMPLEMENT_TMPDIR/execution-issues.md` is the only audit trail and is removed at cleanup). Fork dry-run mode (`--forked`) does not create a tracking issue. In all cases, session-derived content in `larch-logs/` passes through secrets and tmpdir-path redaction, but redaction is best-effort — operators should avoid pasting sensitive content into `/implement` prompts.

## Plan scope and committed logs

Issue-anchored `larch:plan` blocks list the files that a `/implement` run is expected to touch. Retroactive maintenance across many runs under `larch-logs/design/` or `larch-logs/implement/` — for example URL normalization, typo fixes, or redaction-policy updates in historical committed logs — is not implied by plans that only target the **runtime plugin authority surface** defined in `AGENTS.md` (`skills/`, `agents/`, `hooks/`, `scripts/`, `.claude-plugin/`). Everything else in the repo (including `docs/`, `larch-logs/`, CI config, and `.claude/skills/`) is supplementary unless the tracking issue's `larch:plan` file list names it. Prefer a log-only PR for bulk `larch-logs/` edits so plan-to-diff review stays traceable; if bulk log edits ship on the same branch as changes under that runtime surface (or other paths not already listed in the plan), disclose the split in the PR title or body so reviewers can separate log churn from substantive work, and extend the issue `larch:plan` file list (or split the PR) when you add normative doc edits such as this file alongside unrelated implementation work.

## Directory structure

```
larch-logs/
  design/
    <RUN_ID>/
      manifest.json
      (design session artifacts: depth-1 files from `$DESIGN_TMPDIR` plus `render-cache/` subtree, trimmed and redacted per `scripts/design-log-publish.md`; `composed-plan.diff` is a unified diff of `composed-plan.md` vs final `plan.txt` — reconstruct with `patch plan.txt composed-plan.diff -o composed-plan.md`)
      plan-review/
        round-<N>/
          findings-classification.tsv
  implement/
    <RUN_ID>/
      manifest.json
      include-probe-evidence.md
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
      final-summary.md
      oos-issues.ndjson
      run-statistics.md
      vendor-failure-diagnostics.txt
      token-report.json
      timing-report.json
      execution-issues.ndjson
      session-transcript.jsonl
      breadcrumbs/
        quiet.log
      round-<N>/
        findings-classification.tsv
        rejected-findings.md
        oos-accepted-review.md
        review-round-summary.md
        review-summary.json
        voting-tally.md
        aggregator-validate.stderr / aggregator-dispatch.stderr (when the findings aggregator fails; committed under the round directory when `write-round` runs)
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
      review-findings-classification-round-<N>.tsv
```

`<RUN_ID>` is the UUID assigned at the start of each `/implement` session. Batch payload files under a run directory are redacted for secrets and tmpdir paths before commit. `manifest.json` schema version 2 keeps `operator_cwd` / `operator_repo_root` only as stable redacted placeholders (`"<OPERATOR_CWD>"`, `"<REPO_ROOT>"`) so committed logs preserve schema shape without exposing operator-local absolute paths.

### In-loop refresh sidecars

In-loop refresh sidecars (`token-report-refresh.json`, `timing-report-refresh.json`,
`session-transcript-refresh.txt`) are volatile in-loop snapshots that are NOT
committed to the run tree. The Python ship driver reads them as inputs for
re-rendering canonical batches (`token-report.ndjson`, `timing-report.ndjson`,
`session-transcript.jsonl`) but does not copy the refresh files themselves into
`larch-logs/implement/<RUN_ID>/`. Canonical reports such as `token-report.json`,
`timing-report.json`, `token-report.ndjson`, and `timing-report.ndjson` are still
committed normally.

### breadcrumbs/

The tree above shows `implement/<RUN_ID>/breadcrumbs/` as a representative
example. The committed path shape is shared across publishing skill roots, so
the same directory artifact may exist as `design/<RUN_ID>/breadcrumbs/`,
`review/<RUN_ID>/breadcrumbs/`, or `research/<RUN_ID>/breadcrumbs/` when a
publisher wires that helper for that skill. Today the landed callers are
`python/cli.py run-log commit` (`/implement`) and `scripts/design-log-publish.sh`
(`design` publish).

`breadcrumbs/` is a commit-only directory artifact, not a larch-log batch.
`python/cli.py run-log commit` and `scripts/design-log-publish.sh` invoke the
shared `larch_log_publish_breadcrumbs_shared` helper. Session-tmpdir
`breadcrumbs/` paths (`$IMPLEMENT_TMPDIR/breadcrumbs/`, `$DESIGN_TMPDIR/breadcrumbs/`,
`$REVIEW_TMPDIR/breadcrumbs/`, or `$RESEARCH_TMPDIR/breadcrumbs/`) are publication
hints only; committed publication stages quiet logs from the session root, not
live runtime streams under those directories.

Source resolution uses `LARCH_BREADCRUMB_SOURCE_DIR` when set (which must still
be under an active session tmpdir), else the log-root parent's `breadcrumbs/`.
That directory is a hint only: publication derives the session root with
`dirname` and stages matching `larch-quiet-<script>-<pid>.log` files from the
session root rather than scanning committed inputs from `breadcrumbs/` itself.
The source hint and every staged file must resolve under
`IMPLEMENT/DESIGN/REVIEW/RESEARCH_TMPDIR` via
`larch_log_breadcrumbs_under_session_tmp`; otherwise publication skips
breadcrumb staging and returns success without creating or replacing the
committed `breadcrumbs/` directory.

Per-script session-root quiet logs whose basenames match exactly
`larch-quiet-<script>-<pid>.log` are staged. Each accepted file is individually
redacted through `redact tmpdir-paths | redact secrets --streaming
--state-file <tmp>`, then all redacted content is **concatenated** into a single
`larch-logs/<skill>/<run-id>/breadcrumbs/quiet.log` with per-source header lines
`=== <basename> ===`. The individual source files are not published separately.
Quiet-log sourcing uses `dirname` of the breadcrumbs source path and runs even
when `breadcrumbs/` was never created. Candidates must stay under the active
session tmpdir, must not be symlinks, and must not be hardlinks. Legacy
`*.ndjson` files and other non-quiet-log artifacts under the session
`breadcrumbs/` hint are not published.
When no quiet log stages, the helper returns 0 and does not create, replace,
or clear an existing committed `breadcrumbs/` destination.

The enforced-reject and silent-skip split is documented in
[SECURITY.md § Breadcrumb stream redaction](../SECURITY.md#breadcrumb-stream-redaction):
enforced triggers fail closed for the whole directory, while legacy ndjson files,
non-regular files, and non-matching quiet-log basenames are ignored and not
committed.

`round-<N>/` directories are written by `run-log write-round` during
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

### design plan-review `findings-classification.tsv`

`larch-logs/design/<RUN_ID>/plan-review/round-<N>/findings-classification.tsv`
is the per-round forensic export produced by
`skills/design/scripts/tally-plan-review.sh`. The file always uses a 21-column,
tab-separated schema:

`finding_id`, `finding_reviewers`, `voting_result`, then three repeated slot
groups of: `vote`, `correctness`, `severity`, `quality`, `uncertain`, `tool`.

The canonical header is:

```text
finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool
```

Semantics:

- `finding_id` is the ballot heading id (`FINDING_N` or `OOS_N`).
- `finding_reviewers` is proposer attribution copied from the ballot block.
- `voting_result` is the final tally outcome for that row.
- `vN_vote` is the normalized vote token used by the tally (`YES`, `NO`,
  or empty when that slot had no parseable vote for the id; stray `EXONERATE` tokens are mapped to `NO`).
- `vN_correctness`, `vN_severity`, `vN_quality`, and `vN_uncertain` are the
  optional forensic rating axes parsed from the same voter line.
- `vN_tool` is the runtime tool identity for that slot.

Slot semantics:

- For explicit `--voter` dispatch, non-`MainAgent` voters preserve canonical
  tool slots from the declared `SLOT` label: `Claude -> v1`, `Codex -> v2`,
  `Cursor -> v3`. Basename heuristics do not override explicit slot labels.
  Missing slots stay empty instead of compacting later voters leftward.
- For sole `--voter MainAgent:<PATH>` adjudication, `v1`/`v2`/`v3` remain empty
  and `voting_result` stays `rejected` for every row even though the accepted /
  rejected / OOS artifact files reflect the MainAgent adjudication result.
- For legacy `--voter-files`, slots are inferred from basename/tool heuristics.
- Missing or degraded rounds preserve empty cells so every data row still has
  the full schema width. <!-- lint-literal-counts: allow fixed TSV schema --> A 0-finding or tally-error round may therefore publish a
  header-only TSV.

See [skills/design/scripts/tally-plan-review.md](skills/design/scripts/tally-plan-review.md)
for the authoritative producer contract and harness coverage.

### design plan-review per-round artifacts

Under `larch-logs/design/<RUN_ID>/plan-review/round-<N>/`, each single-pass Step 3 review entry produces forensic artifacts. The list below is a **representative** selection grouped by producer — `scripts/lib-design-round-artifacts.md` is the **authoritative** allowlist for the complete file set, and the `SECURITY.md` design-log publish-allowlist paragraph enforces what may be committed.

#### Findings

- `findings.md`
- `findings-in-scope.md`
- `findings-oos.md`
- `findings-classification.tsv`

#### Voting

- `oos.md`
- `oos-accepted-design.md`
- `ballot.txt` (session snapshot; excluded from committed log by publisher)
- `voting-tally.md`

`accepted-plan-findings.md` and `rejected-findings.md` are excluded from committed round directories (#3721) — they are cumulative across rounds (round N's copy is a prefix-snapshot of round N+1's); only the top-level copies in the design run directory are kept. Per-round outcome attribution is preserved by each round's `findings-classification.tsv` joined with `findings.md`.

#### Manifests and voter diagnostics

- `plan-review-slots.ndjson`
- `plan-voter-slots.ndjson`
- `scout-plan-manifest.json`
- `*-vote-output.txt`
- `*-vote-output-first-pass.txt`
- `voter*-diag.txt`
- `plan.txt` (round 1 only; rounds ≥ 2 commit `plan.diff` vs previous round)

#### Loop forensics

- `round-summary.env`

#### Revise sub-tree (`round-<N>/revise/`)

- `codex-output.txt`
- `cursor-output.txt`
- `claude-output.txt`
- `revise.env`
- `prompt.txt`
- `*-candidate.patch`

### code-review `findings-classification.tsv`

`/implement` review rounds publish
`larch-logs/implement/<RUN_ID>/round-<N>/findings-classification.tsv`.
Standalone `/review --diff` publishes flat per-round batches named
`review-findings-classification-round-N.tsv` under
`larch-logs/review/<RUN_ID>/`.

The code-review TSV schema is:

```text
finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain
```

`finding_id` is the ballot id (`FINDING_N` or `OOS_N`), `reviewer_slots` is the
pipe-delimited proposer attribution, and `voting_result` is one of `accepted`, `neutral`, or `rejected`. `vN_*` columns follow compact effective
voter order after failed/degraded slots are removed. Rating cells are enum-only;
missing or invalid axis tokens are empty and force `vN_uncertain=true`.

For 0-judge degraded rounds (`TALLY_STATUS=main-agent-vote-required`),
`voting_result=rejected` is a placeholder TSV sentinel, not a literal panel
outcome. Those rows intentionally keep empty `vN_*` cells until later
main-agent adjudication; the accepted/rejected/OOS markdown artifacts are the
authoritative operator-facing outcome for that degraded round.

`/review` uses the same `larch-logs/<skill>/<RUN_ID>/` layout when a run ID is provided. Review phase names are encoded in flat batch slugs, not subdirectories: `review-context` for gathered context, `review-panel-manifest` for launched slots, `review-findings` for collected finding records, `review-tally` for vote results, `review-scout-manifest` for dynamic-reviewer scout status, `review-round-summary` for the human-readable round summary, and `review-findings-classification-round-N` for the forensic vote/rating TSV.

## manifest.json

Created by `python/cli.py run-log init` during **Step 0** when the tracking issue is first resolved (tracking adoption / post-resolution). Updated by `run-log manifest` calls throughout the run. Contains: skill name, run ID, operator CWD, operator repo root, tracking-issue number, PR number (once created), the run status last recorded in that manifest snapshot, and optional routing flags such as `coder_fallback=true` when omitted-`--coder` routing fell past Codex. Authoritative contract: `docs/run-log-cli.md`.

For current `/implement` runs, the committed manifest is normally an `"in-progress"` snapshot because the post-merge `"done"` update happens inside `$IMPLEMENT_TMPDIR` after the last log commit window. That is not an absolute invariant: older committed runs, tests, or manual/status-update flows can still produce committed manifests with `"done"` or other statuses. To assess completion, read `status` as one signal and correlate it with PR merge state plus the surrounding run-log artifacts.

## Batch files

### include-probe-evidence.md

**Mode**: replace. **Written**: optional, when a plan's acceptance criteria require Phase 1 empirical subprocess output that otherwise lives only under `$IMPLEMENT_TMPDIR` (for example cross-agent include probes). Holds a redacted, tmpdir-free copy: a `BRANCH=A` / `BRANCH=B` header line plus per-agent transcript sections so post-merge reviewers can verify the probe and branch decision without the operator session tree.

### parent-issue.md

**Mode**: replace. **Written**: **Step 0** materialization tail and refreshed at the pre-bump flush when
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

**Mode**: replace (JSON object). **Written**: **Step 0** materialization tail, after the plan-review voting tally is exported.

One JSON object per `/implement` session. The tally envelope shape is shared with
`code-review-tally.json`: `schema_version` (`2`), `phase`, `batch`, `mode`, `rounds`,
`accepted_count`, `rejected_count`, `exonerated_count` (always 0; retained for backward compatibility), and `body`. For plan review the extra counters are normally `0`. Plan review voting itself runs during `/design`; this batch is often a stub or summary that references that outcome. The `body` contains
the plan-review voting outcome (accepted count, rejected count, round summaries)
plus any rejected plan-review findings under a `## Rejected Plan Review Findings`
sub-header. When no voting artifact is attached for this run, the body may note that plan review was completed in the `/design` phase instead of duplicating ballots here.

### code-review-tally.json

**Mode**: replace (JSON object). **Written**: Step 5, after the Step 5 review loop completes (via `review-and-fix CLI` / `review core`; standalone `/review` is a separate skill).

One JSON object per `/implement` session with the same tally envelope fields as
`plan-review-tally.json`. `exonerated_count` is an informational sub-count of
`rejected_count` (operator-facing summaries use “`K` accepted, `N` rejected (`P` exonerated)” where `P ≤ N`). `rejected_count` counts every finding that did not meet the acceptance threshold (including split-panel and exonerated vote patterns). The body contains the code-review voting outcome and a round-by-round
summary. It also includes rejected code-review findings under a
`## Rejected Code Review Findings` sub-header — findings that are not accepted appear here under a unified `### [rejected] FINDING_N` heading with a short **Rejected subtype** line when useful for operators.

**Note**: Internal tally KV may still emit `NEUTRAL_COUNT` for scoreboard accounting; that key is **not** the same thing as `JUDGE_ERROR`, which is a per-judge-per-finding state (the parser fallback when a
voter's ballot did not contain a parseable vote line for that finding). `JUDGE_ERROR`
appears in the per-finding vote breakdown table under the `JERR` column header but
is not separately enumerated in the tally envelope counters.

### review-findings-full.jsonl

**Mode**: replace (line-delimited JSON). **Written**: Step 5, immediately after the `code-review-tally` batch.

Per-finding payloads for plan-review accepted, plan-review rejected, and code-review entries. One JSON object per line with keys `id`, `issue_number`, `phase` (`plan-review` | `code-review`), `outcome` (`accepted` | `rejected` | `out_of_scope`), `schema_version` (`2`), `reviewer_slots` (array of redacted reviewer labels), `round_num` (empty outside numbered review rounds), `category` (best-effort, extracted from a leading `## <cat>: ...` body line — may be empty), and `prose_body` (redacted). See `python/legacy_review_shell/compose-review-findings.sh` (producer contract; `python/cli.py review compose-findings` is the CLI entrypoint).

**Backward compatibility**: Committed `larch-logs/**/review-findings-full.jsonl` may mix envelopes across runs. Normalize each line in three ways: **(1) v2** when `(has("reviewer_slots") and (.reviewer_slots | type == "array"))` — use `reviewer_slots` (and optional `schema_version`) as the canonical slot list. **(2) Legacy** only when v2 is absent: a string `reviewer` field (often without `schema_version`). **(3) Unknown / partial** — sparse historical stub rows may omit both usable shapes; log and skip (or count as unknown) rather than assuming a full v2 field set or treating `reviewer_slots: null`/non-array as v2. Example `jq` sketch:

```jq
if (has("reviewer_slots") and (.reviewer_slots | type == "array")) then
  .reviewer_slots
elif has("reviewer") and (.reviewer | type == "string") then
  [.reviewer]
else
  empty   # or: log "unknown row" to stderr
end
```

See `python/legacy_review_shell/compose-review-findings.sh` for the same mixed-stream contract (`python/cli.py review compose-findings` is the CLI entrypoint).

### version-bump-reasoning.md

**Mode**: replace. **Written**: **not** on the `/implement` ship path after Phase 1 (#3364). Legacy runs may still carry this batch from pre-Phase-1 implement bumps; new implement runs omit it. `/release` and manual `.claude/skills/release` flows own version reasoning when operators need an auditable bump record.

Markdown explanation of the version bump classification: which bump type was chosen (PATCH / MINOR / MAJOR), which changed files drove the decision, and the reasoning applied. Useful for auditing unexpected version jumps on release-driven paths.

### final-summary.md

**Mode**: replace. **Written**: the committed body is rendered by [`scripts/render-run-summary.sh`](../scripts/render-run-summary.sh); [`skills/implement/scripts/write-final-report.sh`](../skills/implement/scripts/write-final-report.md) writes `larch-logs/implement/<RUN_ID>/final-summary.md` and upserts the tracking-issue `larch:final-summary` comment for `/implement`, while [`skills/design/scripts/render-final-summary.sh`](../skills/design/scripts/render-final-summary.sh) does the same for `/design` under `larch-logs/design/<RUN_ID>/` during the post-outcome Step 5c render after plan write, diagram upsert, rename, and design-log publish have settled.

Committed **rich markdown** projection of the run: outcome, mode flags, token totals (Claude / Codex / Cursor / Claude (subprocess) — the spawned-process Claude reviewer/voter/CI/scout lane, machine name `claude_sub`, priced at Claude rates and summed into the total), optional per-lane USD estimates when [`python/report_tokens_cost.py`](../python/report_tokens_cost.py) rates are configured, duration, plan/code review tallies, OOS and execution-issue counts, log directory pointer, and operator-facing notes (fork dry-run, draft, no-merge, upstream issue, fork OOS stubs). The body is produced by [`scripts/render-run-summary.sh`](../scripts/render-run-summary.sh): it begins with a `## /<skill> run <run-id> — <outcome>` heading and a normalized markdown bullet list (including `**PR**:` when a PR is known; `- **Outcome**:` for outcomes matching `bailed*`, `stalled`, `cancelled-*`, `failed-*`, or `publish-skipped`; the other fields follow the renderer contract). A versioned HTML sentinel (`<!-- larch:run-summary v=1 -->`) appears on its own line after that bullet block (and before any optional trailing note lines) so consumers can detect the standardized block while the opening line stays human-readable. The `- **PR**:` bullet is omitted when no PR number is known; otherwise `#<number> — <url>` or `#<number>` when the URL is unknown. When `RUN_LOGS_PATH=N/A`, the renderer must not synthesize a fallback log path for `RUN_ID=unknown`, `failed-publish`, or `publish-skipped` outcomes. The tracking-issue `larch:final-summary` comment is the canonical live projection once upserted.

### oos-issues.ndjson

**Mode**: append (NDJSON records). **Written**: Step 9a.1, after out-of-scope issue filing.

Two sub-blocks per record: accepted OOS observations that were filed as GitHub issues (each entry includes the filed issue URL), and rejected / out-of-scope observations that were voted down or not filed (each entry includes the rejection reason). Security findings are never filed via this path.

### run-statistics.md

**Mode**: replace. **Written**: Step 9a.1.

Summary statistics for the run: number of accepted and rejected OOS items, filed-issue URLs, round counts, and other aggregate metrics.

### vendor-failure-diagnostics.txt

**Mode**: replace. **Written**: Step 7a pre-ship flush via `scripts/flush-vendor-failure-diagnostics.sh`, when at least one vendor-agent slot logged a failure diagnostic during the run.

Concatenation of per-slot `*.failure-diag` carriers composed by `append_vendor_failure_diagnostics` in `scripts/lib-failed-agent-stderr-tail.sh`. Each slot entry is redacted (tmpdir paths and secrets) before being staged as a part under `$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.parts/`; the flush helper concatenates all parts and writes the combined `vendor-failure-diagnostics.txt` batch. CI launchers (`python3 python/cli.py agent launch-codex-ci`, `python3 python/cli.py agent launch-cursor-ci`, `python3 python/cli.py agent launch-claude-ci`) and implement launchers (`launch-codex-implement.sh`, `launch-cursor-implement.sh`) feed this batch; reviewer launchers (`agent launch-review`) also contribute when `IMPLEMENT_TMPDIR` is set. **Availability caveat**: runs that bail before Step 7a (e.g., Step 2 dispatcher stall or Step 5 review stall) do not flush this batch; diagnostic parts then remain in the session tmpdir and are removed at Step 18 cleanup. The batch is absent in the committed run log for such early-bail runs.

### token-report.json

**Mode**: replace. **Written**: Step 7a tail (pre-ship log flush) and refreshed at Step 9a.1. CI-fix rebase/push retries also refresh the batch so the merged PR carries the most recent data: bash opt-in uses `python/cli.py run-log refresh` Triggers A-C inside `ship-pr.sh`, while the default Python driver uses `run_logs.flush_logs_pre` at CI/rebase boundaries.

Structured per-step Claude and external-vendor token usage for the session. The pre-ship flush captures cost up through implementation and review.

### timing-report.json

**Mode**: replace. **Written**: same lifecycle as `token-report.json`.

Structured per-step elapsed-time data for the session, measured from the timing ledger marks at each step entry. Useful for identifying slow steps (e.g., long Codex spawns, extended CI waits).

JSON reports may include an additive `rounds` array on a matching per-step row. `/implement` code-review rounds attach only to the `Step 5 — code review` row whose interval fully contains the round start and end; `/design` plan-review rounds attach only to the `design Step 3 — plan review` row under the same containment rule. Rows are de-duplicated by round number with the latest ledger row winning, then sorted by round. Round objects contain `round`, `duration_seconds`, `accepted`, and `rejected`; `/design` plan-review round objects also include `oos` when present.

### execution-issues.ndjson

**Mode**: append (NDJSON records). **Written**: Step 2 (Q/A entries, progressive), Step 7a (pre-bump flush of `execution-issues.md`), later external-implementer / pre-push refreshes when new entries are added after Step 7a, and Step 18's safety net when the normal flush path was missed.

Log of noteworthy events during the run, grouped by category: `Pre-existing Code Issues`, `Tool Failures`, `Permission Prompts`, `External Reviewer Issues`, `CI Issues`, `Warnings`, and `Q/A`. Entries from Step 2's Q/A loop are appended progressively; the main flush happens at Step 7a before shipping so the audit log is part of the same PR tree that CI validates. If later steps append new execution issues, the shared external-implementer / pre-push flush paths append only the unflushed tail, and Step 18 remains the best-effort fallback. This batch is the durable audit trail for follow-up work and operational events.

### session-transcript.jsonl

**Mode**: replace. **Written**: Step 7a tail (pre-ship log flush) for runs that reach Step 7a. Runs that bail out before Step 7a do not write this batch. The transcript is truncated at the pre-ship boundary — Steps 8+ (PR creation, CI, merge, cleanup; version bump omitted in Phase 1) are not included. On each CI retry, bash opt-in re-captures through `python/cli.py run-log refresh` Triggers A-C and the default Python driver refreshes through `run_logs.flush_logs_pre`, so the final merged PR carries the most up-to-date transcript available before merge.

A filtered, machine-readable rendering of the Claude Code session, produced by `scripts/render-session-transcript.py` from the raw session JSONL. **Schema v3 (policy: prose-errors-only).** The first line is a `{"v": 3, "source_basename": ..., "turns": N, "policy": "prose-errors-only"}` header; subsequent lines are per-turn objects with a `blocks` array. Blocks carry user-typed slash commands and text, assistant prose, and errored/warned `tool_result` entries (full body). `tool_call` blocks and non-error `tool_result` blocks are **omitted entirely** (v3 policy). Assistant `thinking` blocks are kept only when at least one `tool_use` in the same turn produced an errored result. Harness-injected SKILL.md expansions, attachments, and housekeeping events are dropped. Redacted for tmpdir paths and secrets before commit.

**Accepted capability loss (v3)**: tool-sequence reconstruction for clean runs (e.g., auditing how many times a file was re-read) is no longer possible from the committed transcript. Incident forensics of that shape must use live-session artifacts instead.

The `session-transcript` capture records `SESSION_TRANSCRIPT_STATUS` in the execution-issues `Warnings` section for every capture outcome, including refresh/deferred-commit `captured` outcomes and `render-failed` / `render-empty` when the renderer cannot produce a usable output (the run continues; nothing is committed). For runs that reach Step 7a, `session-transcript.jsonl` is part of the required-file completeness manifest; pre-Step-7a partial directories remain excluded by the verifier's step reachability rules. The recovery warning records only the discovered transcript basename, not the full operator-local path. See `scripts/render-session-transcript.md` for the complete schema.

### round-<N>/

**Mode**: directory replace-by-file. **Written**: first at the end of each
`review core` round during `/implement` Step 5, then optionally refreshed
later in the same round after the coder finishes if `review-and-fix CLI`
produces additional registered artifacts (for example coder-side files).

Contains a curated set of per-round artifacts: the aggregate `findings.md`,
accepted / rejected findings, OOS review markdown, voting tally and summary,
`aggregator-dispatch.stderr` / `aggregator-validate.stderr` when the findings
aggregator fails (so execution issues can point at committed paths instead of
`$REVIEW_TMPDIR`),
per-voter outputs (the byte-identical vote prompts and the raw per-specialist
reviewer outputs are excluded by `round_artifact_included` in
`python/cli.py run-log` because the aggregates already cover their content),
panel manifest (with `archetype_ref` for dynamic slots — see below),
code-voter slots, and any later registered coder artifacts. The `review core`
flush is the first snapshot for the round; `review-and-fix CLI` may run one more
`write-round` after coder application so the committed round directory reflects
the full round state before the later shared log-commit paths copy it into
`larch-logs/implement/<RUN_ID>/round-<N>/` in the repo. There is no per-round
commit.

**`round-meta.json`** (Phase 3c, issue #3716) — the per-round
sidecar files are consolidated into one JSON object rather than committed
individually. Sections:

| Section | Source file |
|---|---|
| `tally` | `review-tally.env` (KV → JSON object) |
| `collector` | `collector-results.env` (raw text) |
| `summary` | `review-summary.json` (JSON passthrough) |
| `coder` | `coder.env` (KV → JSON object) |
| `wrapper_logs.cursor` | `coder-cursor.wrapper.log` (raw text) |
| `wrapper_logs.codex` | `coder-codex.wrapper.log` (raw text) |

Absent sections are omitted. The audit scan `coder-tool` reads `round-meta.json`
as the primary source (`.coder.CODER_TOOL` via jq), falling back to `coder.env`
for rounds predating Phase 3c.

**Archetype pool** (Phase 3c) — `reviewer-dyn-*.md` archetype definitions are
no longer committed per-round. Each unique definition is written once to
`larch-logs/shared/archetypes/<sha256-12>.md` (content-addressed, idempotent).
Entries in `panel-manifest.ndjson` for `dyn-*` slots carry an `archetype_ref`
field (the SHA256-12 identifier). To resolve an archetype: look up
`archetype_ref` in `panel-manifest.ndjson`, then read
`larch-logs/shared/archetypes/<archetype_ref>.md`. The pool grows monotonically;
retroactive migration of pre-Phase-3c directories is handled by
`scripts/consolidate-round-sidecars.sh`.

## Tracking issue comments

The tracking issue carries marker-keyed summary comments as the workflow progresses. Most are run-scoped projections maintained by `/implement` and point at committed `larch-logs/` files rather than embedding bulky payloads inline. The exception is `larch:diagrams`: it is issue-scoped, jointly maintained by `/design` and `/implement`, and embeds Mermaid diagram bodies directly rather than pointing at a batch file.

### `larch:metadata`

Written during **Step 0** when the tracking issue is adopted or created.

Content: run ID, log directory path (`larch-logs/implement/<RUN_ID>/`), agent (implementer coder), and larch plugin version.

### `larch:plan`

Written at **Step 0** materialization tail after the plan is finalized.

Content: current plan-review tally status (voting outcome when present, or a pointer that detailed plan review lives in the `/design` run artifacts). The implementation plan is readable at the tracking issue body (`larch:plan` block via `manifest.json::issue_number`).

### `larch:diagrams`

Architecture is written by `/design` Step 5c via `skills/design/scripts/design-publish.sh` (diagrams upsert) after the `larch:plan` block is successfully written. Code Flow is written by `/implement` Step 7a only when code-flow generation succeeds.

Content: the Architecture Diagram (from `/design`) and Code Flow Diagram (generated at Step 7a from the committed implementation diff), both embedded as Mermaid fences. The stable marker is `<!-- larch:diagrams v1 -->` with no `runid=` segment. Diagrams are embedded directly in this comment rather than written as a larch-log batch.

### `larch:final-summary`

For `/implement`, written in two phases for full runs: first during Step 8+
PR creation, where the active Step 8+ driver renders and commits `final-summary.md` with
placeholder PR fields before `create-pr.sh` pushes the branch, and later
refreshed during Step 18 terminal cleanup. The tracking-issue comment may also
be refreshed immediately after PR creation with the live URL, without a second
log commit. Runs that never reach PR creation still run terminal cleanup and may refresh the tracking summary with `PR: N/A` when no PR exists.

For `/design`, `skills/design/scripts/render-final-summary.sh` writes `larch-logs/design/<RUN_ID>/final-summary.md` and upserts the same marker-keyed comment when an issue number is configured, during pre/post publish finalization. `failed-publish` summaries keep `Run logs: N/A` and append recovery metadata when available. `publish-skipped` summaries also keep `Run logs: N/A` and append the skipped-publish note instead of recovery prose.

Content: final run status (`STALL_TRACKING` value), PR URL, and log directory path. The committed `final-summary.md` in the PR tree may carry placeholder `PR: N/A`; the tracking-issue comment is the canonical live source for the PR URL.

## Retention

By default, larch accumulates full-fidelity run logs indefinitely. The `/gc-run-logs` skill implements an age-based retention policy to cap growth.

**Default policy (slim)**:

- Run dirs whose `started_at` date (or first-commit date fallback) is older than `--older-than DAYS` (default 90) are slimmed to the consumer-core keep set.
- The consumer-core keep set for `/implement` dirs: `manifest.json`, `final-summary.md`, `token-report.json`, `timing-report.json`, `review-findings-full.jsonl`, `execution-issues.ndjson`, `run-statistics.md`.
- The consumer-core keep set for `/design` dirs: `manifest.json`, `final-summary.md`, `token-report-final.json`, `timing-report-final.json`, `run-params.json`, `plan.txt`.
- All other files and subdirectories (round forensics, voter outputs, aggregator artifacts, etc.) are removed.
- A `gc-slimmed` marker file is written into each slimmed dir.

**Escalation (delete)**:

- `--delete` fully removes qualifying run dirs. Content remains recoverable via `git show <sha>:<path>` from git history.

**Guards**:

- Dirs containing `pause-state.txt` (resumable design sessions) are skipped.
- Dirs already carrying a `gc-slimmed` marker are skipped (idempotent).
- Dirs with no resolvable run date are skipped with a warning.

**Output**:

GC changes are committed on a dedicated branch and surfaced as a log-only PR for operator review and merge. GC is never run implicitly — operator-invoked only via `/gc-run-logs`.

**Audit interplay**:

Run dirs with a `gc-slimmed` marker may be missing non-keep-set files. Audit scanners should treat such absences as `informational` rather than `fail`; see `docs/run-logs-required-files.tsv` for the GC note on this behavior.

**Consumer safety**:

- `/report-tokens` (both skills): full cost-trend history is preserved indefinitely because it reads exactly the keep-set files.
- `audit-runs`: targets recent batches within the retention window; aged dirs carry the `gc-slimmed` marker for honest scan reporting.

## Authoritative sources

- `docs/run-log-cli.md` — `run-log` verb contracts, log-root resolution, redaction rules
- `docs/run-log-batches.md` — canonical batch slug table (extension, mode, sanitizer)
- `skills/implement/references/summary-comment-template.md` — marker literals and comment contracts
## Concise prune/log audit update

Concise review logs now use `round-meta.json` `reviewer_signals[]` for reviewer output audit scans instead of committing raw transcripts by default. Implement rounds include `prune-decision.env` and `prune-nit.env`; design plan-review rounds default to the four-file concise contract while keeping run-root `plan.txt`.

## /design failure-report artifacts

`/design` auto-reporting writes `design-failure-*.env` and `design-failure-*.md` artifacts under `$DESIGN_TMPDIR`. Important artifacts include terminal state, terminal report sentinels, escalation-success sentinels, operator-action sentinels, escalation ledgers, fallback chat print, operator-action chat audit, captured helper stdout/stderr sidecars, root-cause files, bounded root-cause files, and sensitive-corpus files.

`design-failure-terminal-state.env` is the terminal-state KV contract. Report helper stdout/stderr captures are retained beside `final-summary.md` so the summary body stays free of helper KVs.
