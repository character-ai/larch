# lib-vote-tally.sh

**Type**: sourced-only shared library (no shebang).

**Purpose**: Owns the cross-skill voting primitives shared between `/design` plan-review (`skills/design/scripts/tally-plan-review.sh`) and `/review` code-review (`skills/review/scripts/tally-code-votes.sh`) tally scripts. Single source of truth so the threshold rules and security-tag detection do not drift between callers.

## API

| Function | Inputs | Output | Exit |
|---|---|---|---|
| `vote_for_id <id> <voter_file>` | finding/oos id (e.g. `FINDING_3`), voter output file | stdout: `YES` \| `NO` \| `JUDGE_ERROR` (stray `EXONERATE` tokens tolerated and mapped to `NO`) | 0 |
| `reviewer_for_block <block_file>` | per-block markdown file | stdout: reviewer attribution string (or `unknown`) | 0 |
| `is_security_block <block_file>` | per-block markdown file | — | 0 (security tag found, unfenced) \| 1 (not found) |
| `accept_finding <yes> <no> <exonerate> <eligible>` | vote counts and eligible voter count | — | 0 (accept) \| 1 (reject) |
| `split_ballot_to_blocks <ballot_file> <out_dir>` | ballot file, output dir | per-ID `<id>.md` files in `out_dir` | 0 \| 1 (duplicate `### FINDING_N` / `### OOS_N` headings) |
| `classify_result <yes> <no> <exonerate> <eligible>` | vote counts and eligible voter count | stdout: `accepted` \| `neutral` \| `rejected` | 0 |
| `panel_tier <eligible>` | eligible voter count | stdout: `full-3` \| `unanimous-2` \| `single-judge` \| `main-agent-required` | 0 |

## Threshold

`accept_finding` thresholds:

- `eligible >= 3` → `yes >= 2` accepts.
- `eligible == 2` → `yes == 2` (unanimous) accepts.
- `eligible == 1` → `yes == 1` accepts; `NO` or `JUDGE_ERROR` do not accept.
- `eligible == 0` → never accepts; caller escalates to main-agent adjudication.

The `eligible` argument is the panel-level count of available voter files (non-failed voter outputs), not the per-finding count of YES/NO responses. Missing votes from available judges produce `JUDGE_ERROR` (parser fallback — ballot entry absent or unparseable) and do not reduce the panel tier.

`classify_result` uses the same tiers. It returns `accepted` when the YES threshold is met, `neutral` when YES > 0 but the threshold is not met (0 points to the proposing reviewer), and `rejected` when YES == 0 (-1 point). The `exonerate` parameter is accepted for backward compatibility but is ignored — `vote_for_id` maps stray `EXONERATE` tokens to `NO`.

## ID matching

`vote_for_id` matches an anchored `<id>:` prefix and the first vote token immediately after the colon. Pattern is case-insensitive. Substring collisions are prevented (`FINDING_10:` does not match `FINDING_100:`), and prose such as `FINDING_1: NO -- yes, minor concern` cannot override the leading `NO`. Stray `EXONERATE` tokens from old voter output are tolerated and mapped to `NO`.

## Reviewer attribution

`reviewer_for_block` extracts only anchored reviewer attribution lines: `- **Reviewer(s)**: ...`, `- **Reviewer**: ...`, `- **Reviewers**: ...`, or unbolded line-start `Reviewer(s):` / `Reviewer:` / `Reviewers:` fallbacks. Prose containing `Reviewer` elsewhere in the block is ignored and returns `unknown` when no attribution line exists.

## Security tag

`is_security_block` exits 0 when the block has a security routing token outside triple-backtick fences. Prose/code examples inside single-backtick spans do not count for the canonical `focus-area\s*=\s*security` token. Dedicated line-start `focus-area: security` / `focus-area = security` fields do count even when the label or value is backtick-wrapped. Explicit heading tags count only when the block-opening heading starts its title with `[security]` / `<security>` (optionally after `[OUT_OF_SCOPE]` / `[OOS]`); later body headings that merely cite `[security]` do not route the block. Ordinary heading prose containing the bare word `security` does not count.

## Callers (must be kept in sync)

- `skills/design/scripts/tally-plan-review.sh` — sources this library.
- `skills/review/scripts/tally-code-votes.sh` — sources this library.

## Harness

`scripts/test-lib-vote-tally.sh` (sibling) sources the library and asserts each function in isolation. Run via `make test` (sharded under `test-harnesses`).

## Edit-in-sync

When changing the threshold rules in `accept_finding`, the security regex in `is_security_block`, or the heading regex in `split_ballot_to_blocks`, update both callers, the harness, and `skills/shared/voting-protocol.md` (Threshold Rules table) in the same PR. When changing `vote_for_id` or `classify_result` semantics, update `scripts/parse-judge-vote-and-rating.sh` in the same PR (it has its own vote parser used for forensic rating).

## Scope-reduction marker helper

`is_scope_reduction_block <block>` shells out to `scripts/check-scope-reduction-marker.sh`. The detector only accepts a leading `[SCOPE-REDUCTION]` marker in a finding heading, `what:`, or Concern/problem field after removing fenced code, inline code spans, and one leading severity bracket such as `[important]`, `[nit]`, or `[latent]`. Non-leading prose mentions and code-only mentions are false. The helper does not change tally thresholds; tagged findings are classified by the normal `accept_finding` / `classify_result` rules.
