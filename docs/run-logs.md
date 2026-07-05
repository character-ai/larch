# Larch Run Logs

On a default `/implement --merge` run, a directory of structured log files is committed alongside the PR. These committed files are the single source of truth for full run content — voting tallies, code-review tally counters (`code-review-tally.json` self-review `accepted_count` / `rejected_count`), `review-findings-full.jsonl`, rejected findings, OOS observations, execution issues, run statistics, token/timing reports, and the session transcript. The tracking issue and PR body carry only slim projections. **Phase 1 (#3364):** `/implement` no longer writes `version-bump-reasoning.md` on the ship path; use `/release` or manual bump flows when version reasoning must be committed.

Exceptions: `repo_unavailable=true` produces no committed log at all (`$IMPLEMENT_TMPDIR/execution-issues.md` is the only audit trail and is removed at cleanup). Fork dry-run mode (`--forked`) does not create a tracking issue. In all cases, session-derived content in `larch-logs/` passes through secrets and tmpdir-path redaction, but redaction is best-effort — operators should avoid pasting sensitive content into `/implement` prompts.

## Plan scope and committed logs

Issue-anchored `larch:plan` blocks list the files that a `/implement` run is expected to touch. Retroactive maintenance across many runs under `larch-logs/design/` or `larch-logs/implement/` — for example URL normalization, typo fixes, or redaction-policy updates in historical committed logs — is not implied by plans that only target the **runtime plugin authority surface** defined in `AGENTS.md` (`skills/`, `agents/`, `hooks/`, `scripts/`, `.claude-plugin/`). Everything else in the repo (including `docs/`, `larch-logs/`, CI config, and `.claude/skills/`) is supplementary unless the tracking issue's `larch:plan` file list names it. Prefer a log-only PR for bulk `larch-logs/` edits so plan-to-diff review stays traceable; if bulk log edits ship on the same branch as changes under that runtime surface (or other paths not already listed in the plan), disclose the split in the PR title or body so reviewers can separate log churn from substantive work, and extend the issue `larch:plan` file list (or split the PR) when you add normative doc edits such as this file alongside unrelated implementation work.

## Directory structure

```
larch-logs/
  design/
    <RUN_ID>/
      manifest.json
      architectural-guideline-assessment.md
      (design session artifacts: files from `$DESIGN_TMPDIR` plus `render-cache/` subtree, filtered to exclude raw per-lane transcripts and sidecars via `design_log_publish_flow._publish_excluded`, then trimmed and redacted per `python/design_log_publish_flow.py`; `composed-plan.diff` is a unified diff of `composed-plan.md` vs final `plan.txt` — reconstruct with `patch plan.txt composed-plan.diff -o composed-plan.md`)
      plan-review/
        round-<N>/
          findings-classification.tsv
          panel-prompt-sizes.tsv
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
      difficulty-rating.json
      code-review-tally.json
      review-findings-full.jsonl
      final-summary.md
      oos-issues.ndjson
      run-statistics.md
      vendor-failure-diagnostics.txt
      token-report.json
      timing-report.json
      execution-issues.ndjson
      checks-digest-sizes.tsv
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
        panel-prompt-sizes.tsv
        aggregator-validate.stderr / aggregator-dispatch.stderr (when the findings aggregator fails; committed under the round directory when `write-round` runs)
        *-output.txt
        *-output.txt.meta
        *-output.txt.json
  review/
    <RUN_ID>/
      manifest.json
      session-transcript.jsonl
      review-context.md
      review-panel-manifest.ndjson
      review-findings.ndjson
      review-tally.md
      review-scout-manifest.json
      difficulty-rating.json
      review-round-summary.md
      review-findings-classification-round-<N>.tsv
      panel-prompt-sizes.tsv
      checks-digest-sizes.tsv
```

`<RUN_ID>` is the UUID assigned at the start of each `/implement` session. Batch payload files under a run directory are redacted for secrets and tmpdir paths before commit. `manifest.json` schema version 2 keeps `operator_cwd` / `operator_repo_root` only as stable redacted placeholders (`"<OPERATOR_CWD>"`, `"<REPO_ROOT>"`) so committed logs preserve schema shape without exposing operator-local absolute paths.

### design architectural guideline assessment

`larch-logs/design/<RUN_ID>/architectural-guideline-assessment.md` is a
top-level design artifact written from Gate C only. It is present only when
`ARCHITECTURAL_GUIDELINES.md` is present and valid at final Gate C approval.
It contains either the deterministic clean note or the orchestrator-authored
deviation assessment.

When guidelines are absent or invalid, Gate C removes any stale assessment
artifact before approval, so no stale copy is committed. The artifact publishes
through the existing design-log copy, tmpdir redaction, and secret-scrub flow.
It is auditable through `/fluff-analysis` guideline assessment coverage and
`python/cli.py audit-runs scan-run --skill design`.

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
`python/cli.py run-log commit` (`/implement`) and `scripts/python/cli.py design log-publish`
(`design` publish).

`breadcrumbs/` is a commit-only directory artifact, not a larch-log batch.
`python/cli.py run-log commit` and `scripts/python/cli.py design log-publish` invoke the
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

### panel prompt-size telemetry

`panel-prompt-sizes.tsv` is count-only telemetry for panel-tier prompts. It records safe identifiers, rendered prompt byte and estimated-token counts, derived scaffold and payload byte/token counts, and agent-file byte and estimated-token counts when a repo-local agent file exists. It never stores rendered prompt text or payload text.

Rows are written only when `LARCH_PANEL_SLOT` is set and the slot class is recognized as specialist, plan-review, voter, aggregator, or implementer. Dispatch producers set the panel environment explicitly in review dispatch, code voters, plan-review dispatch, aggregation, and review-fix coder paths. Appends use a best-effort flock-protected TSV writer, so lock or write failures skip telemetry without failing the parent dispatch.

Current rows include `scaffold_bytes`, `scaffold_tokens`, `payload_bytes`, and `payload_tokens`. `prompt_bytes` remains the rendered prompt size. `payload_bytes` is count-only per-run content that the renderer or dispatcher knows it inlined or attached as prompt payload; `scaffold_bytes` is the non-negative remainder of prompt bytes after subtracting payload bytes. Older committed TSVs may lack these columns. `measure-panel-cost` treats missing scaffold as the whole prompt and missing payload as zero.

Committed locations are:

- Design plan review: `larch-logs/design/<RUN_ID>/plan-review/round-<N>/panel-prompt-sizes.tsv` only. Top-level design copies are ignored.
- Implement Step 5: `larch-logs/implement/<RUN_ID>/round-<N>/panel-prompt-sizes.tsv`.
- Standalone review: `larch-logs/review/<RUN_ID>/panel-prompt-sizes.tsv`, or `larch-logs/review/<RUN_ID>/round-<N>/panel-prompt-sizes.tsv` when the dispatch is round-local.

`python3 python/cli.py token measure-panel-cost` aggregates committed panel TSVs by agent file, plus generated/no-agent buckets for voters and generated prompts. It writes a TSV under `larch-logs/measure-panel-cost/` with dispatch counts, runs observed, loads per run, prompt counts, scaffold and payload counts, agent counts, and total realized counts. Rows rank by scaffold bytes so fixed prompt surface stays visible even when payload-heavy runs dominate realized bytes.

### checks digest-size telemetry

`checks-digest-sizes.tsv` is count-only telemetry for relevant-checks failure digests. It records byte and estimated-token counts for the redacted failure log and the generated digest, plus signed `saved_bytes` and `saved_tokens` values. Savings can be negative when a digest is larger than a tiny redacted log. The file never stores log text, digest text, commands, failure lines, prompts, or absolute paths.

Committed locations are:

- Implement checks failures: `larch-logs/implement/<RUN_ID>/checks-digest-sizes.tsv`.
- Standalone review checks failures: `larch-logs/review/<RUN_ID>/checks-digest-sizes.tsv`.

Writes are best-effort. A telemetry lock or write failure prints a warning and does not change the checks result or the `DIGEST_FILE=` failure envelope. The writer skips telemetry unless exactly one active implement or review run directory exists under the session `larch-logs/` tree.

`python3 python/cli.py token measure-checks-digest-savings` aggregates committed checks-digest TSVs into `larch-logs/measure-checks-digest-savings/<DATE>.tsv`. It reports `status=insufficient-data` until at least 5 valid rows exist. With 5 or more rows, positive aggregate signed token savings yields `recommendation=go-design-validator-extension`; zero or negative aggregate token savings yields `recommendation=no-go-design-validator-extension`. The design-validator digest extension remains gated on a future positive measurement.

### design plan-review `findings-classification.tsv`

`larch-logs/design/<RUN_ID>/plan-review/round-<N>/findings-classification.tsv`
is the per-round forensic export produced by
`python/cli.py plan-review tally`. The file always uses a 23-column,
tab-separated schema:

`finding_id`, `finding_reviewers`, `voting_result`, then three repeated slot
groups of: `vote`, `correctness`, `severity`, `quality`, `uncertain`, `tool`,
then `body_severity` and `scope`.

The canonical header is:

```text
finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\tscope
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
- `body_severity` is the optional severity token parsed from the finding body
  (`blocker`, `major`, `minor`, `nit`, or empty). It is forensic metadata only;
  reviewer scoreboards weight accepted in-scope findings from YES-voter panel
  severity, not from `body_severity`.
- `scope` is `in_scope` or `oos`. Producers write `scope=oos` for direct
  `OOS_*` rows, legacy `[OUT_OF_SCOPE]` or `[OOS]` rows, and scope-drift rows.
  Consumers prefer explicit `scope=oos` over id prefixes; legacy TSVs without
  `scope` remain readable with flat accepted +1 scoring and `OOS_` prefix fallback.

Older committed design TSVs may use the 21-column shape without
`body_severity`. `/voter-calibration` keeps those readable through
header-driven detection, so `v3_tool` is not shifted into the body-severity
slot.

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
  the full 23-column schema width. <!-- lint-literal-counts: allow fixed TSV schema --> A 0-finding or tally-error round may therefore publish a
  header-only TSV.

See [python/plan_review.py](python/plan_review.py)
for the authoritative producer contract and harness coverage.

### design plan-review per-round artifacts

Under `larch-logs/design/<RUN_ID>/plan-review/round-<N>/`, each single-pass Step 3 review entry produces forensic artifacts. The list below is a **representative** selection grouped by producer — `python/plan_review.py` is the **authoritative** allowlist for the complete file set, and the `SECURITY.md` design-log publish-allowlist paragraph enforces what may be committed.

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

`voting-tally.md` includes the per-finding vote table, reviewer competition
scoreboard, and voter agreement scoreboard. The voter agreement section is a
diagnostic view over the same classification rows. It does not introduce a new
committed artifact.

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

New three-slot code-review TSV writes use this schema:

```text
finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tscope
```

`finding_id` is the ballot id (`FINDING_N` or `OOS_N`), `reviewer_slots` is the
pipe-delimited proposer attribution, `voting_result` is one of `accepted`, `neutral`, or `rejected`, and `scope` is `in_scope` or `oos`. Producers write `scope=oos` for direct `OOS_*` rows, legacy `[OUT_OF_SCOPE]` or `[OOS]` rows, and scope-drift rows. Consumers prefer explicit `scope=oos` over id prefixes; legacy TSVs without `scope` remain readable with flat accepted +1 scoring and `OOS_` prefix fallback. On the three-slot code-review path, `v1` is `codex-validity`, `v2` is `codex-plan-fidelity`, and `v3` is `codex-pragmatism`; `claude` appears in `v1_tool` only on the both-externals-down fallback path, and older logs may still contain `cursor-validity`. Empty or failed slots keep their `vN_tool` label with empty rating cells. Rating cells are enum-only; missing or invalid axis tokens are empty and force `vN_uncertain=true`. Older logs may lack `vN_tool` or use the compact 18-column layout. MAV re-tally rows may also use the legacy single-voter 18-column shape.

The committed TSV schemas remain backward compatible for new writes. The
analyzer reads older 21-column design TSVs without `body_severity` and older
18-column compact code-review TSVs through header-driven detection.

For 0-judge degraded rounds (`TALLY_STATUS=main-agent-vote-required`),
`voting_result=rejected` is a placeholder TSV sentinel, not a literal panel
outcome. Those rows intentionally keep empty `vN_*` cells until later
main-agent adjudication; the accepted/rejected/OOS markdown artifacts are the
authoritative operator-facing outcome for that degraded round.

`/review` uses the same `larch-logs/<skill>/<RUN_ID>/` layout when a run ID is provided. Review phase names are encoded in flat batch slugs, not subdirectories: `review-context` for gathered context, `review-panel-manifest` for launched slots, `review-findings` for collected finding records, `review-tally` for vote results, `review-scout-manifest` for dynamic-reviewer scout status, `difficulty-rating` for the standalone run difficulty record, `review-round-summary` for the human-readable round summary, and `review-findings-classification-round-N` for the forensic vote/rating TSV.

## manifest.json

Created by `python/cli.py run-log init` during **Step 0** when the tracking issue is first resolved (tracking adoption / post-resolution). Updated by `run-log manifest` calls throughout the run. Contains: skill name, run ID, operator CWD, operator repo root, tracking-issue number, PR number (once created), the larch plugin version (`larch_version`), the main-agent model and reasoning effort (`model_roster.main` and `effort`, resolved at init from the active session transcript and `CLAUDE_CODE_*` / `CLAUDE_*` env, falling back to `unknown`), the run status last recorded in that manifest snapshot, and optional routing flags such as `coder_fallback=true` when omitted-`--coder` routing fell past Codex. Authoritative contract: `docs/run-log-cli.md`.

`model_roster.main` is the orchestrator (main-agent) model id, not the implementer coder. It is captured once at run-log init (the newest session transcript at that point is the orchestrator session, before subagents spawn) via `tokens.read_main_model`, then preserved across `run-log manifest` merges. Historical runs predating this capture carry `"unknown"`.

For current `/implement` runs, the committed manifest is normally an `"in-progress"` snapshot because the post-merge `"done"` update happens inside `$IMPLEMENT_TMPDIR` after the last log commit window. That is not an absolute invariant: older committed runs, tests, or manual/status-update flows can still produce committed manifests with `"done"` or other statuses. To assess completion, read `status` as one signal and correlate it with PR merge state plus the surrounding run-log artifacts.

## Batch files

### include-probe-evidence.md

**Mode**: replace. **Written**: optional, when a plan's acceptance criteria require Phase 1 empirical subprocess output that otherwise lives only under `$IMPLEMENT_TMPDIR` (for example cross-agent include probes). Holds a redacted, tmpdir-free copy: a `BRANCH=A` / `BRANCH=B` header line plus per-agent transcript sections so post-merge reviewers can verify the probe and branch decision without the operator session tree.

### parent-issue.md

**Mode**: replace. **Written**: **Step 0** materialization tail and refreshed at the pre-ship log flush when
present.

Tracking-issue sentinel with the adopted or created issue number and run ID.
This is the session-scope idempotency source for tracking issue recovery.

### pre-review-head.txt and pre-review-untracked.txt

**Mode**: replace. **Written**: Step 5 round 1 initialization.

`pre-review-head.txt` records the HEAD SHA before review starts.
`pre-review-untracked.txt` records the untracked-file snapshot used by the
review-change checks.

### codex-impl-transcript.txt and related Codex setup files

**Mode**: replace. **Written**: Step 7a pre-ship log flush when present.

`codex-impl-transcript.txt` is the external implementer transcript,
`codex-impl-transcript-prompt.txt` is the prompt sidecar,
`codex-commit-message.txt` is the redacted commit message consumed by the
dispatcher, and `codex-impl-manifest-raw.json` is the pre-sanitized manifest
copy retained for diagnosis. These files are optional because non-Codex or
bailout paths may not produce them.

### plan-review-tally.json

**Mode**: replace (JSON object). **Written**: **Step 0** materialization tail. `/implement` writes this batch on every run: the exported plan-review voting tally when one is present, otherwise a stub recording that plan review ran in `/design`.

One JSON object per `/implement` session. The tally envelope shape is shared with
`code-review-tally.json`: `schema_version` (`2`), `phase`, `batch`, `mode`, `rounds`,
`accepted_count`, `rejected_count`, and `exonerated_count` (always 0; retained for backward compatibility). The `body` field is phase-dependent. `plan-review-tally.json` includes `body`; `code-review-tally.json` omits it. For plan review the extra counters are normally `0`. Plan review voting itself runs during `/design`; this batch is often a stub or summary that references that outcome. The `body` contains
the plan-review voting outcome (accepted count, rejected count, round summaries)
plus any rejected plan-review findings under a `## Rejected Plan Review Findings`
sub-header. When no voting artifact is attached for this run, the body may note that plan review was completed in the `/design` phase instead of duplicating ballots here.

### code-review-tally.json

**Mode**: replace (JSON object). **Written**: Step 5, after the Step 5 review loop completes (via `review-and-fix CLI` / `review core`; standalone `/review` is a separate skill).

One JSON object per `/implement` session with these envelope fields:
`schema_version` (`2`), `phase`, `batch`, `mode`, `rounds`, `accepted_count`,
`rejected_count`, and `exonerated_count`. It does not store a `body` field. The
body file is validation input only when the tally is written. Round markdown,
voting prose, and rejected-finding details live in the per-round artifacts and
`review-findings-full.jsonl`.

`rounds` is the total number of completed code-review rounds for the run. For a
normal multi-round `/implement`, it should match the committed `round-*`
directory count. `accepted_count` and `rejected_count` are cumulative across all
code-review rounds and are derived from composed `review-findings-full.jsonl`
code-review rows. `exonerated_count` is an informational sub-count of
`rejected_count` (operator-facing summaries use “`K` accepted, `N` rejected (`P` exonerated)” where `P ≤ N`). `rejected_count` counts every finding that did not meet the acceptance threshold (including split-panel and exonerated vote patterns).

For `mode: self-review`, `rounds` is always `1`. `accepted_count` is the count
of in-scope self-review findings fixed inline during Step 5, recorded as
`### [Code Review] Self-review accepted` headings in
`$IMPLEMENT_TMPDIR/self-review-accepted.md`. `rejected_count` is the count of
self-review findings recorded under exact `### [Code Review] Self-review`
headings in `$IMPLEMENT_TMPDIR/rejected-findings.md`.
`review-and-fix write-self-review-tally` reads those files under
`--implement-tmpdir` and derives `accepted_count` and `rejected_count`
internally; a missing or empty file counts as `0`. Self-review tally counters
are not derived from `review-findings-full.jsonl`; that file may remain an empty
sentinel for self-review runs to show that review ran.

**Note**: Internal tally KV may still emit `NEUTRAL_COUNT` for scoreboard accounting; that key is **not** the same thing as `JUDGE_ERROR`, which is a per-judge-per-finding state (the parser fallback when a
voter's ballot did not contain a parseable vote line for that finding). `JUDGE_ERROR`
appears in the per-finding vote breakdown table under the `JERR` column header but
is not separately enumerated in the tally envelope counters.

### review-findings-full.jsonl

**Mode**: replace (line-delimited JSON). **Written**: Step 5, immediately after the `code-review-tally` batch.

Per-finding payloads for plan-review accepted, plan-review rejected, and code-review entries. One JSON object per line with keys `id`, `issue_number`, `phase` (`plan-review` | `code-review`), `outcome` (`accepted` | `rejected` | `out_of_scope`), `schema_version` (`2`), `reviewer_slots` (array of redacted reviewer labels), `round_num` (empty outside numbered review rounds), `category` (best-effort, extracted from a leading `## <cat>: ...` body line — may be empty), and `prose_body` (redacted). See `python/compose_review.py` (producer contract; `python/cli.py review compose-findings` is the CLI entrypoint).

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

See `python/compose_review.py` for the same mixed-stream contract (`python/cli.py review compose-findings` is the CLI entrypoint).

### version-bump-reasoning.md

**Mode**: replace. **Written**: **not** on the `/implement` ship path after Phase 1 (#3364). Legacy runs may still carry this batch from pre-Phase-1 implement bumps; new implement runs omit it, and it is no longer listed in `docs/run-logs-required-files.tsv`, so the `required-file-presence` audit no longer expects it on implement runs. `/release` and manual `.claude/skills/release` flows own version reasoning when operators need an auditable bump record.

Markdown explanation of the version bump classification: which bump type was chosen (PATCH / MINOR / MAJOR), which changed files drove the decision, and the reasoning applied. Useful for auditing unexpected version jumps on release-driven paths.

### difficulty-rating.json

**Mode**: replace. **Written**: every design, implement, and standalone review run records a JSON object with `schema_version: 1`, rater identity, predicted and applied tier, confidence, bounded rationale, design and implement tiers when known, floor matches, audit placeholders, escalation placeholders, and `panel_skipped` when the run intentionally skipped review. The rating is model judgment anchored by `docs/difficulty-rating.md`; deterministic floors in `docs/difficulty-floor-globs.tsv` can raise the applied tier but never lower it. Early degraded partial dirs may rely on the existing partial-run tolerance rules.

### final-summary.md

**Mode**: replace. **Written**: the committed body is rendered by `python/cli.py render run-summary`; [`python/cli.py final-report write`](../skills/implement/scripts/write-final-report.md) writes `larch-logs/implement/<RUN_ID>/final-summary.md` and upserts the tracking-issue `larch:final-summary` comment for `/implement`. For `/design`, `python/cli.py design log-publish` renders the enriched `final-summary.md` inside the design tmpdir before copying the committed snapshot, with tracking-comment upserts suppressed in that pre-copy render. Step 5c and clarify then run the authoritative follow-up `python/cli.py design render-final-summary` pass that upserts the marker-keyed tracking comment.

Committed **rich markdown** projection of the run: outcome, mode flags, token totals (Claude / Codex / Cursor / Claude (subprocess) — the spawned-process Claude reviewer/voter/CI/scout lane, machine name `claude_sub`, priced at Claude rates and summed into the total), optional per-lane USD estimates when [`python/larch/report/report_tokens_cost.py`](../python/larch/report/report_tokens_cost.py) rates are configured, duration, plan/code review tallies, OOS and execution-issue counts, log directory pointer, the difficulty bullet, the main-agent model, reasoning effort, and larch plugin version (the `- **Main agent model**:`, `- **Effort**:`, and `- **Larch version**:` bullets, read from the run manifest via `--manifest-path` with live fallbacks), and operator-facing notes (fork dry-run, draft, no-merge, upstream issue, fork OOS stubs). The body is produced by `python/cli.py render run-summary`: it begins with a `## /<skill> run <run-id>: <outcome>` heading and a normalized markdown bullet list (including `**PR**:` when a PR is known; `- **Outcome**:` for outcomes matching `bailed*`, `stalled`, `cancelled-*`, `failed-*`, or `publish-skipped`; the other fields follow the renderer contract). A versioned HTML sentinel (`<!-- larch:run-summary v=1 -->`) appears on its own line after that bullet block (and before any optional trailing note lines) so consumers can detect the standardized block while the opening line stays human-readable. The `- **PR**:` bullet is omitted when no PR number is known; otherwise `#<number> — <url>` or `#<number>` when the URL is unknown. When `RUN_LOGS_PATH=N/A`, the renderer must not synthesize a fallback log path for `RUN_ID=unknown`, `failed-publish`, or `publish-skipped` outcomes. The tracking-issue `larch:final-summary` comment is the canonical live projection once upserted.

For `/implement`, non-accepted non-security OOS rows from `round-*/oos.md` surface in a bounded `## Rejected OOS audit` section. `/implement` no longer writes `oos-dropped-before-vote.md`; accepted non-security OOS files through the unified OOS issue path, and security-routed OOS stays out of public logs.

### oos-issues.ndjson

**Mode**: append (NDJSON records). **Written**: Step 9a.1, after out-of-scope disposition evidence is materialized.

Two sub-blocks per record: accepted OOS observations that were filed as GitHub issues (each entry includes the filed issue URL), and rejected / out-of-scope observations that were voted down or not filed (each entry includes the rejection reason). Security findings are never filed via this path. `oos-issues.ndjson` is disposition evidence, not the Step 9a.1 completion signal. A provisional `oos-issues.ndjson` written before a failed disposition checkpoint must not mark Step 9a.1 complete.

### run-statistics.md

**Mode**: replace. **Written**: Step 9a.1, after the OOS disposition checkpoint succeeds.

Summary statistics for the run: number of accepted and rejected OOS items, filed-issue URLs, round counts, and other aggregate metrics. Step 9a.1 completion requires post-checkpoint `run-statistics.md`. Explicit `manifest.json` `steps_ran.step9a1=true` is recorded only together with that file; `step9a1=true` without `run-statistics.md` is a stale or corrupt marker and must fail audit/verify scans.

### vendor-failure-diagnostics.txt

**Mode**: replace. **Written**: Step 7a pre-ship flush via `scripts/flush-vendor-failure-diagnostics.sh`, when at least one vendor-agent slot logged a failure diagnostic during the run.

Concatenation of per-slot `*.failure-diag` carriers composed by `append_vendor_failure_diagnostics` in `python/larch/agents/agents.py`. Each slot entry is redacted (tmpdir paths and secrets) before being staged as a part under `$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.parts/`; the flush helper concatenates all parts and writes the combined `vendor-failure-diagnostics.txt` batch. CI launchers (`python3 python/cli.py agent launch-codex-ci`, `python3 python/cli.py agent launch-cursor-ci`, `python3 python/cli.py agent launch-claude-ci`) and implement launchers (`agent launch-codex-implement`, `agent launch-cursor-implement`) feed this batch; reviewer launchers (`agent launch-review`) also contribute when `IMPLEMENT_TMPDIR` is set. **Availability caveat**: runs that bail before Step 7a (e.g., Step 2 dispatcher stall or Step 5 review stall) do not flush this batch; diagnostic parts then remain in the session tmpdir and are removed at Step 18 cleanup. The batch is absent in the committed run log for such early-bail runs.

### token-report.json

**Mode**: replace. **Written**: Step 7a tail (pre-ship log flush) and refreshed at Step 9a.1. The agentic Claude CI-fix delegate reconstructs `RunContext` and requires `--repo-root`, so rebase/push retries refresh the batch through `run_logs.flush_logs_pre` before force-push or rebase preparation. `ci-fix-exhausted` pairs with Step 12d operator bail. Stall recovery does not auto-resume the ship step for that token.

Structured per-step Claude and external-vendor token usage for the session. The pre-ship flush captures cost up through implementation and review.

### timing-report.json

**Mode**: replace. **Written**: same lifecycle as `token-report.json`.

Structured per-step elapsed-time data for the session, measured from the timing ledger marks at each step entry. Useful for identifying slow steps (e.g., long Codex spawns, extended CI waits).

JSON reports may include an additive `rounds` array on a matching per-step row. `/implement` code-review rounds attach only to the `Step 5 — code review` row whose interval fully contains the round start and end; `/design` plan-review rounds attach only to the `design Step 3 — plan review` row under the same containment rule. Rows are de-duplicated by round number with the latest ledger row winning, then sorted by round. Round objects contain `round`, `duration_seconds`, `accepted`, and `rejected`; `/design` plan-review round objects also include `oos` when present.

### execution-issues.ndjson

**Mode**: append (NDJSON records). **Written**: Step 2 (Q/A entries, progressive), Step 7a (pre-ship log flush of `execution-issues.md`), later external-implementer / pre-push refreshes when new entries are added after Step 7a, and Step 18's safety net when the normal flush path was missed.

Log of noteworthy events during the run, grouped by category: `Pre-existing Code Issues`, `Tool Failures`, `Permission Prompts`, `External Reviewer Issues`, `CI Issues`, `Warnings`, and `Q/A`. Entries from Step 2's Q/A loop are appended progressively; the main flush happens at Step 7a before shipping so the audit log is part of the same PR tree that CI validates. If later steps append new execution issues, the shared external-implementer / pre-push flush paths append only the unflushed tail, and Step 18 remains the best-effort fallback. This batch is the durable audit trail for follow-up work and operational events.

### session-transcript.jsonl

**Mode**: replace. **Written**: `/implement` Step 7a remains the primary green-path capture point, with Step 18 as a best-effort finalization safety net for bail and stall paths that reach teardown first. `/design` captures once inside the shared `design log-publish` entry point, so Step 5c, clarify, and pause-save publish paths use the same hook. Standalone `/review` captures before cleanup and commits staged batches so the transcript survives tmpdir removal. Historical logs are not backfilled.

A filtered, machine-readable rendering of the Claude Code session, produced by `python3 python/cli.py run-log render-session-transcript` from the raw session JSONL. **Schema v3.** The first line is a `{"v": 3, "source_basename": ..., "turns": N, ...}` header; subsequent lines are per-turn objects with a `blocks` array. Blocks carry user-typed slash commands and text, assistant prose, errored/warned `tool_result` entries, and sanitized reference `Read` stubs with normalized `file_path` values only. File contents, other `tool_call` blocks, and non-error `tool_result` blocks are omitted. Assistant `thinking` blocks are kept only when at least one `tool_use` in the same turn produced an errored result. Harness-injected SKILL.md expansions, attachments, and housekeeping events are dropped. Redacted for tmpdir paths and secrets before commit.

**Accepted capability loss (v3)**: full tool-sequence reconstruction for clean runs is not possible from the committed transcript. The retained reference `Read` stubs support aggregate reference-heatmap measurements, not detailed incident forensics.

The `session-transcript` capture records `SESSION_TRANSCRIPT_STATUS` in the execution-issues `Warnings` section for every capture outcome, including refresh/deferred-commit `captured` outcomes and `render-failed` / `render-empty` when the renderer cannot produce a usable output. The run continues when capture cannot produce a transcript. For `/implement` runs that reach Step 7a, `session-transcript.jsonl` is part of the required-file completeness manifest; pre-Step-7a partial directories remain excluded by the verifier's step reachability rules. The recovery warning records only the discovered transcript basename, not the full operator-local path. See `python/render_session_transcript.md` for the complete schema.

`python3 python/cli.py token measure-references-heatmap` now starts with a `transcript_coverage` section that reports transcript-bearing runs, total runs, missing transcript runs, and the coverage ratio per skill before the per-reference heatmap rows. A skill with transcripts and zero reference reads is reported as measured zero data, not as missing data.

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
code-voter slots, the canonical waterfall `*.dropped-slots` ledger, bounded
`dropped-*-*.txt` diagnostics for dropped reviewer slots, and any later
registered coder artifacts. The `review core`
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
| `difficulty` | scout difficulty sidecar, persisted difficulty record, or absent placeholder |
| `wrapper_logs.cursor` | `coder-cursor.wrapper.log` (raw text) |
| `wrapper_logs.codex` | `coder-codex.wrapper.log` (raw text) |

Absent sections are omitted except `difficulty`, which may carry `tier_in_effect`, `ceiling_in_effect`, `applied_tier`, `panel_tier`, `round_cap`, `codex_model_role`, `override_source`, `audit_evaluated`, `audit_upgrade`, `escalations`, empty escalation placeholders, and scout source fields when present. The audit scan `coder-tool` reads `round-meta.json`
as the primary source (`.coder.CODER_TOOL` via jq), falling back to `coder.env`
for rounds predating Phase 3c.

**Archetype pool** (Phase 3c) — `reviewer-dyn-*.md` archetype definitions are
no longer committed per-round. Each unique definition is written once to
`larch-logs/shared/archetypes/<sha256-12>.md` (content-addressed, idempotent).
Entries in `panel-manifest.ndjson` carry `vendor` and `resolved_model` for each slot. Entries for `dyn-*` slots also carry an `archetype_ref`
field (the SHA256-12 identifier). To resolve an archetype: look up
`archetype_ref` in `panel-manifest.ndjson`, then read
`larch-logs/shared/archetypes/<archetype_ref>.md`. The pool grows monotonically.

## Tracking issue comments

The tracking issue carries marker-keyed summary comments as the workflow progresses. Most are run-scoped projections maintained by `/implement` and point at committed `larch-logs/` files rather than embedding bulky payloads inline. The exception is `larch:diagrams`: it is issue-scoped, jointly maintained by `/design` and `/implement`, and embeds Mermaid diagram bodies directly rather than pointing at a batch file.

### `larch:metadata`

Written during **Step 0** when the tracking issue is adopted or created.

Content: run ID, log directory path (`larch-logs/implement/<RUN_ID>/`), agent (implementer coder), and larch plugin version.

### `larch:plan`

Written at **Step 0** materialization tail after the plan is finalized.

Content: current plan-review tally status (voting outcome when present, or a pointer that detailed plan review lives in the `/design` run artifacts). The implementation plan is readable at the tracking issue body (`larch:plan` block via `manifest.json::issue_number`).

### `larch:diagrams`

Architecture is generated by `/design` Step 5b.5 after Gate C approval, then written by `/design` Step 5c via `python/cli.py design step5c`; that orchestration entrypoint calls the `design publish` tail in-process to upsert diagrams after the `larch:plan` block is successfully written. Code Flow is written by `/implement` Step 7a only when code-flow generation succeeds.

Content: the Architecture Diagram (from `/design`) and Code Flow Diagram (generated at Step 7a from the committed implementation diff), both embedded as Mermaid fences. The stable marker is `<!-- larch:diagrams v1 -->` with no `runid=` segment. Diagrams are embedded directly in this comment rather than written as a larch-log batch. Top-level design diagram body artifacts and diagram-generation or sanitizer failure captures are excluded from committed design logs. Implement code-flow diagram body files and `code-flow-diagram.failure.log` are not copied into `larch-logs/implement/<RUN_ID>/`; bounded `execution-issues.md` warnings are the durable failure surface.

### `larch:final-summary`

For `/implement`, written in two phases for full runs: first during Step 8+
PR creation, where the active Step 8+ driver renders and commits `final-summary.md` with
placeholder PR fields before `python/cli.py pr create` pushes the branch, and later
refreshed during Step 18 terminal cleanup. The tracking-issue comment may also
be refreshed immediately after PR creation with the live URL, without a second
log commit. Runs that never reach PR creation still run terminal cleanup and may refresh the tracking summary with `PR: N/A` when no PR exists.

For `/design`, `python/cli.py design log-publish` renders the committed `larch-logs/design/<RUN_ID>/final-summary.md` before copying the run tree. Step 5c and clarify follow with a post-publish `python/cli.py design render-final-summary` pass that upserts the same marker-keyed tracking comment when an issue number is configured. `failed-publish` summaries keep `Run logs: N/A` and append recovery metadata when available. `publish-skipped` summaries also keep `Run logs: N/A` and append the skipped-publish note instead of recovery prose.

Content: final run status (`STALL_TRACKING` value), PR URL, and log directory path. The committed `final-summary.md` in the PR tree may carry placeholder `PR: N/A`; the tracking-issue comment is the canonical live source for the PR URL.

## Retention

By default, larch accumulates full-fidelity run logs indefinitely. The `/gc-run-logs` skill implements an age-based retention policy to cap growth.

**Default policy (slim)**:

- Run dirs whose `started_at` date (or first-commit date fallback) is older than `--older-than DAYS` (default 90) are slimmed to the consumer-core keep set.
- The consumer-core keep set for `/implement` dirs: `manifest.json`, `final-summary.md`, `difficulty-rating.json`, `token-report.json`, `timing-report.json`, `review-findings-full.jsonl`, `execution-issues.ndjson`, `run-statistics.md`, `checks-digest-sizes.tsv`.
- The consumer-core keep set for `/design` dirs: `manifest.json`, `final-summary.md`, `difficulty-rating.json`, `token-report-final.json`, `timing-report-final.json`, `run-params.json`, `plan.txt`, `architectural-guideline-assessment.md`, and any `larch-tokens-*.jsonl` token ledger. The ledger is retained so cost reporting can recover design runs that committed token data but never finalized `token-report-final.json` (the reader-side fallback in `report_tokens_scan.py`; issue #5133).
- The consumer-core keep set for `/review` dirs includes `manifest.json`, `final-summary.md`, `difficulty-rating.json`, and `checks-digest-sizes.tsv`, so digest savings telemetry survives default slimming before enough samples accrue.
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

- `/report-tokens` (both skills): full cost-trend history is preserved indefinitely because it reads exactly the keep-set files. For `/design`, runs that never finalized `token-report-final.json` are priced from the retained `larch-tokens-*.jsonl` ledger fallback (committed vendor lanes only; the main-agent Claude lane lives in the uncommitted transcript and is not recoverable).
- `/difficulty-calibration`: reads `difficulty-rating.json`, classification TSVs, JSONL/NDJSON fallback findings, token/timing reports, and `rejected-analysis-verdicts.tsv`. It tolerates gc-slimmed dirs and pre-initiative gaps. Non-escalated runs without a parseable classification source report realized tier `unknown`. It is read-only and produces no run-log batches.
- `audit-runs`: targets recent batches within the retention window; aged dirs carry the `gc-slimmed` marker for honest scan reporting.

## Authoritative sources

- `docs/run-log-cli.md` — `run-log` verb contracts, log-root resolution, redaction rules
- `docs/run-log-batches.md` — canonical batch slug table (extension, mode, sanitizer)
- `docs/summary-comment-template.md` — marker literals and comment contracts
## Concise prune/log audit update

Concise review logs now use `round-meta.json` `reviewer_signals[]` for reviewer output audit scans instead of committing raw transcripts by default. Implement rounds include `prune-decision.env` and `prune-nit.env`; design plan-review rounds default to the four-file concise contract while keeping run-root `plan.txt`.

## /design failure-report artifacts

`/design` auto-reporting writes `design-failure-*.env` and `design-failure-*.md` artifacts under `$DESIGN_TMPDIR`. Important artifacts include terminal state, terminal report sentinels, escalation-success sentinels, operator-action sentinels, escalation ledgers, fallback chat print, operator-action chat audit, captured helper stdout/stderr sidecars, root-cause files, bounded root-cause files, and sensitive-corpus files.

`design-failure-terminal-state.env` is the terminal-state KV contract. Report helper stdout/stderr captures are retained beside `final-summary.md` so the summary body stays free of helper KVs.

## Reconciling stuck design-log PRs

`/design` opens one `chore(larch-logs):` design-run PR per run (title prefix `chore(larch-logs):` followed by `design run <RUN_ID>`, head branch `larch-logs/design-<RUN_ID>`) and spawns a **detached, best-effort** `ship design-log` waiter to admin-merge it once required CI passes. That waiter does not reliably survive the session that launched it, so design-log PRs can accumulate unmerged.

`python3 python/cli.py ship design-log-sweep` is the durable backstop. It lists open PRs that carry **both** the `chore(larch-logs):` title prefix **and** a `larch-logs/` head branch, then admin-squash-merges the ones whose required checks are green. PRs that are still pending or failing are left for a later sweep, and already-merged PRs are skipped. The admin merge bypasses only the review gate the automated PR can never satisfy; the no-bypass CI ruleset still blocks merging red CI.

- Runs under the operator's `gh` auth, so it requires admin merge rights.
- `--dry-run` reports the per-PR outcome without merging.
- `--repo OWNER/REPO` targets a specific repo; otherwise the repo is resolved from the working tree.
- Emits `SWEEP_TOTAL`, `SWEEP_MERGED`, `SWEEP_ALREADY_MERGED`, `SWEEP_SKIPPED`, and `SWEEP_FAILED` counters; exit code is `1` when any green PR failed to merge, else `0`.

**Automatic trigger:** `scripts/sweep-design-logs.sh` is a SessionStart hook (wired in `hooks/hooks.json`) that launches the sweep as a detached background process at every `startup`, `resume`, `clear`, and `compact` session event. Output is captured to a per-invocation temp log (`larch-sweep-design-logs-<PID>.log`) for post-hoc debugging. The hook always exits 0 and never blocks session start. To run the sweep manually: `python3 python/cli.py ship design-log-sweep`.

## Rejected-analysis ledger and verdict sidecar

`larch-logs/rejected-analysis-ledger.tsv` is the committed idempotency ledger for `/rejected-analysis`. It records deterministic drops, verification outcomes, stale or already-fixed results, dirty-tree rejects, security-sensitive skips, cap drops, near-duplicate `alias_of` links, filed issue numbers, and deduplicated issue mappings. The primary key is `finding_hash`, computed from normalized `file_path` plus normalized `concern` only. `line_hint`, `FINDING_N`, run id, round, voter slots, and filesystem state do not participate in the hash.

`larch-logs/rejected-analysis-verdicts.tsv` is the committed sidecar when verifier verdicts exist. It carries `finding_hash`, source skill, run id, round, finding id, dissenting slots, verifier verdict, re-checked location, evidence, and triage time for downstream diagnostics, `/voter-calibration` false-negative labels, and `/difficulty-calibration` under-rating annotations.

`/difficulty-calibration` reads `difficulty-rating.json`, classification TSVs, `review-findings-full.jsonl` or `review-findings.ndjson` fallbacks, token/timing reports, and the verdict sidecar from committed logs. It tolerates gc-slimmed dirs and missing pre-initiative artifacts. Non-escalated runs without a parseable classification source report realized tier `unknown`. The analyzer is read-only and writes no run-log batches.

The collector reads implement artifacts from `larch-logs/implement/<run>/round-*/review-findings-full.jsonl` with `round-*/findings-classification.tsv`, falling back to the run-root JSONL only when no round-local JSONL exists. It reads standalone review artifacts from `larch-logs/review/<run>/review-findings.ndjson` with `review-findings-classification-round-*.tsv`, using `review-findings-full.jsonl` only as a fallback.

Each run work dir also contains non-committed `ingest-status.jsonl`. One row is appended per verifier launch attempt. `launch-failed` rows stay retryable and are not ledgered as verification failures. `parse-failed`, `location-mismatch`, `dirty-tree`, stale, and already-fixed rows are terminal dispositions. `issue-cluster-map.json` maps `/issue` batch indexes to finding hashes so record can map created and deduplicated issues without parsing issue prose.
