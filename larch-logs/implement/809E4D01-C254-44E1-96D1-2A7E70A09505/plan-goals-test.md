## Goal
Implement issue #6579: [IMPLEMENTING] [BUG] Voter OOS_N relabeling of FINDING_N items causes per-item JUDGE_ERRORs.

## Implementation Plan
## Plan

## Approach

Implement parser-side alias acceptance only where the full ballot id set proves the alias is safe.

Add a small helper in `voting.py`:

- `alias_ballot_id(ballot_id, ballot_id_set)`.
- Return `OOS_k` for `FINDING_k`, or `FINDING_k` for `OOS_k`.
- Return `""` when the id does not match the grammar.
- Return `""` when the alias is already present in the same ballot.

Thread that alias into vote parsing:

- Add optional keyword-only `alias_id: str = ""` to `vote_for_id`.
- Add optional keyword-only `alias_id: str = ""` to `parse_judge_vote`.
- Preserve current behavior for callers that do not pass `alias_id`.
- Parse the primary id first.
- Fall back to `alias_id` only when the primary id yields no valid vote.
- Keep `EXONERATE` mapping to `NO`.
- Keep markdown-table normalization before both primary and alias parsing.

Thread ballot-id awareness through tally paths:

- In code-review tally, build `ballot_id_set` from split ballot block stems.
- Pass `alias_ballot_id(item_id, ballot_id_set)` to each `parse_judge_vote`.
- In parse-rate checking, build the same set from `_ballot_ids` and pass aliases during per-item parsing. This prevents a relabeled voter from being removed before the tally.
- In plan-review tally, store a `ballot_id_set` on `_Tally` after `_sorted_ids()`.
- Use one small `_alias_id(item_id)` method so every plan-review call to `vote_for_id` and `parse_judge_vote` uses the same safe alias.

Do not change:

- Ballot heading generation.
- Voter prompt prose.
- Retry logic.
- CLI argv or stdout schema.

## Files to modify/create

### UPDATED: python/larch/review/voting.py

Add `alias_ballot_id`.

Refactor vote-line parsing enough to support primary-first, alias-second behavior without changing existing outputs. A private helper is fine if it keeps `vote_for_id` and `parse_judge_vote` small.

Update `check_voter_parse_rate` so it computes the ballot id set once and passes a safe alias for each id.

Keep `vote_for_id_main` and `parse_judge_vote_main` CLI contracts unchanged.

### UPDATED: python/larch/review/review_tally.py

After `_block_files(...)`, derive:

- `ballot_id_set = {block.stem for block in blocks}`.

For each item, compute `alias_id = voting.alias_ballot_id(item_id, ballot_id_set)` and pass it to all `parse_judge_vote` calls in the item loop.

Keep `is_oos` classification based on id prefix or `[OUT_OF_SCOPE]` title text. The alias must affect vote parsing only.

### UPDATED: python/larch/review/plan_review_tally.py

Add `self.ballot_id_set: set[str] = set()` to `_Tally`.

After `sorted_ids = self._sorted_ids()`, set `self.ballot_id_set = set(sorted_ids)`.

Add a tiny method, for example `_alias_id(self, item_id: str) -> str`, that calls `voting.alias_ballot_id`.

Pass the alias to all plan-review uses of:

- `voting.vote_for_id`.
- `voting.parse_judge_vote`.

Cover these methods:

- `_tally_votes_for_id`.
- `_votes_and_severities_for_item`.
- `_vote_and_severity_for_slot`.
- `_write_findings_classification`.

### UPDATED: python/tests/review/test_voting.py

Add unit tests for:

- `alias_ballot_id("FINDING_6", {"FINDING_6"}) == "OOS_6"`.
- `alias_ballot_id("FINDING_1", {"FINDING_1", "OOS_1"}) == ""`.
- Reverse aliasing from `OOS_k` to `FINDING_k`.
- `vote_for_id` accepts `OOS_6:` for `FINDING_6` when `alias_id="OOS_6"`.
- `parse_judge_vote` accepts the aliased line and preserves axes.
- A primary `FINDING_k:` line wins over an alias line when both are present.
- Existing anchored parsing still works without `alias_id`.

### UPDATED: python/tests/review/test_review_tally.py

Add an integration regression for code-review tally:

- Ballot contains `### FINDING_1: [OUT_OF_SCOPE] ...`.
- No `### OOS_1:` heading exists.
- Voters emit `OOS_1: YES ...` lines.
- Assert the tally counts votes as YES, not JUDGE_ERROR.
- Assert `PARSE_FAILED_COUNT=0`, so parse-rate aliasing happened before slot removal.
- Assert the classification TSV row for `FINDING_1` stores the recovered vote and `scope=oos`.

Add a collision guard case, either in the same test or a separate small test:

- Ballot contains both `### FINDING_1:` and `### OOS_1:`.
- A voter line for `OOS_1:` must not count as a vote for `FINDING_1`.

## Edge cases

- A ballot may contain both `FINDING_1` and `OOS_1`; do not alias either id in that case.
- A malformed primary line plus a valid alias line may still recover through alias if the primary yields no valid vote.
- A valid primary line must win over alias text.
- Markdown table vote normalization must still work for primary ids.
- Alias parsing must not change result classification. `FINDING_N` rows still use normal finding quorum rules unless current OOS title logic classifies the item as OOS.
- Missing or unreadable voter files should keep current error and fallback behavior.

## Failure modes

- If parse-rate is not updated, relabeled voters can still be dropped before tallying.
- If plan-review uses aliases for `parse_judge_vote` but not `vote_for_id`, tally counts and severity-derived fileability can diverge.
- If aliasing ignores collisions, mixed ballots can mis-assign votes across distinct ballot items.
- If tests cover only `vote_for_id`, classification TSV axis fields can still remain blank.

## Testing strategy

Run focused tests first:

```bash
python3 -m pytest python/tests/review/test_voting.py -q
python3 -m pytest python/tests/review/test_review_tally.py -q
```

Then run the Python relevant checks for changed Python files if available in the working tree flow:

```bash
python3 python/cli.py checks run-relevant
```

If `plan_review_tally.py` changes are not exercised by the focused tests, also run the smallest matching plan-review tally tests:

```bash
python3 -m pytest python/tests/review/test_plan_review.py -q
```

## Difficulty

This is a workflow-affecting parser and tally change across shared voting helpers, code-review tally, and plan-review tally. The collision guard and parse-rate path are integration-sensitive.

## Acceptance

Run focused tests first:

```bash
python3 -m pytest python/tests/review/test_voting.py -q
python3 -m pytest python/tests/review/test_review_tally.py -q
```

Then run the Python relevant checks for changed Python files if available in the working tree flow:

```bash
python3 python/cli.py checks run-relevant
```

If `plan_review_tally.py` changes are not exercised by the focused tests, also run the smallest matching plan-review tally tests:

```bash
python3 -m pytest python/tests/review/test_plan_review.py -q
```

diff_lines: 180

## Test plan
(no test plan section in plan-file)
