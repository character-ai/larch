# Review Round 3

- Mode: `diff`
- 2 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Plan-review tally lacks fail-closed neutralized-ballot sidecar guard; MAV re-tally omits explicit sidecar binding
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-artifact-attribution-output.txt
- **Severity**: important
- **Concern**: `plan_review_tally.py` does not mirror `review_tally.py`'s fail-closed behavior for neutralized ballots. `review_tally.py` sets `proposer_sidecar_required=True` when `_ballot_is_neutralized()` sees `anonymous` reviewer lines, so a neutralized ballot without a usable sidecar aborts instead of scoring `anonymous`. `plan_review_tally.py` only sets `proposer_sidecar_required` when `--proposer-map-file` is passed or `$DESIGN_TMPDIR/proposer-map.tsv` exists; if that file is missing, deleted, or pointed at the wrong tmpdir, `voting.proposer_for_item(..., sidecar_required=False)` returns `anonymous` from the ballot block. That poisons `findings-classification.tsv`, reviewer scoreboards, and post-vote artifacts (`accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`) because `_artifact_text_for_item()` calls `restore_reviewer_attribution()` with an empty `reviewer_line` and leaves neutral text unchanged. MAV re-tally on a neutralized `ballot.txt` without valid `proposer-map.tsv` records proposer `anonymous` instead of erroring. The `/design` MAV re-tally path (`skills/design/scripts/design-step3-mav.sh:279-284`) omits explicit `--proposer-map-file` and depends on default sidecar binding, so missing or stale `proposer-map.tsv` during MainAgent re-tally can silently mis-attribute findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port `_ballot_is_neutralized/_resolve_proposer_map` (or shared helper) into `plan_review_tally` and add a fail-closed test.
  - From cursor-specialist-edge-cases-output.txt: Pass `--proposer-map-file` explicitly in `design-step3-mav.sh` post phase and fail when neutralized ballot lacks a valid sidecar.
  - From dyn-artifact-attribution-output.txt: **Suggested fix:** Port `_ballot_is_neutralized()` (or share it from `voting.py`) into `plan_review_tally.py`, set `proposer_sidecar_required=True` when the ballot is neutralized even if the sidecar file is absent, and add a `test_plan_review.py` case equivalent to `test_neutralized_tally_without_sidecar_fails_closed`. Optionally pass `--proposer-map-file "$DESIGN_TMPDIR/proposer-map.tsv"` explicitly from `design-step3-mav.sh`.


### FINDING_3: Stale or ambient `proposer-map.tsv` overrides live attributed ballot reviewer lines during tally
- **Reviewer(s)**: codex-generic-output.txt, dyn-ballot-neutrality-output.txt
- **Severity**: important
- **Concern**: `proposer_for_item()` always returns the sidecar row when `proposer-map.tsv` exists, even if the split block still carries a non-`anonymous` reviewer line. That diverges from the plan contract ("fall back to `reviewer_for_block()` … when the block still carries a non-anonymous reviewer line"). `plan_review_tally.py:382-386` and `review_tally.py:446-450` auto-bind a default sidecar whenever that file is present, so `tally-code-votes` auto-binds `$REVIEW_TMPDIR/proposer-map.tsv` whenever the file exists, even for an attributed ballot. Concrete failure: tally a new or legacy attributed `FINDING_1` in a reused tmpdir that still has a prior round's `proposer-map.tsv`, and classification plus scoreboards credit the stale sidecar proposer instead of the block's visible `- **Reviewer**:` value. Production neutralized ballots are fine when map and ballot are rebuilt together; attributed-ballot + leftover sidecar can mis-score competition rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: **Suggested fix:** Default to the sidecar only when the ballot is neutralized, or pass an explicit current-round sidecar from production callers and keep attributed ballots on the legacy `reviewer_for_block` path.
  - From dyn-ballot-neutrality-output.txt: **Suggested fix:** In `proposer_for_item()`, use the sidecar only when the block reviewer is neutralized (`anonymous`) or `sidecar_required` is set with no non-neutral block line; otherwise return `reviewer_for_block()`. Optionally skip auto-binding the default sidecar unless the ballot is neutralized or `--proposer-map-file` was explicit.


