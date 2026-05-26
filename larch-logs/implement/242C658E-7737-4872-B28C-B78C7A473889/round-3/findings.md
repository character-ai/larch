### FINDING_1: code-quality: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Stall bullet grew far beyond the plan’s three prose edits into a long ship-pr-state seeding contract. Agents may miss parts of the bullet; Step 5 and Step 18 both describe durable state, increasing drift risk. Keep retain/classification edits in the stall bullet; move ship-pr seed/rewrite to Step 18 or a linked subsection.
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] STALL_TRACKING=false for starting-round-invalid depends on prompt-side ship-pr-state seeding with no script or test. Step 5 stall before Step 8 without seeded ship-pr-state can still skip restore and fail teardown or mis-report stall state. Add a small seed helper plus a restore-finalize-state or implement-structure harness for pre–Step 8 stall with STALL_TRACKING=false.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-113
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Hoisted past-cap uses raw -f while starting-round validation uses step5_probe_prior_round_env with sync retry. Past-cap restart immediately after MAV write could theoretically miss hoisted path yet recover via in-loop cap check; asymmetry is fragile for future edits. Use step5_probe_prior_round_env for the hoisted anchor or document in-loop as the mandatory retry backstop.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2003-2009
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Parsers section sources lib-implement-round-cap and eval-renames count_prior_degraded_rounds without using it. Extra coupling and load on every parsers CI shard run. Remove the unused source/eval from parsers; keep only in step5-starting-round.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-145
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Hoisted mav-resume-past-cap flushes batches before emit; in-loop path still emits then flushes. Inconsistent side-effect ordering between two resume paths. Match flush/emit order to the hoisted path in the in-loop branch.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2107-1292
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan allowed lifting write_prior_round but branch added step5_write_prior_round alongside a different convergence helper. Two similarly named helpers with different signatures may confuse future test authors. Rename the step5 helper or add a brief comment distinguishing it from convergence’s accept-count fixture.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] STALL_TRACKING=false durability depends on prompt-side ship-pr-state seeding; changed Bash does not write ship-pr-state.sh Envelope STALL_TRACKING=false but orchestrator skips seeding; Step 18 teardown requires readable finalize-state.sh from ship-pr-state and can die at implement-finalize.sh:121 Persist STALL_TRACKING in Bash when emitting the terminal envelope or add an integration test for Step 5 stall to Step 18 state files
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-116
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Hoisted past-cap anchor uses bare -f; sync retry only in step5_probe_prior_round_env STARTING_ROUND past cap with briefly invisible prior env takes in-loop mav-resume instead of hoisted entry path Use step5_probe_prior_round_env for the hoisted anchor too
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:109-144
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Hoisted mav-resume flushes batches before envelope; in-loop path does the reverse Incremental stdout consumers may see ordering differences between hoisted and in-loop past-cap exits Match in-loop ordering (envelope then flush) unless documented otherwise
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] SKILL stall bullet grew beyond the plan’s ~5-line scoped edit Plan acceptance #10 says only the stall bullet prose triad; diff adds ship-pr-state seeding contract Update plan acceptance or split seeding into a dedicated referenced subsection
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-implement-structure.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No mechanical regression guard for Step 5 stall STALL_TRACKING contract Future SKILL.md edit could reintroduce unconditional Set STALL_TRACKING=true or move starting-round-invalid back to Tracking Issues; loop could emit STALL_TRACKING=false while orchestrator still marks [STALLED] Add grep pins to test-implement-structure.sh per plan optional harness
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **risk-integration** `scripts/ship-pr.sh:622-628` — `ship-pr-state.sh` is already treated as a session-local trust boundary (tampered `IMPLEMENT_TMPDIR` is re-validated). The expanded `SKILL.md` stall bullet now instructs the orchestrator to seed or rewrite `ship-pr-state.sh` on Step 5 stalls so `STALL_TRACKING=false` survives to Step 18; that is correct for this bug but inherits the same trust model (writable only by the implement session). **Suggested fix:** N/A for this PR; any future hardening belongs in a dedicated state-file writer helper, not here.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:114` — The new `larch_err` diagnostic prints full `IMPLEMENT_TMPDIR` and `expected_env_path` to stderr. That can expose local usernames or session paths if logs are shared; it is operational telemetry, not parsed as envelope KVs, and matches existing `larch_err` usage. **Suggested fix:** If log export is a concern, redact or hash paths in a follow-up (out of scope for this fix). ## Verdict From a security and trust-boundary lens, the branch is safe to merge: the artifact anchor is a net improvement, and no injection, auth bypass, or secret-handling regressions were identified in the modified production paths.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] STALL_TRACKING durability for Step 5 stall is prompt-only via ship-pr-state seeding Orchestrator parses STALL_TRACKING=false but omits ship-pr-state seed; Step 18 teardown may fail or use stale stall state Mechanize ship-pr-state write from run-step5-review.sh or add structure-test grep guards
- **Suggested revision**: Address the concern above.

### FINDING_15: architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Hoisted past-cap anchor uses raw -f without sync retry Just-written prior-round env visible to probe but not hoisted anchor; slower in-loop recovery only Reuse step5_probe_prior_round_env for the anchor check
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:139-140
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] In-loop prior_deg lacks numeric validation present at entry Malformed count_prior_degraded_rounds mid-loop can abort under set -e Share entry validation helper for all cap math sites
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:105-117
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Original STARTING_ROUND=5 cap=5 case still needs sync retry not mav-resume If sync ineffective on platform, starting-round-invalid persists (non-tracking) Document residual risk; consider writer-side fsync if reports continue
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-111
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Hoisted vs in-loop flush/envelope ordering differs Future flush semantic changes could diverge paths Align flush-then-envelope at both mav-resume-past-cap sites
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2154-2156
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Diagnostic assertion uses grep co-occurrence Multi-line stderr could false-pass diagnostic key test Use token-aware stderr parser like envelope assertions
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] architecture: scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] IMPLEMENT_TMPDIR pwd -P mismatch not addressed Path mismatch still yields starting-round-invalid after retry Unify tmpdir resolution in a follow-up issue
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] correctness: scripts/lib-implement-round-cap.sh:23-38
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] MAV rounds not counted as degraded Cap-boundary mav-resume-past-cap at STARTING_ROUND=base_cap+1 unavailable Deferred; future DEGRADED_ROUND policy change
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Stall bullet expanded beyond plan with ship-pr-state.sh rewrite/seed prose after review rounds. Plan required only retain-from-envelope + Skip to Step 16 and no other SKILL.md changes; extra prose is out of plan scope and acceptance #10. Amend plan to authorize persistence or revert SKILL.md to planned minimal stall routing.
- **Suggested revision**: Address the concern above.

### FINDING_23: **architecture** `skills/implement/SKILL.md:1214` — The expanded `**stall**` bullet is architecturally correct to persist envelope `STALL_TRACKING` into durable state: Step 18 `implement-finalize.sh teardown` reads `STALL_TRACKING` only from `finalize-state.sh` (see `scripts/implement-finalize.sh:1320`), and `restore-finalize-state.sh` rebuilds that file exclusively from `ship-pr-state.sh` (`scripts/restore-finalize-state.sh:35-70`). Retaining the parsed envelope in the orchestrator shell variable alone would not affect `[STALLED]` rename. However, the new “minimal Step-8-shape” seed list is a second, hand-maintained key contract that diverges from the canonical `<!-- write-initial-state-keys:begin/end -->` block at `skills/implement/SKILL.md:1446-1455` (guarded against `scripts/ship-pr.sh` drift by `scripts/test-implement-structure.sh:374-414`). The seed omits many keys present in the canonical set (`HAS_BUMP`, `OOS_PENDING`, `MANIFEST_PATH`, `IMPLEMENT_TMPDIR`, CI counters, etc.). That is safe for the normal Step 5 stall → Step 16 → Step 18 path (ship-pr is not re-entered), but it creates a maintenance hazard: future additions to the Step 8 required-key region will not automatically apply to pre-Step-8 stall seeds, and a mistaken post-stall `ship-pr.sh` resume could see incomplete state. **Suggested fix:** Point the stall seed path at the `write-initial-state-keys` region as SSOT (copy all keys, override only `STALL_TRACKING` / `STALL_STEP`), or add a drift guard in `scripts/test-implement-structure.sh` asserting the Step 5 seed key set is a superset of `LARCH_FINALIZE_STATE_KEYS` plus the ship-pr keys needed if resume ever occurs.
- **Reviewer**: dyn-envelope-contract-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1214` — The expanded `**stall**` bullet is architecturally correct to persist envelope `STALL_TRACKING` into durable state: Step 18 `implement-finalize.sh teardown` reads `STALL_TRACKING` only from `finalize-state.sh` (see `scripts/implement-finalize.sh:1320`), and `restore-finalize-state.sh` rebuilds that file exclusively from `ship-pr-state.sh` (`scripts/restore-finalize-state.sh:35-70`). Retaining the parsed envelope in the orchestrator shell variable alone would not affect `[STALLED]` rename. However, the new “minimal Step-8-shape” seed list is a second, hand-maintained key contract that diverges from the canonical `<!-- write-initial-state-keys:begin/end -->` block at `skills/implement/SKILL.md:1446-1455` (guarded against `scripts/ship-pr.sh` drift by `scripts/test-implement-structure.sh:374-414`). The seed omits many keys present in the canonical set (`HAS_BUMP`, `OOS_PENDING`, `MANIFEST_PATH`, `IMPLEMENT_TMPDIR`, CI counters, etc.). That is safe for the normal Step 5 stall → Step 16 → Step 18 path (ship-pr is not re-entered), but it creates a maintenance hazard: future additions to the Step 8 required-key region will not automatically apply to pre-Step-8 stall seeds, and a mistaken post-stall `ship-pr.sh` resume could see incomplete state. **Suggested fix:** Point the stall seed path at the `write-initial-state-keys` region as SSOT (copy all keys, override only `STALL_TRACKING` / `STALL_STEP`), or add a drift guard in `scripts/test-implement-structure.sh` asserting the Step 5 seed key set is a superset of `LARCH_FINALIZE_STATE_KEYS` plus the ship-pr keys needed if resume ever occurs.
- **Suggested revision**: Address the concern above.

### FINDING_24: **architecture** `skills/implement/SKILL.md:1214` — Plan acceptance criterion 4 only required three prose edits (category move, retain-from-envelope, drop unconditional `Set STALL_TRACKING=true`). The branch also added orchestrator-side `ship-pr-state.sh` rewrite/seed obligations (round 2, commit `ff40de94`). That expansion is **backed** by the downstream contract (Step 18 block at `skills/implement/SKILL.md:1805-1817` plus `review-implement-step5-loop.md:17`), but it is not reflected in the plan’s acceptance list or scoped file estimate (~5 lines). This is an envelope-contract gap between plan and implementation, not an ungrounded side effect. **Suggested fix:** Amend the plan acceptance criteria to require Step 5 stall paths to persist envelope `STALL_TRACKING` into `ship-pr-state.sh` (rewrite or canonical seed) before `Skip to Step 16`, so reviewers can verify the full orchestrator→teardown chain.
- **Reviewer**: dyn-envelope-contract-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1214` — Plan acceptance criterion 4 only required three prose edits (category move, retain-from-envelope, drop unconditional `Set STALL_TRACKING=true`). The branch also added orchestrator-side `ship-pr-state.sh` rewrite/seed obligations (round 2, commit `ff40de94`). That expansion is **backed** by the downstream contract (Step 18 block at `skills/implement/SKILL.md:1805-1817` plus `review-implement-step5-loop.md:17`), but it is not reflected in the plan’s acceptance list or scoped file estimate (~5 lines). This is an envelope-contract gap between plan and implementation, not an ungrounded side effect. **Suggested fix:** Amend the plan acceptance criteria to require Step 5 stall paths to persist envelope `STALL_TRACKING` into `ship-pr-state.sh` (rewrite or canonical seed) before `Skip to Step 16`, so reviewers can verify the full orchestrator→teardown chain.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] **STALL_TRACKING naming:** No collision with `stall_track` in `skills/review-and-fix/scripts/review-implement-step5-loop.sh:125`. That symbol is a bash-local loop accumulator in a different scope; the envelope/orchestrator contract uses the `STALL_TRACKING` KV emitted by `step5_emit_final_envelope` (`review-implement-step5-loop.sh:64`). The stall bullet’s “assign that parsed value back to the orchestrator `STALL_TRACKING` variable” language is self-consistent with the token-aware parse at `skills/implement/SKILL.md:1206`.
- **Reviewer**: dyn-envelope-contract-output.txt
- **Concern**: - **STALL_TRACKING naming:** No collision with `stall_track` in `skills/review-and-fix/scripts/review-implement-step5-loop.sh:125`. That symbol is a bash-local loop accumulator in a different scope; the envelope/orchestrator contract uses the `STALL_TRACKING` KV emitted by `step5_emit_final_envelope` (`review-implement-step5-loop.sh:64`). The stall bullet’s “assign that parsed value back to the orchestrator `STALL_TRACKING` variable” language is self-consistent with the token-aware parse at `skills/implement/SKILL.md:1206`.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] **ship-pr seed necessity:** Seeding `ship-pr-state.sh` on pre-Step-8 stalls is required for `restore-finalize-state.sh` / teardown to observe `STALL_TRACKING=false`; it is not an orphan side effect. Without it, Step 18 would skip restore when the file is absent (`skills/implement/SKILL.md:1805-1808`) yet still invoke teardown against a missing `finalize-state.sh` (`skills/implement/SKILL.md:1815-1817`), which fails `implement-finalize.sh` validation (`scripts/implement-finalize.sh:119-121`).
- **Reviewer**: dyn-envelope-contract-output.txt
- **Concern**: - **ship-pr seed necessity:** Seeding `ship-pr-state.sh` on pre-Step-8 stalls is required for `restore-finalize-state.sh` / teardown to observe `STALL_TRACKING=false`; it is not an orphan side effect. Without it, Step 18 would skip restore when the file is absent (`skills/implement/SKILL.md:1805-1808`) yet still invoke teardown against a missing `finalize-state.sh` (`skills/implement/SKILL.md:1815-1817`), which fails `implement-finalize.sh` validation (`scripts/implement-finalize.sh:119-121`).
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] **Pre-existing gap:** Early bail paths that jump straight to Step 18 (e.g. Step 0 `STALL_TRACKING=true` at `skills/implement/SKILL.md:420`) still do not seed `ship-pr-state.sh`; NEVER #13 documents that absent state may block restore. This branch does not widen that gap; it closes it specifically for Step 5 `stall` envelopes.
- **Reviewer**: dyn-envelope-contract-output.txt
- **Concern**: - **Pre-existing gap:** Early bail paths that jump straight to Step 18 (e.g. Step 0 `STALL_TRACKING=true` at `skills/implement/SKILL.md:420`) still do not seed `ship-pr-state.sh`; NEVER #13 documents that absent state may block restore. This branch does not widen that gap; it closes it specifically for Step 5 `stall` envelopes.
- **Suggested revision**: Address the concern above.

