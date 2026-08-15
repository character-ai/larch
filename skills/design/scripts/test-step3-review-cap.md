# test-step3-review-cap.sh

Regression harness for `/design` Step 3 two-round review cap handling.

Pins cap-entry behavior, `NEXT_ACTION` routing, pending-round persistence rules, round cursor advancement through the Rust `plan-review run` owner, and the disk-derived Step 3.5 continuation guard under the two-round cap. It also exercises the automatic multi-round chain: Rust continuation → Rust `plan-review step3-state --auto-continuation-entry` → a second `plan-review run --no-preview` entry, with prior-round artifacts preserved and Gate C deferred until the heuristic stops. HARD escalation changes panel policy, not the fixed cap of 2.
