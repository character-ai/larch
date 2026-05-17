# tally-code-votes.sh

**Type**: executable script.

**Purpose**: Tally `/review` code-review votes from a 3-judge panel and emit accepted/rejected/OOS findings plus a per-finding scoreboard. Replaces the older `tally-votes.sh` which presumed 2 voter files that no script ever wrote — hence every finding silently auto-accepted (the bug this PR closes).

Sources `${CLAUDE_PLUGIN_ROOT}/scripts/lib-vote-tally.sh` for `vote_for_id`, `reviewer_for_block`, `is_security_block`, `accept_finding`, `classify_result`, and `split_ballot_to_blocks`. The same library backs `skills/design/scripts/tally-plan-review.sh`, so the threshold rules and security-tag detection cannot drift between code review and plan review.

## Args

| Flag | Type | Required | Description |
|---|---|---|---|
| `--ballot-file FILE` | path | yes | Markdown file containing one `### FINDING_N:` block per finding. OOS items are indicated by `[OUT_OF_SCOPE]` in the title heading line — same convention `collect-findings.sh` already emits. |
| `--voter-files FILE...` | path list | yes | Vote-output files (typically `cursor-vote-output.txt`, `codex-vote-output.txt`, `claude-vote-output.txt`). Each voter file contains lines like `FINDING_N: YES`, `FINDING_N: NO — reason`, `FINDING_N: EXONERATE — reason`. |
| `--review-tmpdir DIR` | path | yes | Output directory for all artifacts. |
| `--session-env-path FILE` | path | no | When non-empty, OOS-accepted is also written to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-review.md` so `/implement` Step 9a.1 can find it. |
| `--cursor-available true\|false` | enum | no | Forwarded from review-core for context (currently informational only). |
| `--codex-available true\|false` | enum | no | Same as above. |
| `--both-down true\|false` | enum | no | When `true`, voting is bypassed and all findings auto-accepted. Used when both external reviewers were unavailable in the same round. Default: `false`. |

## Output artifacts

- `voting-tally.md` — per-item table (`Item | YES | NO | EXON | NEUT | Result`) plus reviewer competition scoreboard.
- `accepted-findings.md` — accepted FINDING_N blocks (in-scope only; OOS items go to a separate file).
- `rejected-findings.md` — rejected/neutral/exonerated blocks with `Vote tally: YES=… NO=… EXON=… NEUTRAL=…` appended.
- `oos-accepted-review.md` — accepted OOS blocks with the security-tag filter applied (security-tagged OOS items are held locally only, never filed publicly).
- `oos.md` — all OOS items (accepted and not), with vote tallies.
- `review-tally.env` — `FINDING_N_ACCEPTED=true|false` keys for each block.
- Reviewer competition scoreboard score formula: `accepted + oos_accepted - rejected - oos_rejected`; rendered OOS columns are `OOS-Proposed`, `OOS-Accepted`, `OOS-Neutral/Exon`, and `OOS-Rejected`.

## stdout (FD 3 via `emit_kv`)

| Key | Description |
|---|---|
| `ACCEPTED_COUNT` | In-scope findings accepted. |
| `REJECTED_COUNT` | In-scope findings not accepted. |
| `OOS_ACCEPTED_COUNT` | OOS items accepted (excluding security-tagged). |
| `OOS_REJECTED_COUNT` | OOS items not accepted. |
| `VOTING_TALLY_FILE` | Absolute path to `voting-tally.md`. |
| `TALLY_FILE` | Absolute path to `review-tally.env`. |
| `ACCEPTED_FINDINGS_FILE` | Absolute path to `accepted-findings.md`. |
| `REJECTED_FINDINGS_FILE` | Absolute path to `rejected-findings.md`. |
| `OOS_ACCEPTED_FILE` | Absolute path to OOS-accepted file (parent-dir copy when `SESSION_ENV_PATH` is set). |
| `OOS_FILE` | Absolute path to `oos.md`. |
| `TALLY_OK` | Always `true` on success. |
| `VOTER_COUNT` | Voter file count. |
| `VOTING_SKIPPED_WARNING` | Present iff fewer than 2 judges available OR both-down. |

## Threshold (delegated to lib-vote-tally.sh)

- `eligible >= 3` → `yes >= 2` accepts.
- `eligible == 2` → unanimous `yes == 2` accepts.
- `eligible <  2` → all findings auto-accepted with `VOTING_SKIPPED_WARNING`.
- `--both-down true` → all findings auto-accepted with `VOTING_SKIPPED_WARNING` (no judges launched).

## Callers

- `skills/review/scripts/review-core.sh` — invoked after `dispatch-code-voters.sh` produces the three vote-output files. `review-core.sh` references the resolved path via `REVIEW_CORE_TALLY_VOTES_SH` env var (renamed to point at `tally-code-votes.sh`).

## Harness

`skills/review/scripts/test-tally-code-votes.sh` covers: 3-voter 2-YES accept, 3-voter 1-YES reject, 2-voter unanimous accept, 1-voter skip path, both-down, OOS handling with `[OUT_OF_SCOPE]` title prefix, rejected-OOS scoring, security-tag filtering on accepted OOS.
