# tally-code-votes.sh

**Type**: executable script.

**Purpose**: Tally `/review` code-review votes from a 3-judge panel and emit accepted/rejected/OOS findings plus a per-finding scoreboard. Replaces the older `tally-votes.sh` which presumed 2 voter files that no script ever wrote — hence every finding silently auto-accepted (the bug this PR closes).

Sources `${CLAUDE_PLUGIN_ROOT}/scripts/lib-vote-tally.sh` for `vote_for_id`, `reviewer_for_block`, `is_security_block`, `accept_finding`, `classify_result`, and `split_ballot_to_blocks`. The same library backs `skills/design/scripts/tally-plan-review.sh`, so the threshold rules and security-tag detection cannot drift between code review and plan review.

## Args

| Flag | Type | Required | Description |
|---|---|---|---|
| `--ballot-file FILE` | path | yes | Markdown file containing one `### FINDING_N:` block per finding. OOS items are indicated by `[OUT_OF_SCOPE]` in the title heading line — same convention `collect-findings.sh` already emits. |
| `--voter-files FILE...` | path list | no | Vote-output files (typically `cursor-vote-output.txt`, `codex-vote-output.txt`, `claude-vote-output.txt`). Each voter file contains lines like `FINDING_N: YES`, `FINDING_N: NO — reason`, `FINDING_N: EXONERATE — reason`. Zero files triggers `TALLY_STATUS=main-agent-vote-required`. |
| `--review-tmpdir DIR` | path | yes | Output directory for all artifacts. |
| `--session-env-path FILE` | path | no | When non-empty, OOS-accepted is also written to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-review.md` so `/implement` Step 9a.1 can find it. |
| `--scope-files FILE` | path | no | File containing changed file names (one per line, from `git diff --name-only`). When non-empty, enables the scope-fit gate on the block heading line (first line of each `### FINDING_N:` block): tokens matching the extended-regex pattern `[a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+:[0-9]+` yield file paths after stripping the trailing `:line` suffix. If the heading has no such token, the gate skips (keeps in-scope). If every extracted path is absent from both this file and (when provided) `--plan-file`, the finding is reclassified as OOS (`OUT_OF_SCOPE_DRIFT`). When absent or empty, the gate is a no-op (backward compatible). |
| `--plan-file FILE` | path | no | Implementation plan file. When provided alongside `--scope-files`, the gate exempts any finding whose location file is mentioned anywhere in the plan. |
| `--cursor-available true\|false` | enum | no | Forwarded from review-core for context (currently informational only). |
| `--codex-available true\|false` | enum | no | Same as above. |
| `--both-down true\|false` | enum | no | Deprecated compatibility flag. When `true`, maps to the same 0-judge `main-agent-vote-required` path as an empty voter-file set. Default: `false`. |

## Output artifacts

- `voting-tally.md` — per-item table (`Item | YES | NO | EXON | NEUT | Result`) plus reviewer competition scoreboard.
- `accepted-findings.md` — accepted FINDING_N blocks (in-scope only; OOS items go to a separate file).
- `rejected-findings.md` — only findings with outcome `rejected` (strictly voted down), with `Vote tally: YES=… NO=… EXON=… NEUTRAL=…` appended. Exonerated and neutral findings are counted but not written here.
- `oos-accepted-review.md` — accepted OOS blocks with the security-tag filter applied (security-tagged OOS items are held locally only, never filed publicly).
- `oos.md` — all OOS items (accepted and not), with vote tallies.
- `review-tally.env` — per-block `FINDING_N_ACCEPTED=true|false` and `FINDING_N_OUTCOME=<accepted|rejected|exonerated|neutral>` keys, plus summary counters (`ACCEPTED_COUNT`, `REJECTED_COUNT`, `EXONERATED_COUNT`, `NEUTRAL_COUNT`, `OOS_ACCEPTED_COUNT`, `OOS_REJECTED_COUNT`).
- Reviewer competition scoreboard score formula: `accepted + oos_accepted - rejected - oos_rejected`; rendered OOS columns are `OOS-Proposed`, `OOS-Accepted`, `OOS-Neutral/Exon`, and `OOS-Rejected`.

## stdout (FD 3 via `emit_kv`)

| Key | Description |
|---|---|
| `TALLY_STATUS` | `ok` on normal tally; `main-agent-vote-required` when 0 judges are available. |
| `ACCEPTED_COUNT` | In-scope findings with outcome `accepted`. |
| `REJECTED_COUNT` | In-scope findings with outcome `rejected` (voted down) only; does not include exonerated or neutral. |
| `EXONERATED_COUNT` | In-scope findings with outcome `exonerated` (valid but not worth implementing in this PR). |
| `NEUTRAL_COUNT` | In-scope findings with outcome `neutral` (tied vote, no clear consensus). |
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
| `VOTER_COUNT` | Voter file count. |
| `VOTING_SKIPPED_WARNING` | Present on the 0-judge main-agent path. |

## Threshold (delegated to lib-vote-tally.sh)

- `eligible >= 3` → `yes >= 2` accepts.
- `eligible == 2` → unanimous `yes == 2` accepts.
- `eligible == 1` → single-judge binding decision (`YES` accepts; `NO` rejects; `EXONERATE` is exonerated but not accepted).
- `eligible == 0` → no automated vote; emit `TALLY_STATUS=main-agent-vote-required`, leave accepted/rejected counts at 0, and require main-agent adjudication.

The quorum basis is the panel-level eligible voter count (number of non-failed voter files), not the per-finding non-neutral vote count. NEUTRAL or missing per-item votes do not reduce a 3-judge panel to a lower tier.

## Callers

- `skills/review/scripts/review-core.sh` — invoked after `dispatch-code-voters.sh` produces the three vote-output files. `review-core.sh` references the resolved path via `REVIEW_CORE_TALLY_VOTES_SH` env var (renamed to point at `tally-code-votes.sh`).

## Harness

`skills/review/scripts/test-tally-code-votes.sh` covers: 3-voter 2-YES accept, 3-voter 1-YES reject with NEUTRAL abstentions, 2-voter unanimous and non-unanimous paths, single-judge YES/NO/EXONERATE, 0-judge main-agent-required, deprecated `--both-down`, OOS handling with `[OUT_OF_SCOPE]` title prefix, rejected-OOS scoring, security-tag filtering on accepted OOS, and the scope-fit gate (diff-only list, plan exemption, no-op without `--scope-files`).
