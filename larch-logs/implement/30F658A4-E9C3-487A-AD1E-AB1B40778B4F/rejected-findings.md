### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/implement/scripts/step-7a.sh:79-101,334-338
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] is_small_non_runtime_change reads base_remote/base_ref assigned much later under set -u A refactor that calls the classifier before base_remote/base_ref are set aborts with unbound variable instead of degrading to diagram generation Initialize base_remote/base_ref in the top-level defaults block or pass them as function arguments at the sole call site
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: `generate-code-flow-diagram.sh` adds defaults, regex validation, and quoted `BASE_TARGET` in the merge-base chain (`generate-code-flow-diagram.sh:28-45`, `65`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `generate-code-flow-diagram.sh` adds defaults, regex validation, and quoted `BASE_TARGET` in the merge-base chain (`generate-code-flow-diagram.sh:28-45`, `65`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: Harness cases `diagram-skip-forked` and `diagram-generate-forked` plus augmented `green` assertions cover both classifier and generator callsites.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Harness cases `diagram-skip-forked` and `diagram-generate-forked` plus augmented `green` assertions cover both classifier and generator callsites.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: Rebase-macro `(C')` assertions were updated for the derived `BASE_ARGS` shape.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Rebase-macro `(C')` assertions were updated for the derived `BASE_ARGS` shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: risk-integration: scripts/test-implement-rebase-macro.sh:99-108
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] (C') for step-7a.sh no longer asserts the forked_target conditional that gates base_remote=upstream; only coarse base_remote=/base_ref= presence plus derived BASE_ARGS near the wrapper. A maintainer could remove or invert the forked_target if-block while keeping literal assignments; structural lint stays green until diagram-skip or diagram-skip-forked fails. Re-add a grep for the forked_target conditional assignment pattern in step-7a.sh and/or add a non-fork calls.log assertion that rebase-checkpoint-probe.sh receives --base-remote origin --base-ref main.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/implement/scripts/test-step-7a.sh:338-390
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate fork fixture helpers mirror make_skip_repo with only commit payload differing Future fixture fixes must be applied in three places or fork cases drift Factor a shared make_forked_repo helper parameterized by changed files
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: `ef3df272` — Align Step 7a fork base selection (feature)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `ef3df272` — Align Step 7a fork base selection (feature)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: `6c3c24b2` — docs(linting) inventory refresh (#2873, adjacent)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `6c3c24b2` — docs(linting) inventory refresh (#2873, adjacent)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: `fd3e3839` — chore(larch-logs) flush (ignored per review policy)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `fd3e3839` — chore(larch-logs) flush (ignored per review policy) Reviewed `ef3df272` against the implementation plan; pre-computed diff at the session path is dominated by `larch-logs/` noise. ### Requirement traceability | Plan item | Status | |-----------|--------| | `step-7a.sh`: module-level `base_remote`/`base_ref` after session-key block, before token-ledger mark | Done (`334:338:skills/implement/scripts/step-7a.sh`) | | Classifier uses `"${base_remote}/${base_ref}"` instead of hard-coded `origin/main` | Done (`81:81:skills/implement/scripts/step-7a.sh`) | | Generator call passes `--base-remote` / `--base-ref` | Done (`352:355:skills/implement/scripts/step-7a.sh`) | | `BASE_ARGS` unconditionally derived from module vars | Done (`405:409:skills/implement/scripts/step-7a.sh`) | | `generate-code-flow-diagram.sh`: argv flags, regex validation, `BASE_TARGET`, usage update | Done (`28:65:skills/implement/scripts/generate-code-flow-diagram.sh`) | | `test-step-7a.sh`: `make_forked_skip_repo`, `make_forked_generate_repo`, two new cases, augmented `green` | Done | | `test-implement-rebase-macro.sh` + `.md`: updated `(C')` assertions | Done | | `step-7a.md` / `generate-code-flow-diagram.md`: base-ref docs + session-env-only activation | Done | | `test-step-7a.md`: two new case entries | Done (cases 3–4) | | `docs/linting.md`: fork-mode coverage note | Done — branch already used qualitative prose (no numeric count) from #2873; fork note added | All nine planned files are touched in the feature commit. Scope exclusions (no new shared helper, no `test-generate-code-flow-diagram.sh`, unchanged `forked-target` rebase assertions) are honored.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/test-implement-rebase-macro.sh:2029-2035
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] (C') step-7a assertion weakened to file-scope base_remote=/base_ref= grep A spurious late base_remote= line could satisfy the harness without correct fork policy placement Keep BASE_ARGS proximity check and add a bounded line-range check near session-key resolution
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: Module-level `base_remote` / `base_ref` are set after argv/session rehydration and before the classifier runs (`step-7a.sh:334-343`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Module-level `base_remote` / `base_ref` are set after argv/session rehydration and before the classifier runs (`step-7a.sh:334-343`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: `is_small_non_runtime_change` uses `"${base_remote}/${base_ref}"` at call time, not definition time (`step-7a.sh:81`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `is_small_non_runtime_change` uses `"${base_remote}/${base_ref}"` at call time, not definition time (`step-7a.sh:81`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: The generator receives `--base-remote` / `--base-ref` (`step-7a.sh:352-355`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - The generator receives `--base-remote` / `--base-ref` (`step-7a.sh:352-355`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: `BASE_ARGS` is unconditionally derived; non-fork now passes explicit `origin`/`main`, which is equivalent to the prior empty `BASE_ARGS` + `rebase-push.sh` defaults (`rebase-push.sh:88-89`, `rebase-checkpoint-probe.sh:44-50`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `BASE_ARGS` is unconditionally derived; non-fork now passes explicit `origin`/`main`, which is equivalent to the prior empty `BASE_ARGS` + `rebase-push.sh` defaults (`rebase-push.sh:88-89`, `rebase-checkpoint-probe.sh:44-50`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

