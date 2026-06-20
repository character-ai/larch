# Review Round 4

- Mode: `diff`
- 2 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_2: write_proposer_map accepts anonymous/neutralized reviewer values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ballot-neutrality-output.txt
- **Severity**: important
- **Concern**: `write_proposer_map` / `proposer_map_from_ballot` / `proposer_for_item` treat `anonymous` (and empty) as valid sidecar proposer values. Re-running sidecar write on an already-neutralized ballot, or misordered caller/round reuse, can overwrite the sidecar with anonymous entries while coverage validation still passes. Tally and scoreboards then record `anonymous` instead of failing closed, breaking the contract that missing or unusable attribution must not silently score as `anonymous`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reject neutral reviewer values in write_proposer_map or refuse when ballot_is_neutralized without attributed snapshot
  - From dyn-ballot-neutrality-output.txt: Reject anonymous/empty proposer values in `proposer_map_from_ballot` / `write_proposer_map`, and in `proposer_for_item` treat sidecar rows whose reviewer is `anonymous` as missing (raise `TallyError`) when the block is neutralized.


### FINDING_8: stale proposer-map.tsv auto-bound without ballot consistency checks
- **Reviewer(s)**: dyn-ballot-neutrality-output.txt, dyn-artifact-attribution-output.txt
- **Severity**: important
- **Concern**: Auto-binding `proposer-map.tsv` when `ballot_is_neutralized()` is true keys only on sidecar existence plus neutralization, without verifying the map matches the current ballot. A neutralized ballot plus a stale sidecar from a prior round (e.g. overlapping item IDs like `FINDING_1`) can yield wrong `reviewer_slots`/scoreboard labels and wrong reviewer restoration in artifacts without error; only absent IDs fail closed. Existing coverage (`test_attributed_ballot_ignores_stale_sidecar`) covers attributed ballots only, not neutralized ones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ballot-neutrality-output.txt: Add sidecar/ballot consistency checks before auto-bind (item-id set match and non-anonymous proposer values), or require an explicit `--proposer-map-file` on re-tally/MAV paths and fail when the sidecar is older than the ballot rewrite.
  - From dyn-artifact-attribution-output.txt: Stamp the sidecar with a ballot hash or monotonic generation id at write time; have `_resolve_proposer_map` reject stale maps, or require an explicit `--proposer-map-file` on every neutralized tally path. Extend coverage with a neutralized-ballot + stale-sidecar regression test (the branch only covers attributed-ballot stale sidecar ignore in `python/test_review_tally.py:1339-1374`).


