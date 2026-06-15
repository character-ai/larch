### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: correctness: skills/design/scripts/design-publish.sh:280-307
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] panel-skipped is refused but never produced by any Step 3 or publish writer Operators cannot hit the documented panel-skipped refusal path; zero-review cases depend only on rounds_completed=0 Emit panel-skipped from the appropriate cap/skip path or remove it from refusal surfaces
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_21: risk-integration: skills/design/references/approval-gates.md:187-208
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] panel-failed acknowledgment is bypassed by --skip-approve panel-failed with launched reviewers can auto-approve and publish [DESIGNED] without explicit acknowledgment Make panel-failed override --skip-approve or require separate acknowledgment before Step 5; add a regression test
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (0 YES)

### FINDING_25: **correctness** `scripts/implement-preflight.sh:198-218` — `refuse_unreviewed_plan` only refuses explicit `panel-init-failed` / `panel-skipped` and a present `rounds_completed:` that is `0` or non-numeric. A plan bearing `review_status: complete` with no `rounds_completed:` line passes preflight, including under `--emergency` (emergency bypasses do not cover this case). That allows `/implement` on metadata that claims success without documenting how many review rounds ran, which is weaker than the acceptance goal of blocking zero-review outcomes. **Suggested fix:** When `review_status:` is present, require a numeric `rounds_completed:` ≥ 1 (refuse missing `rounds_completed:` as malformed provenance), or refuse any `review_status` other than an allowlisted set unless both fields are present and consistent.
- **Reviewer**: dyn-review-provenance-output.txt
- **Concern**: - **correctness** `scripts/implement-preflight.sh:198-218` — `refuse_unreviewed_plan` only refuses explicit `panel-init-failed` / `panel-skipped` and a present `rounds_completed:` that is `0` or non-numeric. A plan bearing `review_status: complete` with no `rounds_completed:` line passes preflight, including under `--emergency` (emergency bypasses do not cover this case). That allows `/implement` on metadata that claims success without documenting how many review rounds ran, which is weaker than the acceptance goal of blocking zero-review outcomes. **Suggested fix:** When `review_status:` is present, require a numeric `rounds_completed:` ≥ 1 (refuse missing `rounds_completed:` as malformed provenance), or refuse any `review_status` other than an allowlisted set unless both fields are present and consistent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** dismissed (0 YES)

### FINDING_26: **correctness** `skills/design/scripts/design-publish.sh:285-307` and `scripts/implement-preflight.sh:201-205` — `panel-skipped` is wired into publish refusal and preflight refusal, but no Step 3 loop branch, cap-short-circuit, or `review_status_for_plan` mapping ever emits `panel-skipped` (only `panel-init-failed`, `panel-failed`, `cap-hit`, etc.). The acceptance criteria and issue text expect this token for skip-without-review scenarios; today it is dead surface area, so the intended cap-skip / zero-launch path cannot be distinguished from `cap-hit` or `panel-init-failed` in published metadata. **Suggested fix:** Define and implement the producer (for example cap hit with zero launched rounds → `panel-skipped`, or drop `panel-skipped` from refusal surfaces if `panel-init-failed` / `cap-hit` are meant to cover all cases).
- **Reviewer**: dyn-review-provenance-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-publish.sh:285-307` and `scripts/implement-preflight.sh:201-205` — `panel-skipped` is wired into publish refusal and preflight refusal, but no Step 3 loop branch, cap-short-circuit, or `review_status_for_plan` mapping ever emits `panel-skipped` (only `panel-init-failed`, `panel-failed`, `cap-hit`, etc.). The acceptance criteria and issue text expect this token for skip-without-review scenarios; today it is dead surface area, so the intended cap-skip / zero-launch path cannot be distinguished from `cap-hit` or `panel-init-failed` in published metadata. **Suggested fix:** Define and implement the producer (for example cap hit with zero launched rounds → `panel-skipped`, or drop `panel-skipped` from refusal surfaces if `panel-init-failed` / `cap-hit` are meant to cover all cases).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_3: correctness: skills/design/references/approval-gates.md:187
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] --skip-approve can bypass the required panel-failed acknowledgment. /design --skip-approve with STEP3_REVIEW_LOOP_STATUS=panel-failed proceeds to Step 5 without explicit operator acknowledgment. Disable skip-approve auto-approval for panel-failed and require the degraded-review acknowledgment prompt.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** dismissed (0 YES)

### FINDING_35: **risk-integration** `scripts/design-log-publish.sh:324` — `design_publish_cleanup_same_run_worktrees || true` discards cleanup failure. When the stale worktree is outside the allowlisted temp paths (`unsafe=true`), publish still fails with the same “branch already checked out” message and no structured signal that cleanup was attempted and refused. Bug 5 asked for cleanup-and-retry; this is only a best-effort pre-check, not a recoverable retry path. **Suggested fix:** Propagate cleanup outcome (`CLEANUP_REMOVED`, `CLEANUP_UNSAFE`) via `emit_kv`, and when cleanup removed a worktree, re-run the checkout probe once before emitting the terminal publish-failure envelope.
- **Reviewer**: dyn-shell-flow-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:324` — `design_publish_cleanup_same_run_worktrees || true` discards cleanup failure. When the stale worktree is outside the allowlisted temp paths (`unsafe=true`), publish still fails with the same “branch already checked out” message and no structured signal that cleanup was attempted and refused. Bug 5 asked for cleanup-and-retry; this is only a best-effort pre-check, not a recoverable retry path. **Suggested fix:** Propagate cleanup outcome (`CLEANUP_REMOVED`, `CLEANUP_UNSAFE`) via `emit_kv`, and when cleanup removed a worktree, re-run the checkout probe once before emitting the terminal publish-failure envelope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** dismissed (0 YES)

### FINDING_36: **correctness** `skills/design/scripts/design-step3-review.sh:273-387` — Prelaunch failure paths (`monitor-mode-unavailable`, `scope-anchor-missing`) allocate `_plan_review_stdout_file` via `mktemp` and then `exit 1` before the main `trap _step3_review_cleanup` is installed. Those temp captures are not removed on those exits. **Suggested fix:** `rm -f "$_plan_review_stdout_file"` immediately before each prelaunch `exit 1`, or install a small early EXIT trap that always deletes the capture file.
- **Reviewer**: dyn-shell-flow-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-step3-review.sh:273-387` — Prelaunch failure paths (`monitor-mode-unavailable`, `scope-anchor-missing`) allocate `_plan_review_stdout_file` via `mktemp` and then `exit 1` before the main `trap _step3_review_cleanup` is installed. Those temp captures are not removed on those exits. **Suggested fix:** `rm -f "$_plan_review_stdout_file"` immediately before each prelaunch `exit 1`, or install a small early EXIT trap that always deletes the capture file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_37

**Rejected subtype:** dismissed (0 YES)

### FINDING_37: **risk-integration** `scripts/implement-preflight.sh:339-341` — `refuse_unreviewed_plan` runs only when `review_status` is `panel-init-failed` / `panel-skipped`, or when `rounds_completed:` is present and `0`/malformed. Legacy `[DESIGNED]` plans with no `review_status:` or `rounds_completed:` trailers still pass Preflight, so pre-#4336 unreviewed designs can reach `/implement`. **Suggested fix:** If the acceptance contract requires blocking all unreviewed plans, refuse when both metadata lines are absent on plans written after a cutoff, or refuse `review_status: unknown` / missing metadata unless `--emergency` with an explicit bypass log entry.
- **Reviewer**: dyn-shell-flow-output.txt
- **Concern**: - **risk-integration** `scripts/implement-preflight.sh:339-341` — `refuse_unreviewed_plan` runs only when `review_status` is `panel-init-failed` / `panel-skipped`, or when `rounds_completed:` is present and `0`/malformed. Legacy `[DESIGNED]` plans with no `review_status:` or `rounds_completed:` trailers still pass Preflight, so pre-#4336 unreviewed designs can reach `/implement`. **Suggested fix:** If the acceptance contract requires blocking all unreviewed plans, refuse when both metadata lines are absent on plans written after a cutoff, or refuse `review_status: unknown` / missing metadata unless `--emergency` with an explicit bypass log entry.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_40

**Rejected subtype:** dismissed (0 YES)

### FINDING_40: **code-quality** `scripts/implement-preflight.sh:198-218` — `refuse_unreviewed_plan` only refuses explicit bad tokens (`panel-init-failed`, `panel-skipped`, malformed/`rounds_completed=0`). Plans with **no** `review_status:` / `rounds_completed:` lines pass preflight, so legacy `[DESIGNED]` issues from before this branch (the exact Bug 3/4 failure mode) remain implementable. `scripts/test-implement-preflight.sh` exercises refusal cases but never asserts that a metadata-free plan is blocked. **Suggested fix:** Treat absent review provenance on `[DESIGNED]` plans as a hard refusal (or require both keys with `rounds_completed >= 1`), and add a harness case where `PLAN_CASE=present` writes only `Plan text\n` and expects exit 2.
- **Reviewer**: dyn-regression-surface-output.txt
- **Concern**: - **code-quality** `scripts/implement-preflight.sh:198-218` — `refuse_unreviewed_plan` only refuses explicit bad tokens (`panel-init-failed`, `panel-skipped`, malformed/`rounds_completed=0`). Plans with **no** `review_status:` / `rounds_completed:` lines pass preflight, so legacy `[DESIGNED]` issues from before this branch (the exact Bug 3/4 failure mode) remain implementable. `scripts/test-implement-preflight.sh` exercises refusal cases but never asserts that a metadata-free plan is blocked. **Suggested fix:** Treat absent review provenance on `[DESIGNED]` plans as a hard refusal (or require both keys with `rounds_completed >= 1`), and add a harness case where `PLAN_CASE=present` writes only `Plan text\n` and expects exit 2.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_43

**Rejected subtype:** dismissed (0 YES)

### FINDING_43: **code-quality** `skills/design/scripts/design-publish.sh:241-277` — `write_review_metadata_plan` always prepends fresh `review_status:` / `rounds_completed:` before the trailer block and never removes prior copies. A Step 5c retry after partial publish can emit duplicate provenance lines; `plan_review_meta_value` in `scripts/implement-preflight.sh:185-195` then binds the **last** line, which may not match what validators or operators read. **Suggested fix:** Strip existing `review_status:` / `rounds_completed:` lines from the contiguous metadata block (or full plan) before insertion; add a publish harness retry case that asserts single provenance pair.
- **Reviewer**: dyn-regression-surface-output.txt
- **Concern**: - **code-quality** `skills/design/scripts/design-publish.sh:241-277` — `write_review_metadata_plan` always prepends fresh `review_status:` / `rounds_completed:` before the trailer block and never removes prior copies. A Step 5c retry after partial publish can emit duplicate provenance lines; `plan_review_meta_value` in `scripts/implement-preflight.sh:185-195` then binds the **last** line, which may not match what validators or operators read. **Suggested fix:** Strip existing `review_status:` / `rounds_completed:` lines from the contiguous metadata block (or full plan) before insertion; add a publish harness retry case that asserts single provenance pair.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: correctness: skills/design/scripts/design-publish.sh:224-238
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [latent] Publish metadata maps zero-findings-degraded-panel to unknown instead of a real review outcome. Legacy single-mode env with LOOP_STATUS=zero-findings-degraded-panel and REVIEW_ROUND_COUNT=1 writes review_status: unknown. Map zero-findings-degraded-panel to an explicit provenance value or normalize it to complete with degraded metadata.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: risk-integration: scripts/design-log-publish.sh:1226-1237
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Stale worktree cleanup is best-effort and ignored via || true Stale RUN_ID worktrees outside tmp design-log-publish.* paths still block publish without auto-recovery Retry publish after prune on unsafe paths; do not swallow required cleanup failures
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

