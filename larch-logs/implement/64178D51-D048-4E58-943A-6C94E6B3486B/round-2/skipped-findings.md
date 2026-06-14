### OOS_3: Deleted shell harnesses replaced by thin pytest with major behavioral gaps
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-plan-cli-contracts-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Large deleted shell harnesses (`test-plan-review-loop.sh`, `test-run-step3-review.sh`, `test-dispatch-plan-voters.sh`, etc.) were retargeted in the Makefile to `python/test_plan_review.py` (and a thin `python/test_plan_review_panel.py`), but those modules mostly smoke-test CLI usage. Plan-required scenarios are missing: cap behavior, `review-round-count.txt` persist-before-launch/rollback, terminal `LOOP_STATUS` / `STEP3_REVIEW_LOOP_STATUS` matrix, Gate B dedup restore, panel vendor matrix, parse-rate retry, retally env refresh, and round snapshot/timing idempotency. CI can pass while regressions in embedded bash logic go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port high-risk harness scenarios into pytest with injectable subprocess seams or retain focused shell harnesses until parity exists
  - From cursor-specialist-testing-output.txt: Port plan-listed cases from deleted harnesses into pytest with injectable subprocess seams, or retain bash harnesses until parity exists
  - From dyn-plan-cli-contracts-output.txt: Port the retired harness scenarios into `python/test_plan_review.py` (or a dedicated integration module) before deleting the last behavioral references, so CI still pins the env/KV contracts the wrappers parse.
  - From dyn-retired-path-sweep-output.txt: Port the high-value harness scenarios into `python/test_plan_review.py` and `python/test_plan_review_panel.py` (stub subprocess seams where needed) before relying on the thin pytest layer as the sole regression gate.



