### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/voting.py:297-317
- **Concern**: Plan adds BALLOT_HEADING_RE but does not require refactoring split_ballot to consume it. Scenario: proposer_map_from_ballot and validate_proposer_map_coverage can drift from split_ballot if the heading regex is duplicated; coverage validation may pass while tally split fails, or item IDs diverge
- **Proposed resolution**: Refactor split_ballot (and map extraction) to share one BALLOT_HEADING_RE / block-walk helper used by split_ballot, proposer_map_from_ballot, and validate_proposer_map_coverage



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:423-459
- **Concern**: Plan-review OOS append cites findings-oos.md but the Python round driver never writes that file. Scenario: execute_round only persists findings-oos.pre-dedup.md; an implementer that reads findings-oos.md per the plan gets a missing or stale file and composes a ballot without OOS blocks, leaving OOS rows attributed for voters and breaking the issue acceptance criterion
- **Proposed resolution**: In _compose_attributed_ballot use the in-memory oos_md returned from _compose_findings_from_collector (optionally also write findings-oos.md once before compose); do not treat an on-disk findings-oos.md fallback as authoritative unless this step just wrote it



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_tally.py:79-95
- **Concern**: python/review_tally.py plan section omits adding --proposer-map-file to _parse_tally_args and threading it through tally_code_votes. Scenario: The plan describes sidecar defaulting and sidecar_required behavior but never names the CLI flag wiring implementers must add, so review tally-code-votes can ship without accepting --proposer-map-file and Step 5 MAV re-tallies fall back to anonymous proposer labels
- **Proposed resolution**: Add an explicit bullet under ### UPDATED: python/review_tally.py to extend _parse_tally_args with optional --proposer-map-file and pass it into proposer_for_item for classification scoreboard and artifact-restore paths



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_tally.py:489-516
- **Concern**: Scoreboard rows still use a single reviewer string while code-review tally splits comma-separated proposer labels. Scenario: Merged plan-review blocks store comma-separated Reviewer(s) values in the sidecar; plan_review_tally._render feeds that string to _scoreboard as one key so merged proposals under-credit individual vendors compared with pre-change per-slot scoring when sidecar restore preserves combined labels
- **Proposed resolution**: Split sidecar reviewer labels with the same comma-split helper review_tally uses before appending score_rows, or document and test that merged labels must remain a single scoreboard bucket



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:91-98
- **Concern**: The `execute_round` section gates ballot rebuild on "after aggregation succeeds," which conflicts with the Approach section's "rebuild every round" rule and with current control flow where voter dispatch still runs when aggregation fails or is skipped (`AGGREGATOR_STATUS=aggregator-failed`; see python/plan_review_round.py:452-475).. Scenario: An implementer who only rebuilds on aggregator success can leave round 2+ on stale neutralized `ballot.txt` (today's `ballot.is_file()` reuse bug), so voters judge the wrong findings and the sidecar can disagree with the ballot.
- **Proposed resolution**: Rebuild the attributed ballot from post-aggregate `findings-in-scope.md` plus current OOS content after every aggregation attempt, immediately before sidecar write and neutralization, regardless of `AGGREGATOR_STATUS`; keep only the "do not neutralize aggregator inputs" ordering constraint.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_tally.py:83-94
- **Concern**: The `python/review_tally.py` plan section documents sidecar defaulting behavior but never requires adding a `--proposer-map-file` CLI flag, unlike the explicit `Add optional --proposer-map-file` bullet for `python/plan_review_tally.py`.. Scenario: `python/review_pipeline.py` is planned to pass `--proposer-map-file` on normal, validation-exhausted, and MAV re-tally paths. Without a matching argparse surface in `review_tally.py`, those calls fail or the flag is ignored, leaving `voting.reviewer_for_block()` on neutralized ballots and scoring every proposer as `anonymous`.
- **Proposed resolution**: Mirror the `plan_review_tally.py` contract in the `python/review_tally.py` section: add optional `--proposer-map-file`, default to the current round's `proposer-map.tsv` only when intended, and pass `sidecar_required=True` into `proposer_for_item()` whenever the sidecar is explicit or defaulted.



### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_review_tally.py; python/review_tally.py; skills/design/scripts/design-step3-mav.sh:279-284
- **Concern**: [SCOPE-REDUCTION] The plan adds implicit proposer-map defaulting when the flag is omitted instead of updating every production re-tally caller to pass the sidecar explicitly. Scenario: A legacy or direct tally call in a tmpdir that already contains proposer-map.tsv can silently score a different ballot with stale proposer labels. The current design-step3-mav.sh re-tally call omits the sidecar flag, so the plan depends on that risky implicit default for the /design MAV path
- **Proposed resolution**: Remove implicit sidecar defaulting. Keep omitted --proposer-map-file as legacy ballot parsing only. Add skills/design/scripts/design-step3-mav.sh and its tests to the plan, and pass --proposer-map-file "$DESIGN_TMPDIR/proposer-map.tsv" when present; keep review core and Step 5 MAV explicit too.



