# tally-code-votes.sh

**Type**: executable script.

**Purpose**: Tally `/review` code-review votes from a 3-judge panel and emit accepted/rejected/OOS findings plus a per-finding scoreboard. Replaces the older `tally-votes.sh` which presumed 2 voter files that no script ever wrote — hence every finding silently auto-accepted (the bug this PR closes).

Sources `${CLAUDE_PLUGIN_ROOT}/scripts/lib-vote-tally.sh` for `vote_for_id`, `reviewer_for_block`, `is_security_block`, `accept_finding`, `classify_result`, and `split_ballot_to_blocks`. The same library backs `skills/design/scripts/tally-plan-review.sh`, so the threshold rules and security-tag detection cannot drift between code review and plan review.

## Args

| Flag | Type | Required | Description |
|---|---|---|---|
| `--ballot-file FILE` | path | yes | Markdown file containing ballot blocks keyed by `### FINDING_N:` and, for OOS items, either legacy `[OUT_OF_SCOPE]` `FINDING_N` headings or direct `### OOS_N:` headings. |
| `--voter-files FILE...` | path list | no | Vote-output files (typically `cursor-vote-output.txt`, `codex-vote-output.txt`, `claude-vote-output.txt`). Each voter file contains lines like `FINDING_N: YES`, `FINDING_N: NO — reason`, `FINDING_N: EXONERATE — reason`, or `OOS_N: ...` when the ballot uses direct `OOS_N` headings. Zero files triggers `TALLY_STATUS=main-agent-vote-required`. |
| `--review-tmpdir DIR` | path | yes | Output directory for all artifacts. |
| `--session-env-path FILE` | path | no | When non-empty, OOS-accepted is also written to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-review.md` so `/implement` Step 9a.1 can find it. |
| `--scope-files FILE` | path | no | File containing changed file names (one per line, from `git diff --name-only`). When non-empty, enables the scope-fit gate on the block heading line (first line of each `### FINDING_N:` block): tokens matching the extended-regex pattern `[a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+:[0-9]+` yield file paths after stripping the trailing `:line` suffix. If the heading has no such token, the gate skips (keeps in-scope). If every extracted path is absent from both this file and (when provided) `--plan-file`, the finding is reclassified as OOS (`OUT_OF_SCOPE_DRIFT`). When absent or empty, the gate is a no-op (backward compatible). |
| `--plan-file FILE` | path | no | Implementation plan file. When provided alongside `--scope-files`, the gate exempts any finding whose location file is mentioned anywhere in the plan. |
| `--manifest-file FILE` | path | no | Panel manifest NDJSON. When provided, the tally writes `$REVIEW_TMPDIR/scout-archetype-yield.tsv` with per-archetype finding yield metrics; combined with `--collector-results-file`, dead-slot rows are appended to the reviewer competition scoreboard. |
| `--collector-results-file FILE` | path | no | KV records file written by `scripts/collect-agent-results.sh` (blank-line-separated STATUS per reviewer). When provided alongside `--manifest-file`, the tally appends a row for each manifest entry that produced no score rows (including dynamic slots), showing 0 counts and `STATUS=<status>`. Manifest entries missing collector status default to `STATUS=OK`, matching zero-finding slots that ran successfully. |
| `--not-substantive-count N` | non-negative int | no | When > 0, the tally header emits a degraded-panel banner noting N reviewer slot(s) produced narrative-only output. Forwarded by `review-core.sh` from `check-reviewer-failure-threshold.sh`'s `NOT_SUBSTANTIVE_SLOTS` output. |
| `--cursor-available true\|false` | enum | no | Forwarded from review-core for context (currently informational only). |
| `--codex-available true\|false` | enum | no | Same as above. |
| `--both-down true\|false` | enum | no | Deprecated compatibility flag. When `true`, maps to the same 0-judge `main-agent-vote-required` path as an empty voter-file set. Default: `false`. |

## Output artifacts

- `voting-tally.md` — per-item table (`Item | YES | NO | EXON | JERR | Result`) plus reviewer competition scoreboard.
- `findings-classification.tsv` when `REVIEW_TMPDIR` is nested under `$IMPLEMENT_TMPDIR/round-N`, or `findings-classification-round-N.tsv` for standalone `/review --diff` rounds. Schema: `finding_id`, `reviewer_slots`, `voting_result`, then `v1_vote`, `v1_correctness`, `v1_severity`, `v1_quality`, `v1_uncertain` through `v3_*`. Voter columns follow compact `EFFECTIVE_VOTER_FILES` order, so failed slots do not leave positional holes.
- `accepted-findings.md` — accepted FINDING_N blocks (in-scope only; OOS items go to a separate file).
- `rejected-findings.md` — non-accepted in-scope findings rendered under `### [rejected] FINDING_N` with a short **Rejected subtype** line, plus `Vote tally: YES=… NO=… EXON=… JUDGE_ERROR=…` appended.
- `oos-accepted-review.md` — accepted OOS blocks with the security-tag filter applied (security-tagged OOS items are held locally only, never filed publicly).
- `oos.md` — all OOS items (accepted and not), with vote tallies.
- `review-tally.env` — per-block `FINDING_N_ACCEPTED=true|false`, `FINDING_N_OUTCOME=accepted|rejected`, optional `FINDING_N_REJECTED_SUBTYPE=<neutral|exonerated|true_rejected>` for non-accepted rows, plus the same `OOS_N_ACCEPTED` / `OOS_N_OUTCOME` / optional `OOS_N_REJECTED_SUBTYPE` key family for direct OOS headings, and summary counters (`ACCEPTED_COUNT`, `REJECTED_COUNT`, `EXONERATED_COUNT`, `NEUTRAL_COUNT`, `OOS_ACCEPTED_COUNT`, `OOS_REJECTED_COUNT`).
- `scout-archetype-yield.tsv` — written when `--manifest-file` is provided. Schema: `archetype_name`, `focus_area`, `weight`, `findings_total`, `findings_accepted`, `findings_rejected`, `yield_ratio`.
- Reviewer competition scoreboard score formula: `accepted + oos_accepted - rejected - oos_rejected`; rendered OOS columns are `OOS-Proposed`, `OOS-Accepted`, `OOS-Exonerated`, and `OOS-Rejected`.

Manifest attribution maps output basenames, not slot IDs. Fallback basenames normalize `-phase2`, `-phase3`, and `-retry` suffixes before lookup, so `dyn-foo-output-phase2.txt` joins to manifest output `dyn-foo-output.txt`. Static specialist rows map to slugs such as `structure` and focus areas from the canonical enum. Dynamic rows use the manifest `dyn-<name>` slot, `focus_area`, and scout `weight`; `codex-generalist-output.txt` maps to `generic`, `code-quality`, weight `1`.

## stdout (FD 3 via `emit_kv`)

| Key | Description |
|---|---|
| `TALLY_STATUS` | `ok` on normal tally; `main-agent-vote-required` when 0 judges are available. |
| `ACCEPTED_COUNT` | In-scope findings with outcome `accepted`. |
| `REJECTED_COUNT` | In-scope findings that did not meet the acceptance threshold (includes split-panel and exonerated patterns for operator-facing totals). |
| `EXONERATED_COUNT` | In-scope informational sub-count: vote pattern matches the exonerated carve-out (`YES>0`, `NO==0`, `EXONERATE>0`) while still not meeting acceptance. |
| `NEUTRAL_COUNT` | Internal scoreboard accounting: vote pattern `YES>0` and `YES==NO` (split panel). |
| `OOS_ACCEPTED_COUNT` | OOS items accepted (excluding security-tagged). |
| `OOS_REJECTED_COUNT` | OOS items not accepted. |
| `OUT_OF_SCOPE_DRIFT_COUNT` | In-scope findings reclassified to OOS by the scope-fit gate. Emitted as `0` when `--scope-files` is absent, empty, or unreadable, and on the `main-agent-vote-required` early-exit path. |
| `VOTING_TALLY_FILE` | Absolute path to `voting-tally.md`. |
| `TALLY_FILE` | Absolute path to `review-tally.env`. |
| `ACCEPTED_FINDINGS_FILE` | Absolute path to `accepted-findings.md`. |
| `REJECTED_FINDINGS_FILE` | Absolute path to `rejected-findings.md`. |
| `OOS_ACCEPTED_FILE` | Absolute path to OOS-accepted file (parent-dir copy when `SESSION_ENV_PATH` is set). |
| `OOS_FILE` | Absolute path to `oos.md`. |
| `TALLY_OK` | Always `true` on success. |
| `ELIGIBLE_VOTER_COUNT` | Raw voter file count after `--both-down` compatibility handling and before parse-rate degradation. |
| `VOTER_COUNT` | Effective quorum count after removing parse-rate-degraded narrative-only voter slots. |
| `VOTING_SKIPPED_WARNING` | Present on the 0-judge main-agent path. |
| `YIELD_TSV_FILE` | Present when `--manifest-file` produces `scout-archetype-yield.tsv`. |
| `FINDINGS_CLASSIFICATION_TSV_FILE` | Present whenever the forensic vote/rating TSV is written, including 0-judge and zero-finding paths. |

## Findings Classification TSV

`finding_id` is the literal ballot ID (`FINDING_N` or `OOS_N`). `reviewer_slots` is the `|`-delimited reviewer attribution with delimiter whitespace stripped. `voting_result` is the same `classify_result` enum used by the tally (`accepted`, `rejected`, `exonerated`, `neutral`) for both in-scope and OOS rows.

Each `vN_*` group is ordered by effective voter-file iteration order after parse-rate-degraded voters are removed. Votes are `YES`, `NO`, `EXONERATE`, or `JUDGE_ERROR`; missing or unparseable ballot lines are normalized to `JUDGE_ERROR` for effective voter slots. Rating axes are enum-only; missing or unrecognized axis values are recorded as empty and force `vN_uncertain=true`.

When `TALLY_STATUS=main-agent-vote-required` (0 effective judges), data rows keep
`voting_result=rejected` only as a placeholder TSV sentinel so the forensic
export has a stable enum. The actual adjudication outcome is deferred to the
main-agent path and is reflected in the accepted/rejected/OOS artifact files
rather than this degraded-round TSV.

Single-parse invariant: the TSV and markdown tally both derive each per-voter vote from a single call to `scripts/parse-judge-vote-and-rating.sh`. `vote_for_id` remains the legacy library helper, but the forensic TSV contract is keyed to the parser output so tally counts and `vN_vote` cells cannot drift under missing-line or malformed-line cases.

## Threshold (delegated to lib-vote-tally.sh)

- `effective >= 3` → `yes >= 2` accepts.
- `effective == 2` → unanimous `yes == 2` accepts.
- `effective == 1` → single-judge binding decision (`YES` accepts; `NO` rejects; `EXONERATE` is exonerated but not accepted).
- `effective == 0` → no automated vote; emit `TALLY_STATUS=main-agent-vote-required`, leave accepted/rejected counts at 0, and require main-agent adjudication.

The quorum basis is the panel-level effective voter count (`VOTER_COUNT`), not the per-finding non-`JUDGE_ERROR` vote count. `ELIGIBLE_VOTER_COUNT` captures the raw voter file count, while `VOTER_COUNT` removes parse-rate-degraded narrative-only voter slots before tallying. Per-judge `JUDGE_ERROR` fallbacks or missing per-item votes within the effective panel do not reduce a 3-judge panel to a lower tier.

## Callers

- `skills/review/scripts/review-core.sh` — invoked after `dispatch-code-voters.sh` produces the three vote-output files. `review-core.sh` references the resolved path via `REVIEW_CORE_TALLY_VOTES_SH` env var (renamed to point at `tally-code-votes.sh`).

## Harness

`skills/review/scripts/test-tally-code-votes.sh` covers: 3-voter 2-YES accept, 3-voter 1-YES reject with per-judge `JUDGE_ERROR` fallbacks, 2-voter unanimous and non-unanimous paths, single-judge YES/NO/EXONERATE, 0-judge main-agent-required, deprecated `--both-down`, OOS handling with `[OUT_OF_SCOPE]` title prefix, rejected-OOS scoring, security-tag filtering on accepted OOS, the scope-fit gate (diff-only list, plan exemption, no-op without `--scope-files`), and `--manifest-file` yield TSV/scoreboard attribution including dynamic fallback basename normalization, dynamic zero-finding scoreboard rows, `STATUS=OK` fallback, and generalist mapping.
