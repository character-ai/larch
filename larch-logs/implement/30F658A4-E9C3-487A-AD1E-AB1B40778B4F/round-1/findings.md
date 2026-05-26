### FINDING_1: code-quality: skills/implement/scripts/step-7a.sh:79-101,334-338
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] is_small_non_runtime_change reads base_remote/base_ref assigned much later under set -u A refactor that calls the classifier before base_remote/base_ref are set aborts with unbound variable instead of degrading to diagram generation Initialize base_remote/base_ref in the top-level defaults block or pass them as function arguments at the sole call site
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/scripts/test-step-7a.sh:338-390
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate fork fixture helpers mirror make_skip_repo with only commit payload differing Future fixture fixes must be applied in three places or fork cases drift Factor a shared make_forked_repo helper parameterized by changed files
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-implement-rebase-macro.sh:2029-2035
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] (C') step-7a assertion weakened to file-scope base_remote=/base_ref= grep A spurious late base_remote= line could satisfy the harness without correct fork policy placement Keep BASE_ARGS proximity check and add a bounded line-range check near session-key resolution
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-step-7a.md:1-27
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Case inventory omits rebase-unexpected-rc and quiet-diagram-skip-contract Operators relying on .md under-count harness coverage Pre-existing; sync .md with all new_case names in a follow-up
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: scripts/rebase-push.sh:155
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] skip-if-pushed always checks origin heads Fork mode rebases against upstream but may still skip based on origin push state Not introduced by this diff; track separately if fork skip semantics should use BASE_REMOTE
- **Suggested revision**: Address the concern above.

### FINDING_6: Module-level `base_remote` / `base_ref` are set after argv/session rehydration and before the classifier runs (`step-7a.sh:334-343`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Module-level `base_remote` / `base_ref` are set after argv/session rehydration and before the classifier runs (`step-7a.sh:334-343`).
- **Suggested revision**: Address the concern above.

### FINDING_7: `is_small_non_runtime_change` uses `"${base_remote}/${base_ref}"` at call time, not definition time (`step-7a.sh:81`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `is_small_non_runtime_change` uses `"${base_remote}/${base_ref}"` at call time, not definition time (`step-7a.sh:81`).
- **Suggested revision**: Address the concern above.

### FINDING_8: The generator receives `--base-remote` / `--base-ref` (`step-7a.sh:352-355`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - The generator receives `--base-remote` / `--base-ref` (`step-7a.sh:352-355`).
- **Suggested revision**: Address the concern above.

### FINDING_9: `BASE_ARGS` is unconditionally derived; non-fork now passes explicit `origin`/`main`, which is equivalent to the prior empty `BASE_ARGS` + `rebase-push.sh` defaults (`rebase-push.sh:88-89`, `rebase-checkpoint-probe.sh:44-50`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `BASE_ARGS` is unconditionally derived; non-fork now passes explicit `origin`/`main`, which is equivalent to the prior empty `BASE_ARGS` + `rebase-push.sh` defaults (`rebase-push.sh:88-89`, `rebase-checkpoint-probe.sh:44-50`).
- **Suggested revision**: Address the concern above.

### FINDING_10: `generate-code-flow-diagram.sh` adds defaults, regex validation, and quoted `BASE_TARGET` in the merge-base chain (`generate-code-flow-diagram.sh:28-45`, `65`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `generate-code-flow-diagram.sh` adds defaults, regex validation, and quoted `BASE_TARGET` in the merge-base chain (`generate-code-flow-diagram.sh:28-45`, `65`).
- **Suggested revision**: Address the concern above.

### FINDING_11: Harness cases `diagram-skip-forked` and `diagram-generate-forked` plus augmented `green` assertions cover both classifier and generator callsites.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Harness cases `diagram-skip-forked` and `diagram-generate-forked` plus augmented `green` assertions cover both classifier and generator callsites.
- **Suggested revision**: Address the concern above.

### FINDING_12: Rebase-macro `(C')` assertions were updated for the derived `BASE_ARGS` shape.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Rebase-macro `(C')` assertions were updated for the derived `BASE_ARGS` shape.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/test-step-7a.md:1-27` — The Cases list still documents 21 named scenarios while the harness defines 23 `new_case` invocations (e.g. `rebase-unexpected-rc`, `quiet-diagram-skip-contract` are implemented but not listed). This drift predates the two new fork cases; this branch renumbered entries without closing the gap. **Suggested fix:** Align the markdown inventory with every `new_case` in `test-step-7a.sh` in a follow-up docs-only pass.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/generate-code-flow-diagram.sh:43-44` — Invalid `--base-remote` / `--base-ref` values are rejected by regex (per plan), but no dedicated harness asserts `fail_usage` exit 2; coverage is indirect via step-7a stub argv logging only. The plan explicitly waived a direct generator argv harness, so this is informational only.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/scripts/test-generate-code-flow-diagram.sh:45-60
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Real generator prompt base selection is untested after adding --base-remote/--base-ref A typo leaving origin/main hardcoded at generate-code-flow-diagram.sh:58 passes test-step-7a stub assertions and the unchanged generator harness in make lint Extend test-generate-code-flow-diagram.sh with an upstream-only fixture and prompt-file assertion for --base-remote upstream --base-ref main
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/rebase-checkpoint-probe.sh:24-50` — `--base-remote` / `--base-ref` are forwarded to `rebase-push.sh` without local regex validation (rebase-push validates downstream). Pre-existing; not introduced by this branch. **Suggested fix:** Optional defense-in-depth: mirror `rebase-push.sh` validation at the probe boundary for SKILL.md call sites that pass argv directly.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/implement/scripts/generate-code-flow-diagram.sh:27-35` — `--model` remains unconstrained while new base-ref flags are validated. Pre-existing surface. **Suggested fix:** If hardening is desired later, restrict `--model` to an allowlist of known model slugs before passing to `launch-claude-subprocess.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-implement-rebase-macro.sh:99-108
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] (C') for step-7a.sh no longer asserts the forked_target conditional that gates base_remote=upstream; only coarse base_remote=/base_ref= presence plus derived BASE_ARGS near the wrapper. A maintainer could remove or invert the forked_target if-block while keeping literal assignments; structural lint stays green until diagram-skip or diagram-skip-forked fails. Re-add a grep for the forked_target conditional assignment pattern in step-7a.sh and/or add a non-fork calls.log assertion that rebase-checkpoint-probe.sh receives --base-remote origin --base-ref main.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] correctness: scripts/rebase-push.sh:144-158
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] skip-if-pushed hard-codes origin for ls-remote while 7a.r fork mode rebases against upstream via BASE_REMOTE. On a fork with branch pushed to upstream but not origin, skip-if-pushed may not short-circuit and may attempt an unnecessary rebase path. Pre-existing; consider aligning skip-if-pushed with BASE_REMOTE in a separate change if fork push semantics matter.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/generate-code-flow-diagram.sh:43-44
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No direct harness covers invalid --base-remote/--base-ref argv rejection. Manual or future caller typos are only caught at runtime via fail_usage; CI does not pin the exit-2 contract. Optional follow-up: small argv-validation cases in a dedicated test script (out of scope for #2844 per plan).
- **Suggested revision**: Address the concern above.

### FINDING_21: `ef3df272` — Align Step 7a fork base selection (feature)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `ef3df272` — Align Step 7a fork base selection (feature)
- **Suggested revision**: Address the concern above.

### FINDING_22: `6c3c24b2` — docs(linting) inventory refresh (#2873, adjacent)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `6c3c24b2` — docs(linting) inventory refresh (#2873, adjacent)
- **Suggested revision**: Address the concern above.

### FINDING_23: `fd3e3839` — chore(larch-logs) flush (ignored per review policy)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `fd3e3839` — chore(larch-logs) flush (ignored per review policy) Reviewed `ef3df272` against the implementation plan; pre-computed diff at the session path is dominated by `larch-logs/` noise. ### Requirement traceability | Plan item | Status | |-----------|--------| | `step-7a.sh`: module-level `base_remote`/`base_ref` after session-key block, before token-ledger mark | Done (`334:338:skills/implement/scripts/step-7a.sh`) | | Classifier uses `"${base_remote}/${base_ref}"` instead of hard-coded `origin/main` | Done (`81:81:skills/implement/scripts/step-7a.sh`) | | Generator call passes `--base-remote` / `--base-ref` | Done (`352:355:skills/implement/scripts/step-7a.sh`) | | `BASE_ARGS` unconditionally derived from module vars | Done (`405:409:skills/implement/scripts/step-7a.sh`) | | `generate-code-flow-diagram.sh`: argv flags, regex validation, `BASE_TARGET`, usage update | Done (`28:65:skills/implement/scripts/generate-code-flow-diagram.sh`) | | `test-step-7a.sh`: `make_forked_skip_repo`, `make_forked_generate_repo`, two new cases, augmented `green` | Done | | `test-implement-rebase-macro.sh` + `.md`: updated `(C')` assertions | Done | | `step-7a.md` / `generate-code-flow-diagram.md`: base-ref docs + session-env-only activation | Done | | `test-step-7a.md`: two new case entries | Done (cases 3–4) | | `docs/linting.md`: fork-mode coverage note | Done — branch already used qualitative prose (no numeric count) from #2873; fork note added | All nine planned files are touched in the feature commit. Scope exclusions (no new shared helper, no `test-generate-code-flow-diagram.sh`, unchanged `forked-target` rebase assertions) are honored.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-7a.md:5-27` — The sibling case list still omits harness cases `rebase-unexpected-rc` and `quiet-diagram-skip-contract` (present in `test-step-7a.sh` before this PR). This PR added the two planned fork entries but did not close that inventory gap (tracked separately as #2862 per prior review notes). **Suggested fix:** Update `test-step-7a.md` in a follow-up issue, not required for #2844 plan closure.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-7a.md:11-16` — Cases 5–8 still say sanitizer rejection “skips summary upsert,” but the harness asserts `tracking-issue-summary.sh` runs (pre-existing doc/harness mismatch, not introduced here). **Suggested fix:** Align prose with harness behavior under #2862.
- **Suggested revision**: Address the concern above.

