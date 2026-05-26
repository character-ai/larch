### FINDING_1: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Hoisted past-cap uses raw -f while probe uses sync+retry STARTING_ROUND=6 with round-5 env briefly invisible: hoisted anchor misses, loop relies on in-loop cap check instead of immediate mav-resume-past-cap Reuse step5_probe_prior_round_env for the hoisted anchor condition
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:115
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] starting-round-invalid EFFECTIVE_ROUND_CAP uses base_cap not entry_effective_cap Degraded prior rounds inflate entry_effective_cap; stderr shows 10 but envelope EFFECTIVE_ROUND_CAP=5 Mirror entry_effective_cap in the terminal envelope KV
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2149-2155
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Diagnostic assertion uses grep co-occurrence on one line Reordered or multi-line diagnostics could pass/fail incorrectly Parse diagnostic tokens with the same scanner as envelopes
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] STALL_TRACKING=false is prose-only on Step 5 stall→Step 16 path Without ship-pr-state/finalize-state, Step 18 may not see envelope false; wrong [STALLED] rename risk remains orchestrator-dependent Document or script persistence of STALL_TRACKING before Step 18 when Step 8+ is skipped
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2088-2312
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large duplicated test helper block in new section Future parser changes require two edits Hoist shared step5 KV helpers to file scope
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2237
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Case 1 uses STARTING_ROUND=5 vs plan STARTING_ROUND=4 No functional regression; slight plan drift Add comment referencing production incident parameters
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:142-145
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] In-loop vs hoisted flush/envelope order differs Pre-existing; hoisted order matches plan FINDING_16 Unify ordering in a separate refactor if desired
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] correctness: scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] IMPLEMENT_TMPDIR path normalization not in this PR Hypothesis B path mismatch may still defeat sync retry Address in follow-up if diagnostics show mismatch
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Hoisted past-cap anchor uses bare -f instead of step5_probe_prior_round_env. STARTING_ROUND past cap with existing but briefly invisible prior env: hoisted path skipped; in-loop mav-resume still fires before round body. Reuse step5_probe_prior_round_env for the hoisted anchor condition.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2232-2242
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Case 1 only tests sync creating missing prior file, not pre-existing file becoming visible on retry. Regression breaking second -f on existing path would not be caught; production incident (file exists) under-covered. Add test with pre-written prior artifact and shadow sync that does not create the file.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:115
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] starting-round-invalid envelope emits EFFECTIVE_ROUND_CAP=base_cap not entry_effective_cap. STARTING_ROUND=11 with entry_effective_cap=10: envelope shows 5, diagnostic shows 10. Emit entry_effective_cap in envelope or document envelope vs diagnostic split.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Retain STALL_TRACKING prose does not require writing parsed value to ship-pr/finalize state. Step 5 stall before ship-pr-state: teardown may not see envelope false; [STALLED] rename still orchestrator/state dependent. Explicitly assign STALL_TRACKING from envelope and persist when state files are written.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Strict > prevents mav-resume at STARTING_ROUND equal to base cap. STARTING_ROUND=5 base_cap=5 after 4 MAV rounds gets round 5 not mav-resume-past-cap per deferred MAV-as-degraded decision. Future issue if cap-hit must short-circuit at equality.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/SKILL.md:1207
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] SKILL.md stall routing change has no automated regression guard An implement agent could still overwrite STALL_TRACKING=true after parsing starting-round-invalid with false, re-breaking tracking rename behavior Add test-implement-structure grep or envelope-driven fixture asserting Retain STALL_TRACKING prose and no Set STALL_TRACKING=true in stall bullet
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:2092-2313
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Missing test for entry_prior_deg non-numeric env-write-failed path Regression in count_prior_degraded_rounds validation could ship without CI failure Add harness case stubbing count_prior_degraded_rounds to emit non-numeric output; assert stall env-write-failed STALL_TRACKING=true exit 2
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:2232-2242
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No pre-seeded STARTING_ROUND=5 cap-boundary happy path Production resume at round 5 with round-4 already present is untested; only sync-retry path is covered Add case with rounds 1-4 pre-created STARTING_ROUND=5 asserting complete and round body invoked without sync
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.md:11
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness doc omits new step5-starting-round section Contributors running --section step5-starting-round may not find it documented Update test-review-and-fix.md --section list and one-line case summary
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:2148-2155
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Diagnostic assertions check key presence only not values Wrong entry_effective_cap in larch_err could pass if all keys appear on one line Parse stderr tokens and assert entry_effective_cap and expected_env_path per case
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-111
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Hoisted vs in-loop mav-resume flush/envelope ordering differs Unlikely today but consumers assuming uniform ordering could see divergent side effects Document in review-implement-step5-loop.md or align flush/envelope order with in-loop path
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: scripts/test-run-step5-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No E2E loop --starting-round integration test IMPLEMENT_TMPDIR path mismatch between writer and reader would not be caught by unit tests Add deferred integration harness when touching run-step5-review.sh tmpdir resolution
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:142-145
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] In-loop mav-resume-past-cap largely unreachable post-hoist Low risk; hoisted path is tested; in-loop branch is defense-in-depth only Keep COVERAGE_NOTE or add opt-in test seam if in-loop coverage becomes required
- **Suggested revision**: Address the concern above.

### FINDING_22: `6b382278` — Fix Step 5 starting-round resume handling
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `6b382278` — Fix Step 5 starting-round resume handling
- **Suggested revision**: Address the concern above.

### FINDING_23: `a42811d4` — chore(larch-logs): flush implement run 242C658E-…
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `a42811d4` — chore(larch-logs): flush implement run 242C658E-… **Scope reviewed:** Planned changes in `review-implement-step5-loop.sh`, `review-implement-step5-loop.md`, `skills/implement/SKILL.md` (Step 5 stall bullet), `test-review-and-fix.sh`, and `Makefile`. `larch-logs/implement/…` is treated as intentional run-log noise per review instructions.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:81` — On artifact miss, `step5_probe_prior_round_env` invokes the global `sync` utility (best-effort, once per miss). That is not a privilege boundary escape, but on a shared host it can add brief system-wide flush latency during Step 5 restarts. **Suggested fix:** None required for this bugfix; if latency becomes an issue, consider a narrower retry (e.g., `fsync` on a known file descriptor) in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:114` — The new `larch_err` diagnostic prints `IMPLEMENT_TMPDIR` and `expected_env_path` to stderr. That aids debugging path mismatches but may surface full local paths in CI logs or shared run artifacts. **Suggested fix:** If logs are widely published, a follow-up could redact home-directory prefixes using existing redaction helpers elsewhere in larch.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **architecture** `scripts/lib-implement-round-cap.sh:28-37` — `count_prior_degraded_rounds` trusts `DEGRADED_ROUND=true` in prior `review-and-fix.env` files under `IMPLEMENT_TMPDIR`. Anyone who can write that tmpdir during a run could inflate the effective cap (pre-existing behavior; this branch does not worsen it beyond computing cap math earlier at loop entry). **Suggested fix:** Out of scope here; tmpdir integrity is already part of the implement session trust model.
- **Suggested revision**: Address the concern above.

### FINDING_27: architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Hoisted past-cap uses raw -f while artifact guard uses step5_probe_prior_round_env with sync retry. Resume at STARTING_ROUND past entry_effective_cap right after MAV-apply can miss hoisted mav-resume-past-cap on a transient -f miss even though probe would succeed on retry. Route the hoisted anchor through step5_probe_prior_round_env (shared two-attempt contract).
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] STALL_TRACKING retain-from-envelope prose does not require persisting parsed values into ship-pr-state before Step 16. Step 5 stall skips Step 8 ship-pr-state seeding; Step 18 teardown reads finalize-state from ship-pr, so envelope STALL_TRACKING=false may not affect mechanical [STALLED] rename. Add SKILL-directed seed or key-based patch of ship-pr-state.sh with parsed STALL_TRACKING before Step 16/18.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:115
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] starting-round-invalid envelope emits EFFECTIVE_ROUND_CAP=base_cap while diagnostics include entry_effective_cap. Runs with degraded prior rounds show entry_effective_cap in stderr but a lower EFFECTIVE_ROUND_CAP in the terminal envelope, confusing cap-boundary triage. Pass entry_effective_cap into step5_emit_final_envelope for starting-round-invalid (or document and test the intentional split).
- **Suggested revision**: Address the concern above.

### FINDING_30: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2232-2242
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No test for prior artifact present on first probe without sync retry. Regression coverage exercises only the sync-recovery path; a straight-line post-MAV resume with visible round-4 env is untested. Add a noop-sync case with rounds 1-4 pre-created and STARTING_ROUND=5 expecting complete.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] architecture: scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] IMPLEMENT_TMPDIR pwd -P resolution unchanged. Path mismatch between writer and reader would still fail after sync retry; diagnostics are the mitigation. Address in a follow-up if production diagnostics show mismatched IMPLEMENT_TMPDIR paths.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] correctness: scripts/lib-implement-round-cap.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] MAV rounds do not set DEGRADED_ROUND=true. effective_round_cap stays at base_cap after four MAV rounds; cap-hit via hoisted mav-resume requires STARTING_ROUND strictly greater than cap. Deferred per plan; future MAV-as-degraded change would touch hoisted and in-loop checks together.
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2237-2249
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Cases 1 and 2 use STARTING_ROUND=5 instead of the plan-specified STARTING_ROUND=4. Acceptance criteria 6.1/6.2 name STARTING_ROUND=4; with that value prior-round-3 already exists so sync-retry and missing-artifact stalls would not be exercised as written. Either update the plan/acceptance text to STARTING_ROUND=5 (matching the incident) or add a comment in the test explaining the deliberate deviation from the written acceptance spec.
- **Suggested revision**: Address the concern above.

### FINDING_34: **correctness** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:113-115` — On the `starting-round-invalid` path, the diagnostic line reports `entry_effective_cap` (which includes inflated cap from prior degraded rounds), but the terminal envelope still passes `"$base_cap"` as `EFFECTIVE_ROUND_CAP`. For cases like `inflated-anchor-reject` (`STARTING_ROUND=11`, five prior `DEGRADED_ROUND=true` rounds), stderr shows `entry_effective_cap=10` while stdout emits `EFFECTIVE_ROUND_CAP=5`, so token-aware orchestrator parsing and operator triage can disagree on the effective cap for the same failure. **Suggested fix:** Pass `"$entry_effective_cap"` (not `"$base_cap"`) as the ninth argument to `step5_emit_final_envelope` on the `starting-round-invalid` branch, and update `step5_assert_envelope` expectations in `test-review-and-fix.sh` case 4a (and any docs that describe the stall envelope) to match.
- **Reviewer**: dyn-bash-stub-mechanics-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:113-115` — On the `starting-round-invalid` path, the diagnostic line reports `entry_effective_cap` (which includes inflated cap from prior degraded rounds), but the terminal envelope still passes `"$base_cap"` as `EFFECTIVE_ROUND_CAP`. For cases like `inflated-anchor-reject` (`STARTING_ROUND=11`, five prior `DEGRADED_ROUND=true` rounds), stderr shows `entry_effective_cap=10` while stdout emits `EFFECTIVE_ROUND_CAP=5`, so token-aware orchestrator parsing and operator triage can disagree on the effective cap for the same failure. **Suggested fix:** Pass `"$entry_effective_cap"` (not `"$base_cap"`) as the ninth argument to `step5_emit_final_envelope` on the `starting-round-invalid` branch, and update `step5_assert_envelope` expectations in `test-review-and-fix.sh` case 4a (and any docs that describe the stall envelope) to match.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-bash-stub-mechanics-output.txt
- **Concern**: - **risk-integration** — The branch diff includes committed implement run artifacts under `larch-logs/implement/242C658E-7737-4872-B28C-B78C7A473889/` (breadcrumbs, manifest, plan copy). These are outside the six-file scope in the plan and should not ship with the fix. **Commits on branch:** `6b382278` (fix), `a42811d4` (larch-logs flush).
- **Suggested revision**: Address the concern above.

### FINDING_36: **risk-integration** `Makefile:717-719` — The comment above `test-review-and-fix` still says CI uses “the three section targets below,” but the branch adds a fourth sharded target (`test-review-and-fix-step5-starting-round` at `Makefile:732-733`). That mismatch is easy to miss when extending Step 5 harness coverage and does not match the four-target layout now on `test-harnesses-6` (`Makefile:55`). **Suggested fix:** Update the comment to “four section targets” and name `step5-starting-round` alongside `dispatch`, `convergence`, and `parsers`, mirroring the split described in the `test-harnesses-5` / `test-harnesses-6` shard lines (`Makefile:53-55`).
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - **risk-integration** `Makefile:717-719` — The comment above `test-review-and-fix` still says CI uses “the three section targets below,” but the branch adds a fourth sharded target (`test-review-and-fix-step5-starting-round` at `Makefile:732-733`). That mismatch is easy to miss when extending Step 5 harness coverage and does not match the four-target layout now on `test-harnesses-6` (`Makefile:55`). **Suggested fix:** Update the comment to “four section targets” and name `step5-starting-round` alongside `dispatch`, `convergence`, and `parsers`, mirroring the split described in the `test-harnesses-5` / `test-harnesses-6` shard lines (`Makefile:53-55`).
- **Suggested revision**: Address the concern above.

### FINDING_37: **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.md:11` — The harness contract still documents `--section dispatch|convergence|parsers` only, with no mention of `step5-starting-round`, even though `test-review-and-fix.sh:35` accepts it and `Makefile:732-733` runs it under CI via `test-harnesses-6`. Contributors following the doc may run the wrong shard or assume the new cases are covered by `parsers`. **Suggested fix:** Extend line 11 to include `step5-starting-round` and briefly describe that it exercises entry-time cap resume, artifact probe/sync retry, and `starting-round-invalid` envelopes in `review-implement-step5-loop.sh`.
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.md:11` — The harness contract still documents `--section dispatch|convergence|parsers` only, with no mention of `step5-starting-round`, even though `test-review-and-fix.sh:35` accepts it and `Makefile:732-733` runs it under CI via `test-harnesses-6`. Contributors following the doc may run the wrong shard or assume the new cases are covered by `parsers`. **Suggested fix:** Extend line 11 to include `step5-starting-round` and briefly describe that it exercises entry-time cap resume, artifact probe/sync retry, and `starting-round-invalid` envelopes in `review-implement-step5-loop.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_38: **risk-integration** `Makefile:4-5` — Sister shard targets `test-review-and-fix-dispatch`, `test-review-and-fix-convergence`, and `test-review-and-fix-parsers` are listed on the primary mega-`.PHONY` line (`Makefile:4`), but `test-review-and-fix-step5-starting-round` appears only on the secondary `.PHONY` line (`Makefile:5`). Make behavior is fine, but the split breaks the repo’s usual “all CI harness targets on line 4” convention and makes inventory/drift checks easier to get wrong. **Suggested fix:** Add `test-review-and-fix-step5-starting-round` to the `Makefile:4` mega-`.PHONY` list (and drop the duplicate from line 5 if you want a single source).
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - **risk-integration** `Makefile:4-5` — Sister shard targets `test-review-and-fix-dispatch`, `test-review-and-fix-convergence`, and `test-review-and-fix-parsers` are listed on the primary mega-`.PHONY` line (`Makefile:4`), but `test-review-and-fix-step5-starting-round` appears only on the secondary `.PHONY` line (`Makefile:5`). Make behavior is fine, but the split breaks the repo’s usual “all CI harness targets on line 4” convention and makes inventory/drift checks easier to get wrong. **Suggested fix:** Add `test-review-and-fix-step5-starting-round` to the `Makefile:4` mega-`.PHONY` list (and drop the duplicate from line 5 if you want a single source). **Exonerated (scout prompt):** `test-review-and-fix-step5-starting-round` **does** use `bash scripts/harness-timer.sh $@ ...` consistently with `test-review-and-fix-dispatch` / `convergence` / `parsers` (`Makefile:723-733`). The plan snippet’s bare `bash ...` form was not what landed.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] `scripts/test-harness-shards-coverage.md:19` still names only `test-review-and-fix-dispatch` and `test-review-and-fix-convergence` as CI section variants (predating `parsers`; now further behind with `step5-starting-round`). Worth a follow-up doc pass, not introduced solely by the Makefile target wiring.
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - `scripts/test-harness-shards-coverage.md:19` still names only `test-review-and-fix-dispatch` and `test-review-and-fix-convergence` as CI section variants (predating `parsers`; now further behind with `step5-starting-round`). Worth a follow-up doc pass, not introduced solely by the Makefile target wiring.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] The branch also commits `larch-logs/implement/242C658E-.../` artifacts (`diff.txt` hunks ~119–510). That is unrelated to harness integration and widens the PR surface beyond the six scoped implementation files.
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - The branch also commits `larch-logs/implement/242C658E-.../` artifacts (`diff.txt` hunks ~119–510). That is unrelated to harness integration and widens the PR surface beyond the six scoped implementation files.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] Case 1 in the plan used `STARTING_ROUND=4`; the landed test uses `STARTING_ROUND=5` (`skills/review-and-fix/scripts/test-review-and-fix.sh:2237`), which still exercises sync-retry for the missing prior round but is a mild acceptance/doc drift item, not a Makefile harness defect.
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - Case 1 in the plan used `STARTING_ROUND=4`; the landed test uses `STARTING_ROUND=5` (`skills/review-and-fix/scripts/test-review-and-fix.sh:2237`), which still exercises sync-retry for the missing prior round but is a mild acceptance/doc drift item, not a Makefile harness defect.
- **Suggested revision**: Address the concern above.

