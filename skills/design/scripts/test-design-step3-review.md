# test-design-step3-review.sh

Offline harness for Step 3 reporting behavior. It exercises the Rust `plan-review run --record-report-evidence` owner and the live wrapper, verifies that terminal and escalation evidence stay KV-clean, and confirms that only genuine Step 3 failures record escalation ledger evidence while normal main-agent handoffs do not.
