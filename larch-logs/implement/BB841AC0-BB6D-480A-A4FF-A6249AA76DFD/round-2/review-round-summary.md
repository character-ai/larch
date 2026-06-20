# Review Round 2

- Mode: `diff`
- 4 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Stale `findings-oos.md` preferred over current-round `oos_md`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ballot-neutrality-output.txt
- **Severity**: important
- **Concern**: `_compose_attributed_ballot` reads on-disk `$DESIGN_TMPDIR/findings-oos.md` when present, including empty or stale leftovers, instead of the current round's in-memory `oos_md`. `execute_round` writes `findings-oos.pre-dedup.md` but never refreshes `findings-oos.md`, so round 2+ attributed ballots and `proposer-map.tsv` can drop, freeze, or mis-cover OOS blocks while in-scope findings refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Always compose OOS from the current oos_md (or write findings-oos.md from oos_md each round before compose) and remove the stale on-disk fallback.
  - From cursor-specialist-edge-cases-output.txt: Always compose OOS from the current round oos_md (or rewrite findings-oos.md from oos_md before compose) and add a regression test with a stale on-disk file
  - From dyn-ballot-neutrality-output.txt: Treat `oos_md` as authoritative for the current round (or write `findings-oos.md` from `oos_md` immediately before compose). Only read `findings-oos.md` when this step just wrote it; do not prefer a pre-existing file.


### FINDING_2: Ballot rebuild ignores aggregation failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Ballot composition and voter dispatch proceed even when aggregation fails or returns a non-ok outcome. `aggregate_findings` can exit 0 while merge failed, so voters may receive pre-aggregate duplicate findings while `AGGREGATOR_STATUS` is recorded as ok, breaking the post-aggregate ballot contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Parse aggregation stdout (AGGREGATED/REASON) and skip or abort voter dispatch unless reason is ok and findings-in-scope.md was merged.


### FINDING_3: `neutralize_reviewer_attribution()` rewrites quoted reviewer lines in finding bodies
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `neutralize_reviewer_attribution()` rewrites every line matching the reviewer-field pattern, not only each block's attribution line. Finding bodies that quote ballot examples (e.g. `  - **Reviewer**: Codex`) are changed to `anonymous`, violating the requirement that body text remain unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Neutralize only the first reviewer attribution line inside each `FINDING_N` / `OOS_N` block, or use the proposer-map extraction to identify the exact attribution line to rewrite.


### FINDING_4: Neutralized ballots without proposer map silently score `anonymous`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-ballot-neutrality-output.txt, dyn-artifact-attribution-output.txt
- **Severity**: important
- **Concern**: When `findings.md` is already neutralized, MAV re-tally and code-review tally can run without a bound proposer map. `review_tally` sets `proposer_sidecar_required` only from an explicit `--proposer-map-file`; Step 5 docs treat the flag as optional when the file merely exists. `proposer_for_item()` then falls through and records `anonymous` in classification, scoreboards, and artifacts instead of raising `TallyError`, violating fail-closed neutralized-ballot behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail tally when neutralized ballots lack an explicit proposer-map-file, or always require the round sidecar on MAV re-tally.
  - From dyn-ballot-neutrality-output.txt: After neutralization in `review_pipeline.py`, either always pass `--proposer-map-file` on the MAV re-tally path, or teach `review_tally` to auto-bind `review_tmpdir/proposer-map.tsv` for the current invocation (as plan review does) and raise `TallyError` when the ballot is neutralized but the map is missing or incomplete.
  - From dyn-artifact-attribution-output.txt: After the sidecar branch, fail closed when `reviewer_for_block()` returns a neutral token and no map entry was resolved (for example `raise TallyError("neutralized ballot requires proposer map")`). Keep the legacy path only when the block still carries a non-anonymous reviewer line.
  - From dyn-artifact-attribution-output.txt: Either mirror the plan-review default (`review_tmpdir/proposer-map.tsv` when present for nested `round-N` tmpdirs) or detect neutralized reviewer lines in the split ballot and hard-fail tally when no sidecar is bound.


