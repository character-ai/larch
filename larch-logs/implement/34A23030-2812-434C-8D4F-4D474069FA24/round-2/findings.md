### FINDING_1: **correctness** `skills/implement/SKILL.md:1727` — The Step 8+ inline blockquote repeats the same recovery pattern (“read `ship-pr-state.sh` … then re-invoke … with the same arguments as the `Invoke:` block below”) without that clarification, so it inherits the same ambiguity for post-timeout manual replay. **Suggested fix:** Mirror the tightened wording from NEVER #16 here (one sentence) so the blockquote and NEVER #16 stay aligned on where each class of `Invoke:` argument must be sourced.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:1727` — The Step 8+ inline blockquote repeats the same recovery pattern (“read `ship-pr-state.sh` … then re-invoke … with the same arguments as the `Invoke:` block below”) without that clarification, so it inherits the same ambiguity for post-timeout manual replay. **Suggested fix:** Mirror the tightened wording from NEVER #16 here (one sentence) so the blockquote and NEVER #16 stay aligned on where each class of `Invoke:` argument must be sourced.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `skills/implement/SKILL.md:64` — NEVER #16’s recovery clause tells the reader to read `ship-pr-state.sh` and then re-invoke `ship-pr.sh` with the same argv as the Step 8+ `Invoke:` block, but `scripts/ship-pr.sh` keeps `--auto-mode` and `--no-admin-fallback` only as per-invocation CLI globals (`AUTO_MODE`, `NO_ADMIN_FALLBACK` around lines 28–29 and 143–144 in `scripts/ship-pr.sh`), not as durable keys in the initial `ship-pr-state.sh` template (`write_initial_state` around lines 268–305 in `scripts/ship-pr.sh`). After a timeout or turn break, an operator can faithfully read `PHASE`/`MERGE`/`DRAFT`/`REPO`/`FORKED_TARGET`/`NO_LOGS_COMMIT` from state yet still guess wrong `--auto-mode` / `--no-admin-fallback` values, so the guidance slightly over-implies that `ship-pr-state.sh` alone is enough context for a bit-perfect replay of the `Invoke:` argv. **Suggested fix:** In NEVER #16’s “How to apply” recovery sentence, spell out that flags not represented in `ship-pr-state.sh` (at minimum `--auto-mode` and `--no-admin-fallback`, matching `scripts/ship-pr.sh`’s argv model) must be taken from the same sources the orchestrator used originally (e.g. `$IMPLEMENT_TMPDIR/session-env.sh` for `LARCH_AUTO_MODE` where applicable, plus the originating `/implement` flag memory), while `ship-pr-state.sh` remains the authority for persisted `PHASE` / resume semantics.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:64` — NEVER #16’s recovery clause tells the reader to read `ship-pr-state.sh` and then re-invoke `ship-pr.sh` with the same argv as the Step 8+ `Invoke:` block, but `scripts/ship-pr.sh` keeps `--auto-mode` and `--no-admin-fallback` only as per-invocation CLI globals (`AUTO_MODE`, `NO_ADMIN_FALLBACK` around lines 28–29 and 143–144 in `scripts/ship-pr.sh`), not as durable keys in the initial `ship-pr-state.sh` template (`write_initial_state` around lines 268–305 in `scripts/ship-pr.sh`). After a timeout or turn break, an operator can faithfully read `PHASE`/`MERGE`/`DRAFT`/`REPO`/`FORKED_TARGET`/`NO_LOGS_COMMIT` from state yet still guess wrong `--auto-mode` / `--no-admin-fallback` values, so the guidance slightly over-implies that `ship-pr-state.sh` alone is enough context for a bit-perfect replay of the `Invoke:` argv. **Suggested fix:** In NEVER #16’s “How to apply” recovery sentence, spell out that flags not represented in `ship-pr-state.sh` (at minimum `--auto-mode` and `--no-admin-fallback`, matching `scripts/ship-pr.sh`’s argv model) must be taken from the same sources the orchestrator used originally (e.g. `$IMPLEMENT_TMPDIR/session-env.sh` for `LARCH_AUTO_MODE` where applicable, plus the originating `/implement` flag memory), while `ship-pr-state.sh` remains the authority for persisted `PHASE` / resume semantics.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] **Exit 6 / Exit 0 edits vs `scripts/ship-pr.sh`:** Changing Exit 6 (and the generic Exit 0 branch) away from `--resume-phase $PHASE` toward “same `Invoke:` argv, no `--resume-phase`” is consistent with `scripts/ship-pr.sh:1673-1681`, where arbitrary `PHASE` strings such as `checks` or `pr-prep` would hit `unknown --resume-phase` and abort, while `ci-initial` / `ci-merge` are legal resume tokens but are not required for a plain main-loop continuation when state already holds `PHASE`.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **Exit 6 / Exit 0 edits vs `scripts/ship-pr.sh`:** Changing Exit 6 (and the generic Exit 0 branch) away from `--resume-phase $PHASE` toward “same `Invoke:` argv, no `--resume-phase`” is consistent with `scripts/ship-pr.sh:1673-1681`, where arbitrary `PHASE` strings such as `checks` or `pr-prep` would hit `unknown --resume-phase` and abort, while `ci-initial` / `ci-merge` are legal resume tokens but are not required for a plain main-loop continuation when state already holds `PHASE`.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] **Inline vs NEVER #16 token enumeration:** The blockquote at `skills/implement/SKILL.md:1727` defers to “same list as NEVER #16” instead of re-listing tokens, so there is no silent second enumeration to drift out of sync with NEVER #16.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **Inline vs NEVER #16 token enumeration:** The blockquote at `skills/implement/SKILL.md:1727` defers to “same list as NEVER #16” instead of re-listing tokens, so there is no silent second enumeration to drift out of sync with NEVER #16.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **`--resume-phase` token list vs `scripts/ship-pr.sh`:** The explicit list in NEVER #16 (`force-push-gate`, `bump`, `pr-create`, `ci-initial`, `ci-merge`, `evaluate-failure`, `postmerge`) matches the `case "$RESUME_PHASE"` arms in `scripts/ship-pr.sh:1674-1680` (with `force-push-gate|bump` correctly represented as two accepted spellings that both enter the bump resume arm).
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **`--resume-phase` token list vs `scripts/ship-pr.sh`:** The explicit list in NEVER #16 (`force-push-gate`, `bump`, `pr-create`, `ci-initial`, `ci-merge`, `evaluate-failure`, `postmerge`) matches the `case "$RESUME_PHASE"` arms in `scripts/ship-pr.sh:1674-1680` (with `force-push-gate|bump` correctly represented as two accepted spellings that both enter the bump resume arm).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] **`skills/implement/references/rebase-rebump-subprocedure.md`:** This file does not maintain a parallel `--resume-phase` token roster (grep shows no `--resume-phase` usage); NEVER #16 points to it for long-blocking / `ci-wait.sh` guidance, not for resume-token authority, so there is no cross-doc token mismatch to flag—only a pre-existing discoverability gap if someone expects resume tokens to be documented there.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **`skills/implement/references/rebase-rebump-subprocedure.md`:** This file does not maintain a parallel `--resume-phase` token roster (grep shows no `--resume-phase` usage); NEVER #16 points to it for long-blocking / `ci-wait.sh` guidance, not for resume-token authority, so there is no cross-doc token mismatch to flag—only a pre-existing discoverability gap if someone expects resume tokens to be documented there.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:9-24
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] NEVER rule numbering skips 10 (9 then 11). No impact on the ship-pr foreground feature; purely pre-existing doc structure. Leave as-is unless the project wants a editorial renumber pass unrelated to this PR.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:52-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] NEVER list skips number 10 (9 then 11). Pre-existing doc numbering quirk; not introduced by NEVER #16. Optional renumber or placeholder NEVER #10 in a separate editorial pass if desired.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:1755-1759
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implementation plan stated two insertions only in SKILL.md but diff also changes Exit 0 and Exit 6 ship-pr re-invocation guidance. Reviewers comparing branch to the written plan may treat the extra exit-matrix edits as undocumented scope unless the plan is updated. Update the implementation plan or PR summary to enumerate Exit 0/Exit 6 edits as intentional alignment with NEVER #16 and ship-pr.sh resume semantics.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/implement/SKILL.md:64-1759
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Generic NEVER #16 / Step 8+ timeout recovery says re-invoke ship-pr.sh without --resume-phase after reading state; Exit 5 flow is adjacent but structurally different. Clean Exit 5 leaves PHASE=bump with RESUME_PHASE/CALLER_KIND set; a model that applies the generic recovery instead of the Exit 5 matrix can re-enter bump and repeat Exit 5 without running the Rebase + Re-bump Sub-procedure. Clarify in NEVER #16 and the blockquote that the no- --resume-phase recipe targets mid-invocation timeout/kill, not post-Exit 5 recovery; Exit 5 remains governed solely by the exit-code row.
- **Suggested revision**: Address the concern above.

