# test-assess-plan-round.sh

Offline regression harness for `assess-plan-round.sh`.

Validates the Step 3.6 HARD gate, missing-snapshot skip, degraded dispatch fail-open path, stale assessor artifact cleanup, tally/env emission, and a two-entry integration case (cursor advance → `write-after` → round-2 assessor firing across Step 3 entries using case-local assessment mocks). Passive-summary Gate B routing through Step 3.6 is covered separately by `scripts/test-design-structure.sh`.
