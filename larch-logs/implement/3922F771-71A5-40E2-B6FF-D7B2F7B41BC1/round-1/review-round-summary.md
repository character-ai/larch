# Review Round 1

- Mode: `diff`
- 4 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: `accepted_finding_points_from_severities` uses unanimous all-vote rule, not strict majority of YES voters
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-dyn-score-consensus-output.txt, dyn-dyn-rubric-sync-output.txt
- **Severity**: important
- **Concern**: `python/voting.py` (`accepted_finding_points_from_severities`, roughly lines 498–517) awards `+2` only when `total_votes >= MIN_PANEL_VOTES_FOR_BONUS` (2) and `high_yes == total_votes`, where `total_votes` counts every non-empty panel cell (YES, NO, `JUDGE_ERROR`) but `high_yes` counts only YES votes rated `blocker`/`major`. That is unanimous all-recorded-voters-must-be-YES-and-high, not the plan’s strict majority over YES voters (`high_yes > total_yes / 2` with a YES-only denominator). Concrete mismatches vs plan/issue: lone YES/`major` → `+1` (plan `+2`); three YES with two high and one `minor` → `+1` (plan `+2`); two YES/`major` plus one NO → `+1` (plan `+2`); YES/`major`, YES/`major`, `JUDGE_ERROR` → `+1` despite unanimous high among YES voters. `MIN_PANEL_VOTES_FOR_BONUS` also blocks the single-voter `+2` edge case the plan requires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove or narrow the min-vote gate so strict majority applies to any non-empty YES set.
  - From codex-specialist-correctness-output.txt: Count YES votes as the denominator, count high severities only on YES votes, and return 2 when high_yes_count > total_yes_count / 2; use the same rule over severities when votes is omitted
  - From cursor-specialist-edge-cases-output.txt: Count YES voters only; return 2 when high_yes > total_yes / 2; drop or relax MIN_PANEL_VOTES_FOR_BONUS for single-YES high; align docs/tests
  - From cursor-specialist-edge-cases-output.txt: Restrict denominator to YES votes only or document and test explicit +1 cap when any non-YES vote is recorded
  - From codex-specialist-edge-cases-output.txt: Count only YES votes in the denominator, count high severity only for YES votes, return +2 when high_yes_count > total_yes_count / 2, and update docs/prompts/tests to match.
  - From codex-specialist-testing-output.txt: Count YES votes only, return +2 when high_yes_count > total_yes_count / 2, and update tests plus scoring prose to match.
  - From dyn-dyn-score-consensus-output.txt: Count `total_yes` from YES votes only; return `2` when `high_yes > total_yes / 2` (and keep the documented single-voter case `1 > 0.5`). Align `skills/shared/voting-protocol.md`, `skills/design/references/plan-review.md`, `python/rendering.py`, and `python/test_voting.py` with that formula, or explicitly re-scope the issue if unanimous semantics are intended.
  - From dyn-dyn-score-consensus-output.txt: Split counters: `total_yes` / `high_yes` over YES cells only; ignore NO/`JUDGE_ERROR` for the points gate (or treat `JUDGE_ERROR` as non-voting for scoring). Add a tally fixture for `YES`/`major`, `YES`/`major`, `JUDGE_ERROR` and for `YES`/`major`, `YES`/`major`, `NO`/`minor` on an accepted finding.
  - From dyn-dyn-rubric-sync-output.txt: Either implement plan semantics in `accepted_finding_points_from_severities` (count YES voters only; return `2` when `high_yes > total_yes / 2`; keep single-YES-high as `+2`) and update prompts/tests accordingly, or explicitly revise the plan/issue acceptance criteria if unanimous-all-high is intentional.
  - From dyn-dyn-rubric-sync-output.txt: If plan semantics are kept, count `total_yes` from YES votes only and apply `high_yes > total_yes / 2`. If unanimous semantics are kept, document that dissenting NO votes permanently cap an accepted finding at `+1` regardless of YES severities.


### FINDING_2: correctness: `python/test_voting.py` pins unanimous semantics instead of plan majority cases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-score-consensus-output.txt
- **Severity**: important
- **Concern**: Unit tests (notably `test_weighted_finding_points_and_attribution_helpers` around lines 1002–1013) assert unanimous/min-two-voter `+2` behavior that contradicts the plan’s strict-majority contract. Examples pinned wrong: three YES with `major`/`blocker`/`minor` expects `+1` (plan `+2`); missing or inverted cases for lone YES/`major` → `2`, two YES/`major` plus one NO → `2`, and explicit guard that `high_yes == total_votes` is not the intended gate. A correct strict-majority fix would fail these assertions and could ship silently wrong relative to the issue plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add assert for two-of-three YES high == 2 and single YES major == 2; keep one-of-three == 1
  - From cursor-specialist-testing-output.txt: Align implementation and tests to one contract: either restore strict-majority assertions from the plan or rewrite tests to document unanimous MIN_PANEL_VOTES_FOR_BONUS behavior explicitly.
  - From dyn-dyn-score-consensus-output.txt: Replace or extend `test_weighted_finding_points_and_attribution_helpers` with the plan’s matrix, and add one code-review tally case where majority-high YES voters with a dissenting NO still score `+2` once the helper is corrected.


### FINDING_3: risk-integration: `python/test_review_tally.py` lacks majority-high `+2` tally fixture
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-score-consensus-output.txt
- **Severity**: important
- **Concern**: Tally integration tests only prove unanimous-high `+2` (e.g. FINDING_3 fixture); the plan-required 2-of-3 YES-high accepted finding case is untested and currently scores `+1` not `+2` at tally level. No regression guard for mixed high/low YES severities on an accepted finding with expected scoreboard weight `+2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add accepted finding with major/major/minor across three YES voters and assert proposer score +2 under intended contract
  - From cursor-specialist-testing-output.txt: Add a ballot/vote fixture for mixed high/low YES severities with an explicit expected scoreboard weight matching the chosen scoring contract.


### FINDING_4: risk-integration: competition prompt and `voting-protocol.md` describe unanimous rule, not strict-majority YES scoring
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/rendering.py` (competition notice), `skills/shared/voting-protocol.md` (lines 191–196), and `skills/design/references/plan-review.md` (lines 30, 177) describe unanimous YES and every recorded panel severity instead of strict-majority YES-voter scoring. Example: two high YES severities plus one NO `minor` should score `+2` under plan semantics, but prompt/docs say it does not because the panel was not unanimous and not every recorded severity was high. Future phases and operators may follow a unanimous contract divergent from issue #5124.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Change all scoring prose to require a strict majority of YES voters rating blocker or major, and state that only YES-attached vN_severity cells affect points
  - From cursor-specialist-edge-cases-output.txt: Rewrite competition scoring row to strict-majority YES language if majority is authoritative; keep in sync with voting.py


