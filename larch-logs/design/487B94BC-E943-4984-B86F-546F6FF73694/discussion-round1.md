# Discussion Round 1 — Issue #3662

## Decision 1: /implement cap semantics with degraded rounds
- **Question**: Does "cap = 5" mean a hard ceiling of 5 (drop `ROUND_CAP_INFLATED = base + degraded`), or base 5 + degraded extension (keep today's behavior)?
- **Resolution**: Hard ceiling of 5. Drop the inflation everywhere: `run-step5-review.sh` single-mode `ROUND_CAP_INFLATED`, `review-implement-step5-loop.sh` entry/per-round/post-round `effective_round_cap` math, and the implement SKILL.md Step 5 banner fence.
- **Source**: user

## Decision 2: lib-implement-round-cap.sh removal
- **Question**: With inflation dropped, does `scripts/lib-implement-round-cap.sh` retain any consumer?
- **Resolution**: No. Its only export is `count_prior_degraded_rounds`, called from `review-implement-step5-loop.sh`, `run-step5-review.sh` (single mode), and the implement SKILL.md banner fence — all inflation sites. Remove the lib, `lib-implement-round-cap.md`, `test-lib-implement-round-cap.sh`/`.md`, the Makefile target, and source lines in `review-and-fix.sh` / `run-step5-review.sh`.
- **Source**: user (Step 1c option) + codebase

## Decision 3: DEGRADED_ROUND marker retention
- **Question**: Does the per-round `DEGRADED_ROUND=` marker in `review-and-fix.env` serve anything besides cap inflation?
- **Resolution**: Yes — `round_degraded()` / `find_previous_non_degraded_round()` (`review-and-fix.sh:168-185`, used at `:1639`) compare against the previous non-degraded round. Keep the marker emission; remove only cap math.
- **Source**: codebase

## Decision 4: /design tier cap normalization
- **Question**: SIMPLE Gate C cap 3 → 5; HARD stays 5. Keep tier branching with both arms equal, or flatten?
- **Resolution**: Flatten to a single cap of 5 (`run-step3-review.sh:196-197` tier `case` collapses). Tier still appears in the cap-reached message text. Prose surfaces (`approval-gates.md`, `flags.md`, design SKILL.md, `plan-review.md`, docs) say "5" uniformly.
- **Source**: issue + codebase

## Decision 5: EFFECTIVE_ROUND_CAP envelope key
- **Question**: With a flat cap, keep emitting `EFFECTIVE_ROUND_CAP` in the Step 5 loop envelope?
- **Resolution**: Keep the key (now always equal to the base cap 5) — implement SKILL.md parses it (`cap-hit` copy, `mav-resume-past-cap`) and harnesses assert it; removing it is contract churn with zero behavioral value.
- **Source**: codebase

## Decision 6: /implement --round-cap argument retention
- **Question**: Issue item 2 removes `--round-cap` from `plan-review-loop.sh` (/design). Does /implement's `review-and-fix.sh --round-cap` go too?
- **Resolution**: No. It is the live conduit by which `run-step5-review.sh` passes the base cap; only the /design `--round-cap` chain (`plan-review-loop.sh`, `run-step3-review.sh`, design SKILL.md launch line) is vestigial.
- **Source**: codebase + issue scope
