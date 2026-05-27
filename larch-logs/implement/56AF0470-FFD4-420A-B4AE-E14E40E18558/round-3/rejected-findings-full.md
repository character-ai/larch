### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: **Important** `code-quality` `scripts/implement-bootstrap.sh:583-809` — `phase_plan_materialize` is a ~225-line function with 14+ locals that mixes hard failures (`exit 2`), bail returns (`run-flags-persist-failed`, `dirty-tree`, `branch-create-failed`), best-effort tails (`append-tool-failure.sh`), and breadcrumb side effects. That makes the Step 0 contract hard to reason about and will compound when Phase 4 adds more phases in the same file. **Suggested fix:** Split into small helpers aligned with the plan’s numbered steps (e.g. `plan_materialize_copy_and_fetch`, `plan_materialize_branch`, `plan_materialize_logs`, `plan_materialize_summary`) and keep `phase_plan_materialize` as a thin sequencer; preserve the existing harness order assertions.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** `code-quality` `scripts/implement-bootstrap.sh:583-809` — `phase_plan_materialize` is a ~225-line function with 14+ locals that mixes hard failures (`exit 2`), bail returns (`run-flags-persist-failed`, `dirty-tree`, `branch-create-failed`), best-effort tails (`append-tool-failure.sh`), and breadcrumb side effects. That makes the Step 0 contract hard to reason about and will compound when Phase 4 adds more phases in the same file. **Suggested fix:** Split into small helpers aligned with the plan’s numbered steps (e.g. `plan_materialize_copy_and_fetch`, `plan_materialize_branch`, `plan_materialize_logs`, `plan_materialize_summary`) and keep `phase_plan_materialize` as a thin sequencer; preserve the existing harness order assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Phase 3 expanded the harness to ~136s on test-harnesses-7 while CI harness jobs use a 5-minute per-shard timeout Future case growth or slower runners could push shard 7 over the CI job limit and cause intermittent harness failures Monitor LARCH_HARNESS_TIMING for shard 7; reshard or split test-implement-bootstrap if wall time approaches the job timeout
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: correctness: scripts/implement-bootstrap.sh:248-280,658-661
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --resume-plan-tail re-runs create-branch --check and session-entry-gate before plan tail. Clean mid-run checkpoint does not imply entry-gate pass; recovery can fail at infra after operator cleanup. Document gate vs checkpoint semantics, or skip re-gating on resume when session-env.sh exists.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: architecture: scripts/implement-bootstrap.sh:690-697
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] git-current-branch empty/missing BRANCH reuses branch-create-failed bail reason. Operators cannot distinguish capture failure from create-branch failure in logs and routing tables. Introduce branch-capture-failed (or similar) with harness coverage.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: **Nit** `code-quality` `scripts/implement-bootstrap.sh:968-999` — The `plan` / `coder` / `all` arms each repeat the same `REPO_UNAVAILABLE` snapshot guard plus `should_run_phase_plan_materialize` / `phase_plan_materialize` block. **Suggested fix:** Extract a `maybe_run_plan_materialize_phase()` helper called from each arm to avoid drift when Phase 4 dispatch changes.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Nit** `code-quality` `scripts/implement-bootstrap.sh:968-999` — The `plan` / `coder` / `all` arms each repeat the same `REPO_UNAVAILABLE` snapshot guard plus `should_run_phase_plan_materialize` / `phase_plan_materialize` block. **Suggested fix:** Extract a `maybe_run_plan_materialize_phase()` helper called from each arm to avoid drift when Phase 4 dispatch changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_21: correctness: scripts/implement-bootstrap.sh:140-163
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan step 13 emits two fixed breadcrumbs when LARCH_QUIET_BREADCRUMBS is set; implementation gates text on RUN_PLAN_LOGGED and PLAN_SUMMARY_POSTED. Operators expecting canonical step0 breadcrumb lines may not see larch:plan posted or + plan logged after best-effort sub-step failures. Emit both strings whenever breadcrumbs are enabled per plan or update plan/docs for success-gated variants.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: **Nit** `code-quality` `scripts/implement-bootstrap.sh:664-701` — `issue_title` is read from `feature-description.txt` twice (`head -1` for slug derivation and again for goal text). **Suggested fix:** Read once after the resume gate and reuse the variable in both blocks.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Nit** `code-quality` `scripts/implement-bootstrap.sh:664-701` — `issue_title` is read from `feature-description.txt` twice (`head -1` for slug derivation and again for goal text). **Suggested fix:** Read once after the resume gate and reuse the variable in both blocks.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: **Latent** `code-quality` `scripts/implement-bootstrap.sh:676-679` — `create-branch.sh` exit **1** (branch exists) and exit **2** (git failure) both map to the same `IMPLEMENT_BAIL_REASON=branch-create-failed` without the former SKILL.md operator-facing distinction. **Suggested fix:** If diagnostics matter, branch on `create_rc` (or parse `create-branch` stderr) to emit differentiated warnings while keeping a single bail reason, or document in `implement-bootstrap.md` that operators must read `create-branch.stderr.log`.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 4. **Latent** `code-quality` `scripts/implement-bootstrap.sh:676-679` — `create-branch.sh` exit **1** (branch exists) and exit **2** (git failure) both map to the same `IMPLEMENT_BAIL_REASON=branch-create-failed` without the former SKILL.md operator-facing distinction. **Suggested fix:** If diagnostics matter, branch on `create_rc` (or parse `create-branch` stderr) to emit differentiated warnings while keeping a single bail reason, or document in `implement-bootstrap.md` that operators must read `create-branch.stderr.log`. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: scripts/implement-bootstrap.sh:954-957
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] --preflight-tmpdir only required when --issue-number set, not for all plan phases. Direct bootstrap --up-to-phase plan without --issue-number passes validation then fails at gh issue view. Require --preflight-tmpdir for plan/coder/all regardless of issue-number (with resume exception).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

