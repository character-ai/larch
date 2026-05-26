# Review Round 3

- Mode: `diff`
- 6 accepted, 14 rejected (13 exonerated)

## Accepted Findings

### FINDING_11: risk-integration: scripts/test-implement-structure.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No mechanical regression guard for Step 5 stall STALL_TRACKING contract Future SKILL.md edit could reintroduce unconditional Set STALL_TRACKING=true or move starting-round-invalid back to Tracking Issues; loop could emit STALL_TRACKING=false while orchestrator still marks [STALLED] Add grep pins to test-implement-structure.sh per plan optional harness
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] STALL_TRACKING durability for Step 5 stall is prompt-only via ship-pr-state seeding Orchestrator parses STALL_TRACKING=false but omits ship-pr-state seed; Step 18 teardown may fail or use stale stall state Mechanize ship-pr-state write from run-step5-review.sh or add structure-test grep guards
- **Suggested revision**: Address the concern above.


### FINDING_2: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] STALL_TRACKING=false for starting-round-invalid depends on prompt-side ship-pr-state seeding with no script or test. Step 5 stall before Step 8 without seeded ship-pr-state can still skip restore and fail teardown or mis-report stall state. Add a small seed helper plus a restore-finalize-state or implement-structure harness for pre–Step 8 stall with STALL_TRACKING=false.
- **Suggested revision**: Address the concern above.


### FINDING_23: **architecture** `skills/implement/SKILL.md:1214` — The expanded `**stall**` bullet is architecturally correct to persist envelope `STALL_TRACKING` into durable state: Step 18 `implement-finalize.sh teardown` reads `STALL_TRACKING` only from `finalize-state.sh` (see `scripts/implement-finalize.sh:1320`), and `restore-finalize-state.sh` rebuilds that file exclusively from `ship-pr-state.sh` (`scripts/restore-finalize-state.sh:35-70`). Retaining the parsed envelope in the orchestrator shell variable alone would not affect `[STALLED]` rename. However, the new “minimal Step-8-shape” seed list is a second, hand-maintained key contract that diverges from the canonical `<!-- write-initial-state-keys:begin/end -->` block at `skills/implement/SKILL.md:1446-1455` (guarded against `scripts/ship-pr.sh` drift by `scripts/test-implement-structure.sh:374-414`). The seed omits many keys present in the canonical set (`HAS_BUMP`, `OOS_PENDING`, `MANIFEST_PATH`, `IMPLEMENT_TMPDIR`, CI counters, etc.). That is safe for the normal Step 5 stall → Step 16 → Step 18 path (ship-pr is not re-entered), but it creates a maintenance hazard: future additions to the Step 8 required-key region will not automatically apply to pre-Step-8 stall seeds, and a mistaken post-stall `ship-pr.sh` resume could see incomplete state. **Suggested fix:** Point the stall seed path at the `write-initial-state-keys` region as SSOT (copy all keys, override only `STALL_TRACKING` / `STALL_STEP`), or add a drift guard in `scripts/test-implement-structure.sh` asserting the Step 5 seed key set is a superset of `LARCH_FINALIZE_STATE_KEYS` plus the ship-pr keys needed if resume ever occurs.
- **Reviewer**: dyn-envelope-contract-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1214` — The expanded `**stall**` bullet is architecturally correct to persist envelope `STALL_TRACKING` into durable state: Step 18 `implement-finalize.sh teardown` reads `STALL_TRACKING` only from `finalize-state.sh` (see `scripts/implement-finalize.sh:1320`), and `restore-finalize-state.sh` rebuilds that file exclusively from `ship-pr-state.sh` (`scripts/restore-finalize-state.sh:35-70`). Retaining the parsed envelope in the orchestrator shell variable alone would not affect `[STALLED]` rename. However, the new “minimal Step-8-shape” seed list is a second, hand-maintained key contract that diverges from the canonical `<!-- write-initial-state-keys:begin/end -->` block at `skills/implement/SKILL.md:1446-1455` (guarded against `scripts/ship-pr.sh` drift by `scripts/test-implement-structure.sh:374-414`). The seed omits many keys present in the canonical set (`HAS_BUMP`, `OOS_PENDING`, `MANIFEST_PATH`, `IMPLEMENT_TMPDIR`, CI counters, etc.). That is safe for the normal Step 5 stall → Step 16 → Step 18 path (ship-pr is not re-entered), but it creates a maintenance hazard: future additions to the Step 8 required-key region will not automatically apply to pre-Step-8 stall seeds, and a mistaken post-stall `ship-pr.sh` resume could see incomplete state. **Suggested fix:** Point the stall seed path at the `write-initial-state-keys` region as SSOT (copy all keys, override only `STALL_TRACKING` / `STALL_STEP`), or add a drift guard in `scripts/test-implement-structure.sh` asserting the Step 5 seed key set is a superset of `LARCH_FINALIZE_STATE_KEYS` plus the ship-pr keys needed if resume ever occurs.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2003-2009
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Parsers section sources lib-implement-round-cap and eval-renames count_prior_degraded_rounds without using it. Extra coupling and load on every parsers CI shard run. Remove the unused source/eval from parsers; keep only in step5-starting-round.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] STALL_TRACKING=false durability depends on prompt-side ship-pr-state seeding; changed Bash does not write ship-pr-state.sh Envelope STALL_TRACKING=false but orchestrator skips seeding; Step 18 teardown requires readable finalize-state.sh from ship-pr-state and can die at implement-finalize.sh:121 Persist STALL_TRACKING in Bash when emitting the terminal envelope or add an integration test for Step 5 stall to Step 18 state files
- **Suggested revision**: Address the concern above.


