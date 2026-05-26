### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Hoisted past-cap uses raw -f while probe uses sync+retry STARTING_ROUND=6 with round-5 env briefly invisible: hoisted anchor misses, loop relies on in-loop cap check instead of immediate mav-resume-past-cap Reuse step5_probe_prior_round_env for the hoisted anchor condition
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:2148-2155
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Diagnostic assertions check key presence only not values Wrong entry_effective_cap in larch_err could pass if all keys appear on one line Parse stderr tokens and assert entry_effective_cap and expected_env_path per case
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-111
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Hoisted vs in-loop mav-resume flush/envelope ordering differs Unlikely today but consumers assuming uniform ordering could see divergent side effects Document in review-implement-step5-loop.md or align flush/envelope order with in-loop path
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: `6b382278` — Fix Step 5 starting-round resume handling
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `6b382278` — Fix Step 5 starting-round resume handling
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: `a42811d4` — chore(larch-logs): flush implement run 242C658E-…
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `a42811d4` — chore(larch-logs): flush implement run 242C658E-… **Scope reviewed:** Planned changes in `review-implement-step5-loop.sh`, `review-implement-step5-loop.md`, `skills/implement/SKILL.md` (Step 5 stall bullet), `test-review-and-fix.sh`, and `Makefile`. `larch-logs/implement/…` is treated as intentional run-log noise per review instructions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Hoisted past-cap uses raw -f while artifact guard uses step5_probe_prior_round_env with sync retry. Resume at STARTING_ROUND past entry_effective_cap right after MAV-apply can miss hoisted mav-resume-past-cap on a transient -f miss even though probe would succeed on retry. Route the hoisted anchor through step5_probe_prior_round_env (shared two-attempt contract).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2149-2155
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Diagnostic assertion uses grep co-occurrence on one line Reordered or multi-line diagnostics could pass/fail incorrectly Parse diagnostic tokens with the same scanner as envelopes
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_33: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2237-2249
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Cases 1 and 2 use STARTING_ROUND=5 instead of the plan-specified STARTING_ROUND=4. Acceptance criteria 6.1/6.2 name STARTING_ROUND=4; with that value prior-round-3 already exists so sync-retry and missing-artifact stalls would not be exercised as written. Either update the plan/acceptance text to STARTING_ROUND=5 (matching the incident) or add a comment in the test explaining the deliberate deviation from the written acceptance spec.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_38

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_38: **risk-integration** `Makefile:4-5` — Sister shard targets `test-review-and-fix-dispatch`, `test-review-and-fix-convergence`, and `test-review-and-fix-parsers` are listed on the primary mega-`.PHONY` line (`Makefile:4`), but `test-review-and-fix-step5-starting-round` appears only on the secondary `.PHONY` line (`Makefile:5`). Make behavior is fine, but the split breaks the repo’s usual “all CI harness targets on line 4” convention and makes inventory/drift checks easier to get wrong. **Suggested fix:** Add `test-review-and-fix-step5-starting-round` to the `Makefile:4` mega-`.PHONY` list (and drop the duplicate from line 5 if you want a single source).
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - **risk-integration** `Makefile:4-5` — Sister shard targets `test-review-and-fix-dispatch`, `test-review-and-fix-convergence`, and `test-review-and-fix-parsers` are listed on the primary mega-`.PHONY` line (`Makefile:4`), but `test-review-and-fix-step5-starting-round` appears only on the secondary `.PHONY` line (`Makefile:5`). Make behavior is fine, but the split breaks the repo’s usual “all CI harness targets on line 4” convention and makes inventory/drift checks easier to get wrong. **Suggested fix:** Add `test-review-and-fix-step5-starting-round` to the `Makefile:4` mega-`.PHONY` list (and drop the duplicate from line 5 if you want a single source). **Exonerated (scout prompt):** `test-review-and-fix-step5-starting-round` **does** use `bash scripts/harness-timer.sh $@ ...` consistently with `test-review-and-fix-dispatch` / `convergence` / `parsers` (`Makefile:723-733`). The plan snippet’s bare `bash ...` form was not what landed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2088-2312
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large duplicated test helper block in new section Future parser changes require two edits Hoist shared step5 KV helpers to file scope
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2237
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Case 1 uses STARTING_ROUND=5 vs plan STARTING_ROUND=4 No functional regression; slight plan drift Add comment referencing production incident parameters
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Hoisted past-cap anchor uses bare -f instead of step5_probe_prior_round_env. STARTING_ROUND past cap with existing but briefly invisible prior env: hoisted path skipped; in-loop mav-resume still fires before round body. Reuse step5_probe_prior_round_env for the hoisted anchor condition.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

