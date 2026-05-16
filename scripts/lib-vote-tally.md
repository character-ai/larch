# lib-vote-tally.sh

**Type**: sourced-only shared library (no shebang).

**Purpose**: Owns the cross-skill voting primitives shared between `/design` plan-review (`skills/design/scripts/tally-plan-review.sh`) and `/review` code-review (`skills/review/scripts/tally-code-votes.sh`) tally scripts. Single source of truth so the threshold rules and security-tag detection do not drift between callers.

## API

| Function | Inputs | Output | Exit |
|---|---|---|---|
| `vote_for_id <id> <voter_file>` | finding/oos id (e.g. `FINDING_3`), voter output file | stdout: `YES` \| `NO` \| `EXONERATE` \| `NEUTRAL` | 0 |
| `reviewer_for_block <block_file>` | per-block markdown file | stdout: reviewer attribution string (or `unknown`) | 0 |
| `is_security_block <block_file>` | per-block markdown file | — | 0 (security tag found, unfenced) \| 1 (not found) |
| `accept_finding <yes> <no> <exonerate> <eligible>` | vote counts and eligible voter count | — | 0 (accept) \| 1 (reject) |
| `split_ballot_to_blocks <ballot_file> <out_dir>` | ballot file, output dir | per-ID `<id>.md` files in `out_dir` | 0 |
| `classify_result <yes> <no> <exonerate> <eligible>` | vote counts and eligible voter count | stdout: `accepted` \| `rejected` \| `neutral` \| `exonerated` | 0 |

## Threshold

`accept_finding` thresholds:

- `eligible >= 3` → `yes >= 2` accepts.
- `eligible == 2` → `yes == 2` (unanimous) accepts.
- `eligible <  2` → never accepts (caller falls back to accept-all per skill-specific policy).

## ID matching

`vote_for_id` matches an anchored `<id>:` prefix on each voter-file line. Pattern is case-insensitive in the canonical `YES`/`NO`/`EXONERATE` token. Substring collisions are prevented: `FINDING_10:` does not match `FINDING_100:`.

## Security tag

`is_security_block` exits 0 when the block has at least one **unfenced** occurrence of `focus-area\s*=\s*security` (case-insensitive). Both triple-backtick fenced regions and single-backtick code spans are stripped before matching. This is the canonical security counter-invariant — real security findings MUST contain at least one unfenced occurrence.

## Callers (must be kept in sync)

- `skills/design/scripts/tally-plan-review.sh` — sources this library; uses all six functions.
- `skills/review/scripts/tally-code-votes.sh` — sources this library; uses all six functions.

## Harness

`scripts/test-lib-vote-tally.sh` (sibling) sources the library and asserts each function in isolation. Run via `make test` (sharded under `test-harnesses`).

## Edit-in-sync

When changing the threshold rules in `accept_finding`, the security regex in `is_security_block`, or the heading regex in `split_ballot_to_blocks`, update both callers, the harness, and `skills/shared/voting-protocol.md` (Threshold Rules table) in the same PR.
