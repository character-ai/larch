# test-design-step3-review.sh

Offline harness for Step 3 reporting behavior. It exercises `review-design-step3-loop.sh` through the existing `run-step3-review.sh` stubs and checks that terminal and escalation evidence stay KV-clean. It also runs `design-step3-review.sh` against fake plugin roots to verify missing result KVs degrade to `panel-failed` with a stderr warning and legacy `LOOP_STATUS=panel-failed` back-maps to `STEP3_REVIEW_LOOP_STATUS=panel-failed`.
