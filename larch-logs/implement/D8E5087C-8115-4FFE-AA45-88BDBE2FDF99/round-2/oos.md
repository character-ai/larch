### FINDING_11: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **correctness** `scripts/design-log-publish.sh:293` — `plan-review` still uses `[[ -e "$DESIGN_TMPDIR/plan-review" ]]` without `|| -L`, so a dangling `plan-review` root symlink skips the entire subtree block (same as pre-change render-cache). **Suggested fix:** If parity is desired, apply the same outer guard to `plan-review`; otherwise leave as-is and track separately (plan explicitly scoped only render-cache).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **correctness** `scripts/design-log-publish.sh:372-380` — Residual TOCTOU between the tree-wide `find -type l` check and the subsequent `find -type f` enumeration: a symlink created in that gap is not listed by `-type f` and is skipped silently rather than failing publish (symmetric with `plan-review`). **Suggested fix:** Document explicitly or collapse to a single guarded walk; deeper hardening is already tracked as OOS per plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **correctness** `scripts/design-log-publish.sh:372` — `find ... 2>/dev/null || true` means permission errors on symlink discovery yield an empty `_sym_check` and allow publish to continue. **Suggested fix:** Match plan-review posture or fail closed on non-zero `find` exit when output is empty; same pattern exists at `309` for plan-review.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] risk-integration: scripts/design-log-publish.sh:293
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] plan-review/ outer guard lacks || -L dangling-root fallback that render-cache received. A dangling plan-review root symlink is silently skipped (no staging, no fail-closed), unlike render-cache after Change 1. Track separately if plan-review parity is desired; not required by this plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for empty render-cache/ success path documented in plan edge cases. A broken find -type l on empty directories could regress while happy path (nested files) still passes. Add an optional harness case: empty render-cache/ with plan.txt only expects PUBLISH_OK=true and no render-cache artifacts staged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] risk-integration: scripts/test-design-log-publish.sh:639-656
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] render-cache lacks a path-escape find stub test that plan-review has. Regression in render-cache case prefix guard would not be caught by symlink-focused cases. Add make_find_escape_stub coverage for render-cache if parity with plan-review is a goal.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/design-log-publish.sh:293` — `plan-review/` still uses `[[ -e "$DESIGN_TMPDIR/plan-review" ]]` without the `|| -L` fallback added for `render-cache/`, so a dangling `plan-review` symlink is silently skipped (no publish, no `PUBLISH_OK=false`) while other artifacts still publish. **Suggested fix:** Apply the same `[[ -e ... || -L ... ]]` outer guard to the plan-review block for parity with render-cache and the documented dangling-root posture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/design-log-publish.sh:398-403` — Residual TOCTOU remains between enumeration and `design_publish_stage_file`: a parent directory can be swapped for a symlink after `find -type f` but before staging, and a leaf file can be swapped in the microsecond after the per-file `[[ -L ]]` recheck (where `design_publish_stage_file` silently skips symlinks). This is documented and tracked (#2905, #2907); not introduced by this diff. **Suggested fix:** Follow-up hardening (e.g., `O_PATH`/`openat`-style staging or atomic directory snapshots) if same-UID TOCTOU becomes a requirement.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/design-log-publish.sh:380` — `render-cache/` has no filename allowlist (by design), so any regular file under the resolved tree is eligible for redacted publication; symlink hardening closes the prior bypass where `find -type f` skipped symlinked paths silently. **Suggested fix:** None required unless policy demands schema allowlisting for render-cache content.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] security: scripts/design-log-publish.sh:309-310,372-373
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] find -type l stderr is discarded; permission failures look like a clean symlink scan Same-UID attacker or FS edge case could block find under rc_root/pr_root while publish proceeds Propagate find failure or fail closed when find exits non-zero (shared follow-up for both subtrees)
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] correctness: scripts/design-log-publish.sh:293
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] plan-review lacks render-cache dangling-root outer guard A broken plan-review symlink never enters the hardened block and publish succeeds without staging plan-review Apply [[ -e ... || -L ... ]] to plan-review when parity is desired
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] architecture: scripts/design-log-publish.sh:398-403,214-215
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parent-dir TOCTOU and post-recheck symlink swap into design_publish_stage_file still allow silent skip Attacker with same-UID race timing could omit or redirect one staged file without failing publish Tracked OOS items; deeper hardening out of this PR scope
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] **Branch composition** — The full branch vs `main` also ships #2867 `launch-claude-review.sh` `--context-files` work, `validate-plan-commands` changes, version/CHANGELOG bumps, and implement run logs. None of that is required by the render-cache plan; it increases review surface but is not a plan omission for this feature.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Branch composition** — The full branch vs `main` also ships #2867 `launch-claude-review.sh` `--context-files` work, `validate-plan-commands` changes, version/CHANGELOG bumps, and implement run logs. None of that is required by the render-cache plan; it increases review surface but is not a plan omission for this feature.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_28: [OUT_OF_SCOPE] **Plan-review dangling root** — `plan-review` still uses `[[ -e "$DESIGN_TMPDIR/plan-review" ]]` only (no `\|\| -L`). The plan scoped the dangling-root guard to `render-cache` only and tracks broader plan-review gaps via #2905/#2907; no implementation gap for this PR.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Plan-review dangling root** — `plan-review` still uses `[[ -e "$DESIGN_TMPDIR/plan-review" ]]` only (no `\|\| -L`). The plan scoped the dangling-root guard to `render-cache` only and tracks broader plan-review gaps via #2905/#2907; no implementation gap for this PR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_29: [OUT_OF_SCOPE] **Path-escape harness (#2906)** — The plan deliberately did not add a render-cache path-escape test (only symlink Cases A–E). #2906 remains the right follow-up tracker.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. **Path-escape harness (#2906)** — The plan deliberately did not add a render-cache path-escape test (only symlink Cases A–E). #2906 remains the right follow-up tracker.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: [OUT_OF_SCOPE] code-quality: scripts/design-log-publish.sh:293
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] plan-review outer guard lacks || -L so dangling plan-review root symlinks bypass staging. Attacker or race leaves broken plan-review symlink; publish proceeds without plan-review artifacts and without PUBLISH_OK=false. Apply the same [[ -e ... || -L ... ]] pattern to plan-review when hardening is in scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] **Acceptance 6 (lint/tests)** — Not executed in this read-only review; presence of harness cases and Makefile wiring is consistent with the plan, but pass/fail was not verified here.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 4. **Acceptance 6 (lint/tests)** — Not executed in this read-only review; presence of harness cases and Makefile wiring is consistent with the plan, but pass/fail was not verified here.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/design-log-publish.sh:293-411
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicate hardened-subtree staging blocks differ only by allowlist. Next security fix applied to one block only reintroduces asymmetric posture. Extract a shared helper when a follow-up refactor is scheduled (tracked OOS items).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

