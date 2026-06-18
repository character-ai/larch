### OOS_1: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `python/design_pause.py:64-166` — `pause_save_main` tags `STEP=3` when `.step3-reentry` exists but never calls `plan-review step3-state --direct-review-pause-hygiene` before publish. Pre-#3681 `scripts/design-pause-save.sh` did (`|| true`). **Why out of scope:** `design_pause.py` is unchanged on this branch; the gap predates #4731. **Suggested fix:** invoke `--direct-review-pause-hygiene` before `log-publish` when `.step3-reentry` is present, matching the retired shell ordering.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `python/design_pause.py:125-221` — `pause_save_main` never calls `plan-review step3-state --direct-review-pause-hygiene` when `.step3-reentry` is present, though the legacy `design-pause-save.sh` did (removed in #3681). This PR implements the handler and unit-tests it, but pause-save still snapshots unstripped downstream state on mid–Step-3 pause. **Why OOS:** `design_pause.py` is unchanged; behavior predates this branch.
- **Suggested revision**: Address the concern above.


