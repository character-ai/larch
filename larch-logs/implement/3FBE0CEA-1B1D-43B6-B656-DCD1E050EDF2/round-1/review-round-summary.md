# Review Round 1

- Mode: `diff`
- 2 accepted, 5 rejected (0 neutral)

## Accepted Findings

### FINDING_6: Step 3 review cap lost harness-pinned rollback literals
- **Reviewer(s)**: dyn-dyn-skill-contracts, dyn-dyn-closure-ratchet
- **Severity**: important
- **Concern**: Step 3 review-round cap prose dropped exact literals required by `skills/design/scripts/test-step3-review-cap.sh`. The compressed prose weakens the machine-pinned rollback and counter-consumption contract and should make the harness fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-contracts: Restore the pinned literal substrings in the Step 3 cap-guard, `NEXT_ACTION=step3b-bypass`, and continuation-helper paragraphs, or update the harness and any downstream docs together if the shorter prose is intentional. Re-run `bash skills/design/scripts/test-step3-review-cap.sh` before merge.
  - From dyn-dyn-closure-ratchet: Restore the deleted literal pins in the cap-entry paragraph (or update the harness if the contract intentionally moved), keeping the full enum names `TALLY_PLAN_REVIEW_STATUS=tally-error`, `LOOP_STATUS=tally-error`, and `LOOP_STATUS=panel-failed` verbatim.


### FINDING_8: Additional Step 3 and Gate B structural literals were removed
- **Reviewer(s)**: dyn-dyn-closure-ratchet
- **Severity**: important
- **Concern**: Other harness-pinned Step 3 and Gate B literals were compressed into paraphrases, including `PLAN_REVIEW_CONTINUE_REASON=explicit-approve`, the launcher-only resume fence phrase, and `explicit per-round prompt`. This breaks prose-as-contract validation across `test-step3-review-cap.sh` and `test-gate-b-apply-mode.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-closure-ratchet: Reinsert the exact harness literals at their prior call sites, or narrow the compression to prose that is not grep-pinned by `skills/design/scripts/test-step3-review-cap.sh` and `skills/design/scripts/test-gate-b-apply-mode.sh`.


