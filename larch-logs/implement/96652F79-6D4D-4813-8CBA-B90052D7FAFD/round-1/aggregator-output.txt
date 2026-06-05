### FINDING_1: Plugin manifest still advertises retired implement workflow path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-workflow-retirement-output.txt
- **Severity**: important
- **Concern**: `.claude-plugin/plugin.json` still describes `/implement` as using a conventional hard workflow path, contradicting the removed `WORKFLOW_PATH` contract and consumer-facing plan acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reword description: implement has no workflow tier; fixed 7200s timeout; preserve design SIMPLE/HARD and Step 5 hard-panel wording
  - From cursor-specialist-correctness-output.txt: Reword description: design keeps SIMPLE/--hard; implement is issue-anchored with 7200s Step 2 timeout and no workflow tier/path.
  - From cursor-specialist-testing-output.txt: Reword description per plan; add test-implement-structure.sh negative grep for stale hard-workflow-path wording in plugin.json
  - From cursor-specialist-edge-cases-output.txt: Reword description per plan: design SIMPLE/--hard unchanged; implement as positional issue-N with 7200s timeout and no workflow tier
  - From cursor-specialist-plan-fidelity-output.txt: Reword description per plan: design SIMPLE/--hard only; implement positional issue-N, 7200s timeout, no workflow tier; keep Step 5 unified hard panel wording without workflow-path implication.
  - From dyn-workflow-retirement-output.txt: Update `.claude-plugin/plugin.json` `description` to describe `/implement` as positional `<issue-N>` with fixed 7200s Step 2 timeout and no workflow tier/path dimension, while keeping `/design` SIMPLE/HARD tier wording design-only; add a structure-harness grep pin if desired.

### FINDING_2: Missing final-report regression for stale workflow flags
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-workflow-retirement-output.txt, dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-write-final-report.sh` lacks the planned test proving stale `WORKFLOW_PATH` / `POST_PLAN_WORKFLOW_PATH` values cannot leak `Path` or SIMPLE/HARD workflow text into final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add test_write_final_report_ignores_legacy_workflow_flags asserting no Path line and no SIMPLE/HARD leak
  - From cursor-specialist-correctness-output.txt: Add test_write_final_report_ignores_legacy_workflow_flags per plan: fixture with stale keys, assert no Path line and no SIMPLE/HARD leak.
  - From cursor-specialist-testing-output.txt: Add dedicated test with stale run-flags and session-env keys; assert_not_contains for Path bullet and SIMPLE/HARD path values
  - From cursor-specialist-edge-cases-output.txt: Add dedicated test with legacy flags asserting no Path bullet and no SIMPLE/HARD leak
  - From cursor-specialist-plan-fidelity-output.txt: Add test_write_final_report_ignores_legacy_workflow_flags with both stale keys and assert no - **Path**: line or SIMPLE/HARD in output.
  - From dyn-workflow-retirement-output.txt: Add the dedicated harness case using `assert_not_contains` for `- **Path**:` and for `SIMPLE`/`HARD` path values in the composed summary.
  - From dyn-bash-contracts-output.txt: Add a dedicated case with both stale `WORKFLOW_PATH=HARD` and `POST_PLAN_WORKFLOW_PATH=HARD` in session-env, run `write-final-report.sh`, and assert the summary body contains no Path bullet and no workflow tier strings.

### FINDING_3: SKILL.md timing fences lack required implement-skill invariant
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-workflow-retirement-output.txt, dyn-timing-contamination-output.txt, dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-timing-rehydration.sh` does not enforce the planned `LARCH_TIMING_SKILL=implement` adjacency invariant for `skills/implement/SKILL.md` fences that call timing scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend awk invariant B with has_timing_skill_implement check per plan
  - From cursor-specialist-testing-output.txt: Extend awk invariant B with has_timing_skill_implement check in same fence as timing-ledger/timing-report calls
  - From cursor-specialist-security-output.txt: Extend invariant B (or add invariant F) to require `LARCH_TIMING_SKILL=implement` in the same fence as any `timing-ledger.sh` / `timing-report.sh` invocation, mirroring the polluted-env regression in `scripts/test-timing-report.sh`.
  - From cursor-specialist-edge-cases-output.txt: Extend awk invariant B to require LARCH_TIMING_SKILL=implement in fences with timing calls
  - From cursor-specialist-plan-fidelity-output.txt: Extend awk to require LARCH_TIMING_SKILL=implement in same fence as timing-ledger/timing-report calls.
  - From dyn-workflow-retirement-output.txt: Add the planned awk branch (fail when `has_timing` is true and `has_timing_skill_implement` is false, with Step 0 carve-out as needed) and wire a failing fixture if a fence regresses.
  - From dyn-timing-contamination-output.txt: Implement the planned `has_timing_skill_implement` awk invariant in `scripts/test-implement-timing-rehydration.sh`, and add a separate pin that `scripts/step-telemetry-mark.sh` must prefix its timing mark with `LARCH_TIMING_SKILL=implement`.
  - From dyn-bash-contracts-output.txt: In the existing awk block, set `has_timing_skill_implement=1` when a fence line matches `LARCH_TIMING_SKILL=implement`, and fail any fence with `has_timing` set but `has_timing_skill_implement` unset (keeping the Step 0 carve-out).

### FINDING_4: Missing render-run-summary omission test for workflow path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-run-summary.sh` lacks the planned implement case omitting `--workflow-path`, so conditional omission of the `Path` bullet is not directly regression-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add harness case without --workflow-path asserting no - **Path**: line
  - From cursor-specialist-correctness-output.txt: Add implement render case without --workflow-path; assert output lacks - **Path**: line.
  - From cursor-specialist-testing-output.txt: Add implement render case without --workflow-path asserting output lacks - **Path**:
  - From cursor-specialist-edge-cases-output.txt: Add implement invocation without --workflow-path asserting no Path line
  - From cursor-specialist-plan-fidelity-output.txt: Add case without --workflow-path asserting output has no - **Path**: bullet.
  - From dyn-bash-contracts-output.txt: Add a harness case that calls `render-run-summary.sh` with `--skill implement` and no `--workflow-path`, then assert the output lacks `- **Path**:`.

### FINDING_5: compose-pr-summary contract prose is broken
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/compose-pr-summary.md` contains a malformed sentence fragment after the workflow-path wording removal, making the PR summary placeholder contract unclear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace with single coherent sentence about /implement PR prep placeholder replacement
  - From cursor-specialist-correctness-output.txt: Replace lines 4-5 with one grammatical sentence describing /implement PR prep placeholder replacement.
  - From cursor-specialist-plan-fidelity-output.txt: Merge into one complete sentence per planned caller-neutral wording.

### FINDING_6: report token renderer duplicates skill-specific table construction
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/report_tokens_render.py` duplicates column and row construction across multiple skill-specific branches, making future escaping or column changes easy to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared column/row builders keyed by skill

### FINDING_7: report token issue section label still says workflow
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/report_tokens_issue.py` still uses an aggregate title label that says “by workflow,” which misdocuments implement report labels after workflow removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use skill-aware labels or neutral keys with _section_label only

### FINDING_8: compose-pr-summary test comment still references SIMPLE path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-compose-pr-summary.sh` has stale header prose referencing SIMPLE-path wording after the contract was neutralized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update header comment to caller-neutral /implement PR prep wording.
  - From cursor-specialist-plan-fidelity-output.txt: Update comment to caller-neutral /implement PR prep wording.

### FINDING_9: implement timing rehydration doc has stale cardinality
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-timing-rehydration.md` documents stale 41/3 counts while the harness expects 42/4, and it does not document the new skill-pin invariant consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update md to 42 source guards and 4 awk fallbacks; document LARCH_TIMING_SKILL=implement adjacency once enforced
  - From cursor-specialist-plan-fidelity-output.txt: Sync doc counts with scripts/test-implement-timing-rehydration.sh.

### FINDING_10: Step 5 review comment still references retired hard workflow contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/run-step5-review.sh` has stale comment prose tying Step 5 round caps to the retired unified hard workflow contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Reword comment to fixed base cap 5 and review-and-fix.sh panel selection wording
  - From cursor-specialist-plan-fidelity-output.txt: Reword to fixed base cap 5 and panel selection in review-and-fix.sh per plan.

### FINDING_11: step-telemetry-mark can record implement marks under polluted design skill
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-workflow-retirement-output.txt, dyn-timing-contamination-output.txt, dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: `scripts/step-telemetry-mark.sh` calls `timing-ledger.sh mark` without forcing `LARCH_TIMING_SKILL=implement`, so Step 5/16/17/18 entry marks routed through the helper can be written as `design` after a prior `/design` session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Prefix every implement-owned `timing-ledger.sh mark` with `LARCH_TIMING_SKILL=implement` (including `step-telemetry-mark.sh`, which backs four SKILL.md step-ENTRY sites), or teach `step-telemetry-mark.sh` to force-export `LARCH_TIMING_SKILL=implement` before marking.
  - From cursor-specialist-edge-cases-output.txt: Pin LARCH_TIMING_SKILL=implement on all implement timing-ledger.sh mark invocations especially centralize in step-telemetry-mark.sh
  - From dyn-workflow-retirement-output.txt: Export `LARCH_TIMING_SKILL=implement` in `step-telemetry-mark.sh` before the timing mark (and add a polluted-env case to `scripts/test-step-telemetry-mark.sh`).
  - From dyn-timing-contamination-output.txt: Prefix the timing mark in `step-telemetry-mark.sh` with `LARCH_TIMING_SKILL=implement` (mirroring bootstrap/finalize/Step 2/7a/18), and add a structure-harness pin that fails if the helper omits it.
  - From dyn-bash-contracts-output.txt: Set `LARCH_TIMING_SKILL=implement` inside `step-telemetry-mark.sh` before the timing mark (or export it once after reading session-env), so every caller inherits the pin automatically.

### FINDING_12: commit wrapper timing marks lack implement-skill pin
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-workflow-retirement-output.txt, dyn-timing-contamination-output.txt, dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: `commit-implementation.sh` and `commit-review-fixes.sh` still call `timing-ledger.sh mark` without `LARCH_TIMING_SKILL=implement`, so Step 4/7 marks can be misattributed to `design`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Prefix every implement-owned `timing-ledger.sh mark` with `LARCH_TIMING_SKILL=implement` (including `step-telemetry-mark.sh`, which backs four SKILL.md step-ENTRY sites), or teach `step-telemetry-mark.sh` to force-export `LARCH_TIMING_SKILL=implement` before marking.
  - From cursor-specialist-edge-cases-output.txt: Pin LARCH_TIMING_SKILL=implement on all implement timing-ledger.sh mark invocations especially centralize in step-telemetry-mark.sh
  - From cursor-specialist-plan-fidelity-output.txt: Prefix marks with LARCH_TIMING_SKILL=implement or narrow acceptance grep if intentionally excluded.
  - From dyn-workflow-retirement-output.txt: Prefix both marks with `LARCH_TIMING_SKILL=implement`, extend `scripts/test-implement-structure.sh` (or a polluted-env harness) to assert the pin, and document the contract in the commit-wrapper `.md` files.
  - From dyn-timing-contamination-output.txt: Add `LARCH_TIMING_SKILL=implement` on each of these mark invocations and extend `scripts/test-implement-structure.sh` with negative pins (similar to the new `--workflow-path` / `--workflow` guards) so unpinned production mark sites fail lint.
  - From dyn-bash-contracts-output.txt: Prefix both calls with `LARCH_TIMING_SKILL=implement`, matching the other implement-owned mark sites, and extend `scripts/test-implement-structure.sh` to require that prefix instead of only checking for the bare mark string.

### FINDING_13: relevant-checks captured timing marks lack implement-skill pin
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-timing-contamination-output.txt, dyn-bash-contracts-output.txt
- **Severity**: latent
- **Concern**: `scripts/run-relevant-checks-captured.sh` records Step 3/6 timing marks without forcing `LARCH_TIMING_SKILL=implement`, allowing check-pass marks to be misattributed under polluted ambient env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Prefix every implement-owned `timing-ledger.sh mark` with `LARCH_TIMING_SKILL=implement` (including `step-telemetry-mark.sh`, which backs four SKILL.md step-ENTRY sites), or teach `step-telemetry-mark.sh` to force-export `LARCH_TIMING_SKILL=implement` before marking.
  - From dyn-timing-contamination-output.txt: Add `LARCH_TIMING_SKILL=implement` on each of these mark invocations and extend `scripts/test-implement-structure.sh` with negative pins (similar to the new `--workflow-path` / `--workflow` guards) so unpinned production mark sites fail lint.
  - From dyn-bash-contracts-output.txt: Change both lines to `LARCH_TIMING_SKILL=implement IMPLEMENT_TMPDIR=... "$SCRIPT_DIR/timing-ledger.sh" mark ...`.

### FINDING_14: timing-ledger test doc still mentions workflow rows
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-timing-ledger.md` still describes workflow-row coverage after workflow-path behavior was removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Drop workflow from coverage sentence per plan.

### FINDING_15: timing-report test doc still references workflow latest row
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-timing-report.md` misdocuments coverage by still referencing workflow latest-row behavior instead of the new design-only fallback and implement omission coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update to match new test-timing-report.sh coverage.

### FINDING_16: report token render API crashes on empty implement records
- **Reviewer(s)**: dyn-tokens-reporting-output.txt
- **Severity**: latent
- **Concern**: `python/report_tokens_render.py` calls median/mean/max on an empty implement records list if `render("implement", ())` is invoked directly, regressing the previous header-only empty-output behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tokens-reporting-output.txt: Guard the implement branch with the same empty-input behavior as design (emit the `## Aggregate cost` header/table scaffold with zero data rows), or add a single non-empty precondition at the top of `render()` for both skills.

### FINDING_17: degraded-tools docs disagree with implement empty-default contract
- **Reviewer(s)**: dyn-degraded-gate-output.txt
- **Severity**: latent
- **Concern**: Shared degraded-tools documentation says to rehydrate presence keys with `--default "false"`, while `/implement` requires empty defaults so missing keys trigger `PRESENCE_INPUT_EMPTY`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-degraded-gate-output.txt: Align the canonical contract with the implement fence—document and exemplify `--default ""` for presence keys (and empty default for binary-found) in `skills/shared/external-reviewers.md` and `scripts/degraded-tools-gate.md`, or change the implement fence to match the shared `"false"` default only if you explicitly want to drop `PRESENCE_INPUT_EMPTY` detection for missing keys.

### FINDING_18: design degraded-tools gate treats missing binary-found as false
- **Reviewer(s)**: dyn-degraded-gate-output.txt
- **Severity**: latent
- **Concern**: `/design` passes unset `*_BINARY_FOUND` values as explicit `false`, causing partial/corrupt env state to classify tools as binary-missing instead of unknown/present-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-degraded-gate-output.txt: In the design gate fence, omit `--codex-binary-found` / `--cursor-binary-found` when the sourced vars are unset (or pass `unknown`), keep `:-false` only for presence keys, and add a harness case mirroring implement’s partial-env behavior.

### FINDING_19: implement bootstrap resume presence defaults diverge from degraded gate
- **Reviewer(s)**: dyn-degraded-gate-output.txt
- **Severity**: latent
- **Concern**: `scripts/implement-bootstrap.sh` resume-tail logic rehydrates presence with `--default "false"` while the degraded-tools gate uses `--default ""`, creating split semantics for missing legacy or partial tmpdir keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-degraded-gate-output.txt: Use the same rehydration contract in both places (prefer empty defaults at bootstrap resume when keys are absent, or have bootstrap fail closed before routing when presence keys are missing), so coder selection and the degraded gate agree on outage vs rehydration failure.

### OOS_1: Step 2 timing mark may be duplicated for external implementers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `step2-implement.sh` may record Step 2 timing twice via both SKILL.md fence and dispatcher; reviewer marked this pre-existing and out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Consider deduplicating Step 2 timing marks in a follow-up if duration accuracy matters.

### OOS_2: design fallback timing tests omit explicit DESIGN_TMPDIR
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-timing-report.sh` design fallback tests rely on ledger-dirname co-location instead of setting explicit `DESIGN_TMPDIR`; reviewer marked this out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional: set DESIGN_TMPDIR on V2/V1 design cases per plan for production-faithful coverage

### OOS_3: Fixed 7200s implement timeout increases former SIMPLE runtime ceiling
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Universal `LAUNCHER_TIMEOUT=7200` doubles the previous SIMPLE-path timeout, increasing worst-case resource exposure; reviewer marked this out of scope/operational.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Accept as intentional unification, or document operator-facing runtime expectations; no security patch required unless a separate budget gate is desired.

### OOS_4: Branch contains unrelated commits outside workflow-removal scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-workflow-retirement-output.txt, dyn-bash-contracts-output.txt
- **Severity**: latent
- **Concern**: Review scope includes branch commits unrelated to the workflow-removal plan, such as degraded-tools and design/run-log work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Evaluate workflow removal against commit 7c00d697d; treat other commits separately.

### OOS_5: Plugin manifest stale wording marked outside bash-contract scope
- **Reviewer(s)**: dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: Same behavioral risk as FINDING_1, but this reviewer explicitly marked `.claude-plugin/plugin.json` outside the bash-contract review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contracts-output.txt: the plan listed this file for update

### OOS_6: timing rehydration doc cardinality drift marked non-runtime
- **Reviewer(s)**: dyn-workflow-retirement-output.txt
- **Severity**: nit
- **Concern**: Same doc-count drift as FINDING_9, but this reviewer marked it out of scope as harness doc drift rather than a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-retirement-output.txt: `scripts/test-implement-timing-rehydration.md:15` still documents “41 source guards, 3 awk fallbacks” while `scripts/test-implement-timing-rehydration.sh:143-149` expects 42/4 after the SKILL.md edits on this branch — harness doc drift, not a runtime defect.

### OOS_7: render-run-summary omission coverage marked out of scope by one reviewer
- **Reviewer(s)**: dyn-workflow-retirement-output.txt
- **Severity**: latent
- **Concern**: Same coverage gap as FINDING_4, but this reviewer explicitly surfaced it as out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-retirement-output.txt: `scripts/test-render-run-summary.sh` has no case that omits `--workflow-path` and asserts no `- **Path**:` line, though `scripts/render-run-summary.sh:253-255` implements that behavior and the plan called for such coverage.

### OOS_8: vendor task rows can inherit polluted timing skill
- **Reviewer(s)**: dyn-timing-contamination-output.txt
- **Severity**: latent
- **Concern**: `record-vendor-task` call sites can inherit `LARCH_TIMING_SKILL=design`, but reviewer marked this as pre-existing and not driving the workflow-removal report path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-contamination-output.txt: This predates the branch, vendor rows do not drive `workflow_path`, and the branch’s report-side gate (`scripts/timing-report.sh:102-108`) plus pinned report callers prevent SIMPLE/HARD fallback leakage on the implement report path.

### OOS_9: report-tokens CLI lacks design post_issue forwarding assertion
- **Reviewer(s)**: dyn-tokens-reporting-output.txt
- **Severity**: nit
- **Concern**: `python/test_report_tokens_cli.py` does not assert `--skill design` forwards `skill="design"` to `post_issue`; reviewer marked this a coverage gap rather than a demonstrated runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tokens-reporting-output.txt: the updated tests only cover the implement path.

### OOS_10: report-tokens scan happy path has thin workflow assertion
- **Reviewer(s)**: dyn-tokens-reporting-output.txt
- **Severity**: nit
- **Concern**: Normal implement scan tests do not assert `record.workflow == ""`; reviewer marked behavior correct but happy-path coverage thin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tokens-reporting-output.txt: Normal implement scans (for example `test_scan_blank_url`) do not assert `record.workflow == ""`

### OOS_11: duplicate Step 0 preflight telemetry calls predate branch
- **Reviewer(s)**: dyn-degraded-gate-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.sh` calls both token and timing ledgers for the same Step 0 preflight mark; reviewer marked this pre-existing telemetry noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-degraded-gate-output.txt: the extra call predates this branch and is telemetry noise rather than a degraded-gate regression.
