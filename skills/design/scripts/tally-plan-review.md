# tally-plan-review.sh

## Purpose

`tally-plan-review.sh` is the design-local plan-review vote tally. It parses `### FINDING_N:` and `### OOS_N:` blocks from a ballot file, reads explicit voter outputs, writes plan-review artifacts under `$DESIGN_TMPDIR`, and renders the reviewer competition scoreboard.

## Primary Callers

- `skills/design/scripts/design-driver.sh` for `ACTION=TALLY`
- `/design` Step 3 after `dispatch-plan-voters.sh` returns Voter 2/3 output paths

## Invariants

- Required arguments are `--ballot-file FILE` and `--design-tmpdir DIR`.
  Voters are passed with repeatable `--voter <SLOT>:<PATH>` where `SLOT` is
  `Claude`, `Codex`, `Cursor`, or `MainAgent`. `--voter-files FILE...` remains
  as a transition fallback and emits `deprecated: --voter-files; use --voter
  <SLOT>:<PATH>` to stderr.
- `--voter` and `--voter-files` are mutually exclusive. Mixed usage exits
  non-zero with `error: --voter and --voter-files are mutually exclusive`.
- Invalid `--voter` slot values exit non-zero with
  `error: invalid voter slot: <value> (must be Claude|Codex|Cursor|MainAgent)`.
- `--voter MainAgent:<PATH>` is valid only as the sole voter for the 0-judge
  fallback path. It is not mapped to any `vN_*` columns; TSV rows keep the
  `vN_*` cells empty and keep `voting_result=rejected` for every row even
  though the normal accepted / rejected / OOS artifacts still reflect the
  MainAgent adjudication result.
  Mixed MainAgent usage exits with `error: --voter MainAgent is only valid as
  the sole voter (0-judge fallback path)`.
- `--findings-classification-out FILE` writes the forensic TSV to an explicit
  path. When omitted, the default is
  `$DESIGN_TMPDIR/plan-review/round-1/findings-classification.tsv`; the tally
  creates the parent directory before writing.
- The parser supports design-local `### FINDING_N:` and `### OOS_N:` blocks. Voter files use anchored `ID: VOTE` lines (e.g. `FINDING_1: YES`); substring matching is rejected to prevent `FINDING_10` matching inside `FINDING_100`.
- `TALLY_PLAN_REVIEW_STATUS` is emitted on every exit path. Success paths emit `ok` or `main-agent-vote-required`. Every non-zero exit, including argv, ballot, and voter-validation paths, emits `tally-error` via the cleanup EXIT trap. Callers must parse `TALLY_PLAN_REVIEW_STATUS` from stdout to disambiguate; the script's exit code remains the primary signal.
- Acceptance threshold comes from `scripts/lib-vote-tally.sh::classify_result`: 3+ eligible voters require 2+ YES; 2 eligible voters require unanimous YES; 1 eligible voter is a binding single-judge decision; 0 eligible voters emit `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` for main-agent adjudication.
- The quorum basis is the panel-level available voter count, not the per-finding non-`JUDGE_ERROR` response count. Per-judge `JUDGE_ERROR` fallbacks do not reduce the tier.
- Accepted in-scope findings are written to `accepted-plan-findings.md`.
- Non-accepted in-scope findings are written to `rejected-findings.md`.
- OOS visibility output is written to `oos.md`.
- Accepted OOS output is written to `oos-accepted-design.md` under `$DESIGN_TMPDIR`.
- Accepted OOS blocks with an unfenced `focus-area = security` token are excluded from all public OOS outputs. Fenced occurrences (inside backtick or triple-backtick regions) are not load-bearing (Match discrimination false-positive guard).
- Scoreboard score formula: `accepted + oos_accepted - rejected - oos_rejected` (+1 per accepted item, -1 per rejected item).
- The rendered scoreboard columns are `Reviewer`, `Proposed`, `Accepted`, `Exonerated`, `Rejected`, `OOS-Proposed`, `OOS-Accepted`, `OOS-Exonerated`, `OOS-Rejected`, and `Score`.
- Whenever `--design-tmpdir` has been validated, `voting-tally.md` is materialized with at least the degraded header (`# Plan Review Voting Tally` plus a one-line abort note) before any non-zero exit. The missing-required-args and unknown-argument branches are exempt because `$DESIGN_TMPDIR` may be empty.
- `mkdir -p "$DESIGN_TMPDIR"` runs as the first action after argv validation so all subsequent exit paths (including the ballot/voter-unreadable and split-failure branches) can safely write to it.
- The forensic TSV has exactly 21 tab-separated fields per row:
  `finding_id`, `finding_reviewers`, `voting_result`, then for v1/v2/v3:
  `vote`, `correctness`, `severity`, `quality`, `uncertain`, `tool`.
  Header:

```text
finding_id \t finding_reviewers \t voting_result \t v1_vote \t v1_correctness \t v1_severity \t v1_quality \t v1_uncertain \t v1_tool \t v2_vote \t v2_correctness \t v2_severity \t v2_quality \t v2_uncertain \t v2_tool \t v3_vote \t v3_correctness \t v3_severity \t v3_quality \t v3_uncertain \t v3_tool
```

- `finding_reviewers` is ballot-proposer attribution from
  `reviewer_for_block`; `vN_tool` is the actual runtime voter tool identity
  supplied by `--voter`.
- With explicit `--voter`, non-`MainAgent` slots preserve the canonical
  positions implied by the declared slot label (`Claude` -> `v1_*`, `Codex` ->
  `v2_*`, `Cursor` -> `v3_*`). Misleading basenames do not override the
  declared slot. Middle failed slots therefore remain empty instead of
  compacting later voters leftward.
- With legacy `--voter-files`, slot placement still uses basename/tool
  heuristics (`slotN`/canonical tool names first, then first free slot) because
  tool identity must be inferred from the file path. This file is the schema
  authority for `vN_tool` and slot semantics.
- Rows are emitted in numeric `FINDING_*` order first, then numeric `OOS_*`
  order. Missing judge positions preserve empty cells, including trailing
  empties, so every data row remains 21 fields.
- Every voter-sourced cell and `finding_reviewers` is normalized with
  `tr '\t\n' '  '` before TSV write; tabs/newlines become spaces rather than
  being deleted.
- Severity is parsed from voter output by
  `scripts/parse-judge-vote-and-rating.sh` and written verbatim to the v1/v2/v3
  severity columns of the 21-field forensic TSV. No transform other than the
  documented `tr '\t\n' '  '` whitespace normalization is permitted between
  parser and TSV.
- `scripts/parse-judge-vote-and-rating.sh` parses the extended rating axes for
  each voter and ballot id. `vN_vote` is sourced from
  `scripts/lib-vote-tally.sh::vote_for_id` so the forensic TSV and
  `voting_result` share one vote parser.

## Per-round `--design-tmpdir` Routing

Callers may pass a per-round subdirectory as `--design-tmpdir`. The tally writes `voting-tally.md`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, and the forensic TSV selected by `--findings-classification-out` inside that directory. When `--findings-classification-out` is omitted, the backward-compatible default still suffixes `plan-review/round-1/findings-classification.tsv` to the design tmpdir; multi-round callers must pass `--findings-classification-out` explicitly per round. `skills/design/scripts/plan-review-loop.sh` already does so.

## Makefile Wiring

The regression harnesses are `make test-tally-plan-review` and
`make test-findings-classification`, both wired into `test-harnesses-9`.

## Harness

`test-tally-plan-review.sh` covers all-yes, mixed votes, split-panel ties, single-judge YES/NO/EXONERATE, 0-judge main-agent-required, sole-MainAgent adjudication reruns, explicit `--voter` slot preservation, no quorum reduction for per-judge `JUDGE_ERROR` fallbacks, OOS accepted/rejected, security-tagged OOS exclusion, scoreboard rendering, malformed-ballot abort tally stub, and missing-ballot abort tally stub.

`test-findings-classification.sh` covers complete ratings, canonical-position
`--voter` slot filling, legacy `--voter-files` basename fallback, missing
judges, partial rows, 0-judge and 0-finding TSVs, overwrite behavior, OOS
rows, anchored-vote compatibility, unrecognized votes, lowercase-only axis
values, duplicate ID last-line-wins, lowercased ballot ids, tab normalization,
sorted row order, rationale delimiter scoping, cross-parser vote parity,
quiet-mode parser capture, MainAgent rules, argv mutual exclusion, invalid
slots, legacy deprecation, malicious parser-cell sanitization, and 21-field row preservation.

## Edit In Sync

Update this contract, `test-tally-plan-review.sh`, `skills/design/SKILL.md`, and `skills/design/references/plan-review.md` together when ballot or artifact formats change.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
