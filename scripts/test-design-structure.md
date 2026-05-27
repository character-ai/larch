# test-design-structure.sh

Structural guard for the `/design` two-tier contract.

The harness asserts that `/design` exposes only SIMPLE/HARD tier routing, rejects `--trivial`, uses the `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel, runs plan validation unconditionally through `invoke-plan-validator.sh`, includes per-tier Step 3 review-round caps, and no longer references quick-review or v1 budget helpers.

It also verifies `plan-review-loop.sh` remains stateless with respect to `review-round-count.txt`; Step 3 in `SKILL.md` owns the counter and passes the computed `--round-num`.
