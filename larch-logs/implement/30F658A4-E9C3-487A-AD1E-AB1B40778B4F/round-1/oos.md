### FINDING_13: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/test-step-7a.md:1-27` — The Cases list still documents 21 named scenarios while the harness defines 23 `new_case` invocations (e.g. `rebase-unexpected-rc`, `quiet-diagram-skip-contract` are implemented but not listed). This drift predates the two new fork cases; this branch renumbered entries without closing the gap. **Suggested fix:** Align the markdown inventory with every `new_case` in `test-step-7a.sh` in a follow-up docs-only pass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/generate-code-flow-diagram.sh:43-44` — Invalid `--base-remote` / `--base-ref` values are rejected by regex (per plan), but no dedicated harness asserts `fail_usage` exit 2; coverage is indirect via step-7a stub argv logging only. The plan explicitly waived a direct generator argv harness, so this is informational only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_15: risk-integration: skills/implement/scripts/test-generate-code-flow-diagram.sh:45-60
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Real generator prompt base selection is untested after adding --base-remote/--base-ref A typo leaving origin/main hardcoded at generate-code-flow-diagram.sh:58 passes test-step-7a stub assertions and the unchanged generator harness in make lint Extend test-generate-code-flow-diagram.sh with an upstream-only fixture and prompt-file assertion for --base-remote upstream --base-ref main
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/rebase-checkpoint-probe.sh:24-50` — `--base-remote` / `--base-ref` are forwarded to `rebase-push.sh` without local regex validation (rebase-push validates downstream). Pre-existing; not introduced by this branch. **Suggested fix:** Optional defense-in-depth: mirror `rebase-push.sh` validation at the probe boundary for SKILL.md call sites that pass argv directly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/implement/scripts/generate-code-flow-diagram.sh:27-35` — `--model` remains unconstrained while new base-ref flags are validated. Pre-existing surface. **Suggested fix:** If hardening is desired later, restrict `--model` to an allowlist of known model slugs before passing to `launch-claude-subprocess.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] correctness: scripts/rebase-push.sh:144-158
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] skip-if-pushed hard-codes origin for ls-remote while 7a.r fork mode rebases against upstream via BASE_REMOTE. On a fork with branch pushed to upstream but not origin, skip-if-pushed may not short-circuit and may attempt an unnecessary rebase path. Pre-existing; consider aligning skip-if-pushed with BASE_REMOTE in a separate change if fork push semantics matter.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/generate-code-flow-diagram.sh:43-44
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No direct harness covers invalid --base-remote/--base-ref argv rejection. Manual or future caller typos are only caught at runtime via fail_usage; CI does not pin the exit-2 contract. Optional follow-up: small argv-validation cases in a dedicated test script (out of scope for #2844 per plan).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-7a.md:5-27` — The sibling case list still omits harness cases `rebase-unexpected-rc` and `quiet-diagram-skip-contract` (present in `test-step-7a.sh` before this PR). This PR added the two planned fork entries but did not close that inventory gap (tracked separately as #2862 per prior review notes). **Suggested fix:** Update `test-step-7a.md` in a follow-up issue, not required for #2844 plan closure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-7a.md:11-16` — Cases 5–8 still say sanitizer rejection “skips summary upsert,” but the harness asserts `tracking-issue-summary.sh` runs (pre-existing doc/harness mismatch, not introduced here). **Suggested fix:** Align prose with harness behavior under #2862.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-step-7a.md:1-27
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Case inventory omits rebase-unexpected-rc and quiet-diagram-skip-contract Operators relying on .md under-count harness coverage Pre-existing; sync .md with all new_case names in a follow-up
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] architecture: scripts/rebase-push.sh:155
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] skip-if-pushed always checks origin heads Fork mode rebases against upstream but may still skip based on origin push state Not introduced by this diff; track separately if fork skip semantics should use BASE_REMOTE
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

