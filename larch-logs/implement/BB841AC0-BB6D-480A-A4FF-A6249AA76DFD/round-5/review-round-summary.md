# Review Round 5

- Mode: `diff`
- 2 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_4: Plan review aborts voting on recoverable aggregator fallback paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `_aggregation_ok_for_voting` / plan-review `execute_round` aborts when `aggregate-findings` returns `AGGREGATED=false` for recoverable reasons such as `dispatch-failed`, `validation-failed`, or `validation-exhausted`, even though `review_aggregate.py` leaves `findings-in-scope.md` unchanged and returns 0 for those paths. Pre-change `execute_round` always reached voter dispatch after aggregation; code review still tallies on `validation-exhausted`. Plan-review rounds can `panel-fail` with voteable findings during aggregator outages or validator exhaustion, before building the neutralized ballot or launching voters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Proceed to ballot compose/voting when findings-in-scope.md is non-empty and unchanged, mirror code review's validation-exhausted bypass, or document fail-closed behavior and apply it consistently to insufficient-input too.
  - From codex-generic-output.txt: Treat return-code-0 aggregator fallback reasons as "use current findings file unchanged," then build `proposer-map.tsv` and neutralize from the current `findings-in-scope.md`; reserve this abort for nonzero aggregate command failures or sidecar coverage failures.


### FINDING_9: Plan-review scoreboard does not split comma-separated multi-proposer labels
- **Reviewer(s)**: dyn-artifact-attribution-output.txt
- **Severity**: important
- **Concern**: Reviewer competition scoreboard rows in `plan_review_tally.py` use the restored proposer string as a single aggregation key and never split comma-separated multi-proposer labels, unlike code review (`review_tally.py`). Merged findings that store `"Codex-Arch, Cursor-Pragmatic"` in the sidecar will be scored as one synthetic reviewer, so competition points/archetype attribution no longer match the per-slot math used on the `/review` and Step 5 paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-attribution-output.txt: Reuse the code-review split when building `score_rows` (or document and test that plan-review merged labels must remain single-proposer), so scoreboards and `findings-classification.tsv` stay aligned with competition semantics.


