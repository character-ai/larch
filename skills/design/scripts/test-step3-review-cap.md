# test-step3-review-cap.sh

Regression harness for `/design` Step 3 two-round review cap handling.

Pins cap-entry behavior, `NEXT_ACTION` routing, pending-round persistence rules, round cursor advancement via `run-step3-review.sh` (invoked from `SKILL.md` Step 3), and the disk-derived Step 3.5 continuation guard under the two-round cap in `plan-review-continuation.sh`. It also exercises the automatic multi-round chain: continuation helper → `python/cli.py plan-review step3-state --auto-continuation-entry` → a second `run-step3-review.sh --no-preview` entry, with prior-round artifacts preserved and Gate C deferred until the heuristic stops. HARD escalation changes panel policy, not the fixed cap of 2.
