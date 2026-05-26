## Decision 1: Primary fix approach
- **Question**: What is the desired fix for the starting-round-invalid false-positive stall?
- **Resolution**: Combined approach — (a) reorder: detect cap-boundary MAV restart and fire `mav-resume-past-cap` before the `starting-round-invalid` guard; (b) reclassify: `starting-round-invalid` no longer sets `STALL_TRACKING=true` (no [STALLED] rename); (c) add diagnostic logging around the file-existence check to surface stat/path data when the guard fires.
- **Source**: user

## Decision 2: MAV-apply DEGRADED_ROUND semantics
- **Question**: Should MAV-apply rounds set `DEGRADED_ROUND=true` so the effective_round_cap inflates?
- **Resolution**: No — defer to a separate issue. Analysis confirms cap inflation does not fix this incident (effective cap inflation makes `round_num > effective_round_cap` LESS likely to fire, not more), and changing it would break the documented `mav-resume-past-cap` contract for cap-hit MAV restart at round N+1==base_cap+1.
- **Source**: user

## Decision 3: Reproducibility / repro investigation
- **Question**: Can we deterministically reproduce the false-positive file-not-found at cap boundary?
- **Resolution**: Unknown — investigate during implementation. Plan must specify a test approach (probe filesystem semantics on macOS for Hypothesis A timing vs Hypothesis B path mismatch); the structural fix (reorder + reclassify) is defensive and works regardless of root cause.
- **Source**: user

## Decision 4: Reclassification breadth
- **Question**: Does reclassification apply to ALL `starting-round-invalid` invocations or only the false-positive cap-boundary subset?
- **Resolution**: All `starting-round-invalid` → non-tracking (`STALL_TRACKING=false`). SKILL.md Step 5 stall-routing prose (line 1214) moves `starting-round-invalid` out of the `Tracking Issues` bucket. Risk: legitimate operator errors (bad --starting-round) won't rename to [STALLED] either; mitigated by `execution-issues.md` logging.
- **Source**: user

## Decision 5: Out-of-scope confirmation (Cursor aggregator empty output)
- **Question**: Is the upstream "Cursor aggregator never produces structured output" issue in scope for this fix?
- **Resolution**: Out of scope. Issue body explicitly says "this is a separate potential issue". Fixing the stall does not require fixing the aggregator; both can stack independently.
- **Source**: codebase (issue body §Context)

## Decision 6: Hard constraint — preserve existing mav-resume-past-cap contract
- **Question**: Must the existing `mav-resume-past-cap` cap-hit MAV restart contract (MAV at round 5 + restart at round 6 → mav-resume-past-cap) be preserved?
- **Resolution**: Yes — hard constraint. Verified from SKILL.md:1263–1265 — orchestrator treats `mav-resume-past-cap` as `complete` and prints info line. The new cap-boundary detection logic must NOT regress this path.
- **Source**: codebase (skills/implement/SKILL.md:1263–1265)
