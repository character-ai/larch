### OOS_1: [OUT_OF_SCOPE] design-step3-mav.md contract wording inverts result-env precedence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-mav-flow-output.txt
- **Severity**: latent
- **Concern**: The contract says plan-review is read first and “primary result-env values win when both files define the same key,” but `read_step3_result_state` sources `.step3-plan-review-result.env` first and `.step3-review-result.env` second, so on duplicate keys the review env wins (as encoded in `test-design-step3-mav.sh` with conflicting `SCOPE_ANCHOR_FILE` values). Behavior matches the plan’s intent (review-result is authoritative); only the contract wording and the harness label “primary result env wins” are inverted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword `design-step3-mav.md` to say plan-review is the secondary/base read and review-result is primary on conflicts; align the harness assertion label.
  - From dyn-mav-flow-output.txt: The contract says plan-review is primary and wins key conflicts, but the implementation sources plan-review first and then `.step3-review-result.env`, so review-result values win on duplicates (as `test-design-step3-mav.sh` expects for `SCOPE_ANCHOR_FILE`). Behavior matches the normalized handoff; the doc wording is inverted and could cause a bad “fix” later.


