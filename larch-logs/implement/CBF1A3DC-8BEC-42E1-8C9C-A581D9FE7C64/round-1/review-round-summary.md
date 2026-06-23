# Review Round 1

- Mode: `diff`
- 2 accepted, 6 rejected (0 neutral)

## Accepted Findings

### FINDING_6: `_retain_oos_for_slot` violates keyword-only lint
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: blocking
- **Concern**: The new helper at `python/plan_review_round.py:170` violates the branch's `lint keyword-only` rule now wired into `make py-lint`. `python3 python/cli.py lint keyword-only` exits 1 with `plan_review_round.py:_retain_oos_for_slot missing *`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Make `slot_name` keyword-only and update the call site, for example `def _retain_oos_for_slot(oos_counts_by_slot: dict[str, int], *, slot_name: str) -> bool:`.


### FINDING_7: `_retain_oos_for_label` violates keyword-only lint
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: blocking
- **Concern**: The new helper at `python/review_pipeline.py:1424` also violates the newly enforced keyword-only lint, so the required lint target fails before tests can pass. The same command reports `review_pipeline.py:_retain_oos_for_label missing *`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Make `label` keyword-only and update the call site, for example `_retain_oos_for_label(oos_counts_by_label, label=label)`.


