# test-design-step3-review.sh

Offline harness for Step 3 reporting behavior. It exercises `python/plan_review.py` and `python/cli.py plan-review run --record-report-evidence` static checks, verifies that terminal and escalation evidence stay KV-clean, and confirms that only genuine Step 3 failures record escalation ledger evidence while normal main-agent handoffs do not.
