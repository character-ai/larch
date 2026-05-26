# Review Round 1

- Mode: `diff`
- 14 accepted, 12 rejected (10 exonerated)

## Accepted Findings

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


### FINDING_2: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:115
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] starting-round-invalid EFFECTIVE_ROUND_CAP uses base_cap not entry_effective_cap Degraded prior rounds inflate entry_effective_cap; stderr shows 10 but envelope EFFECTIVE_ROUND_CAP=5 Mirror entry_effective_cap in the terminal envelope KV
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


### FINDING_34: **correctness** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:113-115` — On the `starting-round-invalid` path, the diagnostic line reports `entry_effective_cap` (which includes inflated cap from prior degraded rounds), but the terminal envelope still passes `"$base_cap"` as `EFFECTIVE_ROUND_CAP`. For cases like `inflated-anchor-reject` (`STARTING_ROUND=11`, five prior `DEGRADED_ROUND=true` rounds), stderr shows `entry_effective_cap=10` while stdout emits `EFFECTIVE_ROUND_CAP=5`, so token-aware orchestrator parsing and operator triage can disagree on the effective cap for the same failure. **Suggested fix:** Pass `"$entry_effective_cap"` (not `"$base_cap"`) as the ninth argument to `step5_emit_final_envelope` on the `starting-round-invalid` branch, and update `step5_assert_envelope` expectations in `test-review-and-fix.sh` case 4a (and any docs that describe the stall envelope) to match.
- **Reviewer**: dyn-bash-stub-mechanics-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:113-115` — On the `starting-round-invalid` path, the diagnostic line reports `entry_effective_cap` (which includes inflated cap from prior degraded rounds), but the terminal envelope still passes `"$base_cap"` as `EFFECTIVE_ROUND_CAP`. For cases like `inflated-anchor-reject` (`STARTING_ROUND=11`, five prior `DEGRADED_ROUND=true` rounds), stderr shows `entry_effective_cap=10` while stdout emits `EFFECTIVE_ROUND_CAP=5`, so token-aware orchestrator parsing and operator triage can disagree on the effective cap for the same failure. **Suggested fix:** Pass `"$entry_effective_cap"` (not `"$base_cap"`) as the ninth argument to `step5_emit_final_envelope` on the `starting-round-invalid` branch, and update `step5_assert_envelope` expectations in `test-review-and-fix.sh` case 4a (and any docs that describe the stall envelope) to match.
- **Suggested revision**: Address the concern above.


### FINDING_36: **risk-integration** `Makefile:717-719` — The comment above `test-review-and-fix` still says CI uses “the three section targets below,” but the branch adds a fourth sharded target (`test-review-and-fix-step5-starting-round` at `Makefile:732-733`). That mismatch is easy to miss when extending Step 5 harness coverage and does not match the four-target layout now on `test-harnesses-6` (`Makefile:55`). **Suggested fix:** Update the comment to “four section targets” and name `step5-starting-round` alongside `dispatch`, `convergence`, and `parsers`, mirroring the split described in the `test-harnesses-5` / `test-harnesses-6` shard lines (`Makefile:53-55`).
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - **risk-integration** `Makefile:717-719` — The comment above `test-review-and-fix` still says CI uses “the three section targets below,” but the branch adds a fourth sharded target (`test-review-and-fix-step5-starting-round` at `Makefile:732-733`). That mismatch is easy to miss when extending Step 5 harness coverage and does not match the four-target layout now on `test-harnesses-6` (`Makefile:55`). **Suggested fix:** Update the comment to “four section targets” and name `step5-starting-round` alongside `dispatch`, `convergence`, and `parsers`, mirroring the split described in the `test-harnesses-5` / `test-harnesses-6` shard lines (`Makefile:53-55`).
- **Suggested revision**: Address the concern above.


### FINDING_37: **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.md:11` — The harness contract still documents `--section dispatch|convergence|parsers` only, with no mention of `step5-starting-round`, even though `test-review-and-fix.sh:35` accepts it and `Makefile:732-733` runs it under CI via `test-harnesses-6`. Contributors following the doc may run the wrong shard or assume the new cases are covered by `parsers`. **Suggested fix:** Extend line 11 to include `step5-starting-round` and briefly describe that it exercises entry-time cap resume, artifact probe/sync retry, and `starting-round-invalid` envelopes in `review-implement-step5-loop.sh`.
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.md:11` — The harness contract still documents `--section dispatch|convergence|parsers` only, with no mention of `step5-starting-round`, even though `test-review-and-fix.sh:35` accepts it and `Makefile:732-733` runs it under CI via `test-harnesses-6`. Contributors following the doc may run the wrong shard or assume the new cases are covered by `parsers`. **Suggested fix:** Extend line 11 to include `step5-starting-round` and briefly describe that it exercises entry-time cap resume, artifact probe/sync retry, and `starting-round-invalid` envelopes in `review-implement-step5-loop.sh`.
- **Suggested revision**: Address the concern above.


### FINDING_4: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] STALL_TRACKING=false is prose-only on Step 5 stall→Step 16 path Without ship-pr-state/finalize-state, Step 18 may not see envelope false; wrong [STALLED] rename risk remains orchestrator-dependent Document or script persistence of STALL_TRACKING before Step 18 when Step 8+ is skipped
- **Suggested revision**: Address the concern above.


