### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:454-459
- **Concern**: [SCOPE-REDUCTION] Ballot assembly omits OOS blocks before neutralization. Scenario: Active `plan-review run --mode loop` builds `ballot.txt` from `in_scope` only and never appends `oos_md`; OOS items are written to `findings-oos.pre-dedup.md` but excluded from the voter ballot. Acceptance requires OOS rows to be neutralized on voter-facing ballots, so `/design` cannot satisfy the OOS portion of the feature on the production loop path.
- **Proposed resolution**: Before `write_proposer_map` / `neutralize_reviewer_attribution`, set ballot text to in-scope content plus `oos_md` (for example concatenate post-aggregation `findings-in-scope.md` with `oos_md` when creating a new ballot).




### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:427-459
- **Concern**: [SCOPE-REDUCTION] New ballots use pre-aggregation text, not aggregated findings. Scenario: When `ballot.txt` is absent, `execute_round` seeds the ballot from the pre-aggregation `in_scope` variable even though `aggregate-findings` rewrites `findings-in-scope.md` on disk. Voters and the new proposer sidecar therefore see pre-merge findings and proposer labels, while tally artifacts expect the aggregated set. Neutralization wraps the wrong ballot payload.
- **Proposed resolution**: After aggregation succeeds, rebuild ballot text from the updated `findings-in-scope.md` (plus `oos_md`) immediately before writing `proposer-map.tsv` and neutralizing `ballot.txt`; do not reuse the pre-agg `in_scope` variable.




### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_tally.py:234-240
- **Concern**: python/plan_review_tally.py:489-491. Scenario: Zero-judge and MAV re-tally paths still call `reviewer_for_block` on neutralized blocks
- **Proposed resolution**: `main-agent-vote-required` is reached with a neutralized `ballot.txt` while `_write_findings_classification` and `_render` still read proposer labels from split blocks. Without sidecar lookup, `findings-classification.tsv` and the Reviewer Competition Scoreboard record `anonymous` instead of real proposers, breaking acceptance that scoring stays unchanged. The plan already targets `proposer_for_item`; ensure it replaces every `reviewer_for_block` call in `_write_findings_classification`, `_render` score rows, and the `eligible == 0` branch, and add a regression test where neutralized ballot plus sidecar yields pre-change scoreboard labels.




### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:1976-1990
- **Concern**: Validation-exhausted tally may consume a stale proposer map. Scenario: /review reuses one REVIEW_TMPDIR across rounds; after a prior normal round creates proposer-map.tsv, a later aggregate validation-exhausted branch runs before the plan's neutralization/map rewrite point and can default review_tally.py to the old sidecar, so findings-classification.tsv and scoreboards can attribute current FINDING_1 rows to prior-round proposers
- **Proposed resolution**: Build and pass a current proposer-map.tsv before the validation-exhausted tally, or make that branch opt out of sidecar defaulting; do not rely on mere sidecar presence




### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:454-459
- **Concern**: [SCOPE-REDUCTION] Plan adds proposer-map + neutralization on ballot.txt but leaves the existing ballot source logic unchanged. Scenario: execute_round prefers an existing ballot.txt or the pre-aggregate in_scope string, not post-aggregate findings-in-scope.md. Round 2+ reuses an already-neutralized ballot, so proposer-map.tsv records anonymous proposers and the Reviewer Competition Scoreboard collapses. Round 1 can also diverge when aggregation merges or renumbers findings after in_scope was captured.
- **Proposed resolution**: Before writing proposer-map.tsv, always rebuild the attributed ballot from findings-in-scope.md after aggregation (current round). Write the sidecar from that attributed text, then neutralize and overwrite ballot.txt. Do not branch on ballot.is_file() for source selection.




### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: python/plan_review_round.py:454-466; python/review_pipeline.py:2015-2017; python/plan_review_panel.py:520-527
- **Concern**: The proposer sidecar is planned in the same tmpdir before voter dispatch. Scenario: The plan writes predictable proposer-map.tsv beside the ballot before voters run; the Claude plan voter is launched with read access to the design tmpdir, so a ballot-body prompt injection or curious voter can read the sidecar and recover proposer/vendor labels, defeating the structural anonymity requirement
- **Proposed resolution**: Keep the proposer map unavailable to voters: hold the map in memory or a private non-voter path, neutralize the ballot, dispatch voters, then write/pass the sidecar immediately before tally; for MAV, expose the sidecar only after the synthetic vote file exists




### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:454-459
- **Concern**: Plan adds proposer-map write and ballot neutralization but leaves ballot assembly unchanged: it still uses pre-aggregate `in_scope` or a stale existing `ballot.txt`, and never appends OOS blocks from `oos_md`. Scenario: When aggregation rewrites `findings-in-scope.md`, voters and `proposer-map.tsv` can be built from the wrong text; plan-review `OOS_N` items never enter `ballot.txt`, so they are never neutralized or sidecar-mapped despite issue scope requiring identical OOS treatment
- **Proposed resolution**: In `execute_round`, after aggregate, compose final ballot as post-aggregate `findings-in-scope.md` plus OOS content (`oos_md` or `findings-oos.md`), write `ballot.txt`, then build `proposer-map.tsv` from that unstripped text and neutralize `ballot.txt` before `voter-dispatch`




### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/voting.py
- **Concern**: `proposer_map_from_ballot` / `proposer_for_item` do not specify that stored `reviewer` values must be byte-identical to `reviewer_for_block` normalization (strip label prefix, remove `*`, trim). Scenario: Sidecar labels can drift from legacy `reviewer_for_block` output; `findings-classification.tsv`, scoreboards, and restored artifacts may not match pre-change expectations for equivalent ballots
- **Proposed resolution**: Add an explicit contract (and unit test) that sidecar `reviewer` values are produced with the same normalization as `reviewer_for_block`, and that `restore_reviewer_attribution` reinserts the preserved original `reviewer_line` verbatim




### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/voting.py
- **Concern**: `proposer_map_from_ballot` heading detection is unspecified relative to `voting.split_ballot` (`^### (FINDING_[0-9]+|OOS_[0-9]+):`). Scenario: If map parsing accepts a different heading set than `split_ballot`, tally can split blocks with no sidecar entry; `proposer_for_item` then falls back to `reviewer_for_block` on a neutralized block and records proposer `anonymous`, corrupting competition scoring
- **Proposed resolution**: Pin map extraction to the same heading regex and block boundaries as `split_ballot`; fail closed before voter dispatch if any split item ID is missing from the map




### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/voting.py planned helper; plan.txt:46-51,239-244
- **Concern**: Neutralized ballots can silently score as anonymous when the sidecar is malformed or missing an item. Scenario: read_proposer_map ignores malformed rows and proposer_for_item falls back to reviewer_for_block; on new neutralized ballots that fallback returns anonymous, so findings-classification.tsv, scoreboards, and restored artifacts lose original proposer attribution instead of failing
- **Proposed resolution**: For a present or explicitly passed sidecar, treat missing or malformed entries as a tally error when the block reviewer is anonymous; keep per-item fallback only for legacy attributed ballots with a non-anonymous reviewer line




### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:454-459
- **Concern**: Plan does not require rebuilding ballot text from the current round before proposer-map extraction and neutralization. Scenario: The existing `if ballot.is_file()` branch reuses prior `ballot.txt`. After round 1 that file is neutralized (`anonymous`). Round 2+ would build `proposer-map.tsv` from stale or already-anonymous labels, so classification and scoreboards lose real proposers while voters still see round-1 findings
- **Proposed resolution**: In `execute_round`, always derive unattributed ballot text from the current round's post-aggregate `findings-in-scope.md` (not from existing `ballot.txt` and not the pre-aggregate `in_scope` variable). Write `proposer-map.tsv` from that text, then overwrite `ballot.txt` with `neutralize_reviewer_attribution(...)`. Add a multi-round plan-review test




