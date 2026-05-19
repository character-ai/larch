## Goal
Rename NEUTRAL to JUDGE_ERROR in vote_for_id() parser fallback and propagate through all callers and docs

## Implementation Plan

Rename the parser-fallback value `NEUTRAL` in `vote_for_id()` to `JUDGE_ERROR` across all affected files.
Do NOT rename the finding-level `neutral` classification from `classify_result()` — those are correct tied-vote semantics.

### Files to change

**`scripts/lib-vote-tally.sh`** — core fix:
- Function comment (line 8): `NEUTRAL` → `JUDGE_ERROR`
- Function comment (line 11): `NEUTRAL` → `JUDGE_ERROR`
- Awk BEGIN block (line 15): `BEGIN { result="NEUTRAL" }` → `BEGIN { result="JUDGE_ERROR" }`

**`scripts/test-lib-vote-tally.sh`** — test update:
- Line 54: description `2 NEUTRAL` → `2 JUDGE_ERROR`
- Line 56: description `1 NEUTRAL` → `1 JUDGE_ERROR`
- Line 70: description and expected value `"NEUTRAL"` → `"JUDGE_ERROR"`
- Line 75: description and expected value `"NEUTRAL"` → `"JUDGE_ERROR"`
- Add new test case after line 75: voter file with zero FINDING_N: lines asserts JUDGE_ERROR, never NEUTRAL

**`scripts/lib-vote-tally.md`** — API doc:
- API table: output `NEUTRAL` → `JUDGE_ERROR`
- Threshold section: remove NEUTRAL from the list of non-accepting votes; update "NEUTRAL abstentions" sentence

**`scripts/test-lib-vote-tally.md`** — test doc:
- Coverage line: `missing finding → NEUTRAL` → `missing finding → JUDGE_ERROR`

**`scripts/dispatch-code-voters.sh`** — parse-rate inline awk copy:
- Rename local variable `neutral_count` → `judge_error_count` throughout function
- Awk BEGIN: `BEGIN { result="NEUTRAL" }` → `BEGIN { result="JUDGE_ERROR" }`
- Grep: `grep -c '^NEUTRAL'` → `grep -c '^JUDGE_ERROR'`
- Comment: `>=80% NEUTRAL threshold` → `>=80% JUDGE_ERROR threshold`
- Diag field: `neutral_count=` → `judge_error_count=`
- Error message: `findings returned NEUTRAL` → `findings returned JUDGE_ERROR`

**`scripts/dispatch-code-voters.md`** — doc:
- Update NEUTRAL references in check_voter_parse_rate description

**`skills/review/scripts/tally-code-votes.sh`** — tally output format:
- Lines 234, 273: degraded-panel warning `NEUTRAL` → `JUDGE_ERROR`
- Line 276: `| NEUT |` → `| JERR |` column header
- Per-finding loop: rename local variable `neutral` → `judge_error`
- Printf format strings: `NEUTRAL=%s` → `JUDGE_ERROR=%s`

**`skills/design/scripts/tally-plan-review.sh`** — tally output format:
- Line 200: `Neutral` → `JErr` in column header
- Per-finding loop: rename local variable `neutral` → `judge_error`
- Printf format string: `NEUTRAL=%s` → `JUDGE_ERROR=%s`

**`skills/shared/voting-protocol.md`** — voting doc:
- Update "NEUTRAL abstentions" → `JUDGE_ERROR`

**`docs/voting-process.md`** — process doc:
- Update "NEUTRAL abstentions" → `JUDGE_ERROR`

**`docs/run-logs.md`** — run-logs doc:
- Add clarifying note: JUDGE_ERROR is a per-judge-per-finding state (parser fallback), distinct from neutral_count (finding-level tied votes)

**`skills/implement/scripts/test-write-rejected-findings.sh`** — test fixture:
- Update `NEUTRAL=0` → `JUDGE_ERROR=0` in Vote tally format string


## Test plan
Run `scripts/test-lib-vote-tally.sh` to verify JUDGE_ERROR for all vote_for_id missing-ballot cases.
Run `/relevant-checks` to verify no lint regressions.
