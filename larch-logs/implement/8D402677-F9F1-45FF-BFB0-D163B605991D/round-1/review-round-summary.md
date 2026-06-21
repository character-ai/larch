# Review Round 1

- Mode: `diff`
- 10 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Manifest `pr_number` not stamped; audit tolerance blind to historical and new committed snapshots
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-merge-log-path-output.txt, dyn-manifest-reconcile-output.txt
- **Severity**: important
- **Concern**: Audit/verify bail-skip tolerance requires `manifest.json` `pr_number`, but `_reconcile_manifest_for_terminal_report` and `flush_logs_pre` never persist it on the committed post-ensure path (`flush_logs_post` is tmpdir-only per NEVER #16). Historical misrecorded dirs (e.g. `2396BA29`) and new post-ensure snapshots therefore lack `pr_number`, so `_stale_bail_heading_with_pr_evidence` / `_final_summary_bail_signal_without_pr_evidence` stay inactive and `audit-runs` / `verify-completeness` still bail-skip those dirs despite partial/bailed artifacts with PR linkage elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-log-path-output.txt: During post-ensure `_reconcile_manifest_for_terminal_report`, stamp `pr_number` into the committed manifest when PR evidence exists; and/or let audit/verify tolerance treat the scan’s known PR (`audit_runs`’s `pr` arg) as evidence when the heading is a stale bail and the manifest omits `pr_number`.
  - From dyn-manifest-reconcile-output.txt: During post-ensure reconcile (or the following `update_manifest` pass), persist `PR_NUMBER` from `ship-pr-state.sh` into manifest `pr_number` so committed snapshots carry the evidence field tolerance and `verify-completeness` already expect.


### FINDING_4: Missing straight-merge committed-snapshot integration test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required straight-merge regression coverage is absent: ship tests stub strict post-ensure flush/push (autouse fixture) or only assert stage ordering. A regression where post-ensure flush writes `bailed`, leaves `manifest.status` partial, or fails to preserve `step8=true` would still pass. The core acceptance criterion—that a merge-eligible run publishes `pr-created` / `in-progress` / `step8=true` into the squash-merge tree—has no end-to-end guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a dedicated test that disables post-ensure mocks, exercises real `flush_logs_pre(strict_final_report=True)` with `PR_NUMBER` state after `ensure_pr`, stubs git commit/push only, and asserts `final-summary.md` outcome and `manifest.json` status/steps_ran on disk.
  - From codex-specialist-testing-output.txt: Add the planned straight-merge test using the real flush/final-report path and assert final-summary pr-created, manifest.status in-progress, and steps_ran.step8=true.


### FINDING_9: PR-evidence branch ignores `PHASE=stalled` across state files
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The new PR-evidence branch does not treat terminal `PHASE=stalled` as an OR across state files. When `ship-pr-state.sh` has `PHASE=ci-initial`, `PR_NUMBER=12`, `MERGE=true`, empty `MERGE_RESULT`, and `finalize-state.sh` has `PHASE=stalled`, the outcome becomes `pr-created` instead of `stalled`.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_10: `summary-final.md` write failures escape strict post-ensure recovery mapping
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: A disk-full or permission error writing `$IMPLEMENT_TMPDIR/summary-final.md` raises `OSError` and can become an internal ship error instead of a `manifest-recovery-failed` stall. Strict flush should map this to `REFRESH_SKIP_RECOVERY_FAILED`.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_12: Stale `EXIT_CODE` / `BAIL_REASON` survive stall recovery and break post-ensure healthy snapshot gate
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Post-ensure strict flush uses `normalized_outcome_values` but prior `EXIT_CODE` / `BAIL_REASON` / `IMPLEMENT_BAIL_REASON` survive in `ship-pr-state.sh` when resuming `open-pr` after `clear_stall`. After a stalled `--merge` run, stall recovery clears `STALL_TRACKING` only; `EXIT_CODE=4` and `BAIL_REASON=ci-fix-exhausted` remain. Re-entering ship on `open-pr` runs post-ensure strict flush, `_is_healthy_pre_terminal_pr_snapshot` returns false, and committed `final-summary` / `manifest` still record `bailed` despite `PR_NUMBER` being set.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_13: `audit-runs` vs `verify-completeness` use divergent bail-skip tolerance predicates
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-audit-tolerance-output.txt
- **Severity**: important
- **Concern**: PR evidence disables terminal bail-skip too broadly in `verify-completeness` (any terminal heading when `manifest_pr_number` is set) while `audit-runs` suppresses bail-skip only for `bailed` / `bailed-needs-user-input` headings with matching manifest PR evidence. A genuine post-PR stalled run (`stalled` heading, `pr_number` set, empty `steps_ran`, no `run-statistics.md`) can pass required-file scanning in audit but fail verify, or surface different missing-file sets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Suppress the skip only for stale `bailed` or `bailed-needs-user-input` headings with PR evidence; keep the existing terminal skip for non-bailed terminal outcomes.
  - From dyn-audit-tolerance-output.txt: extract one shared helper for “stale terminal heading with manifest PR evidence” and use it in both `audit_runs._stale_bail_heading_with_pr_evidence` and `run_logs._final_summary_bail_signal_without_pr_evidence`, with an explicit policy for which terminal outcomes qualify (at minimum, keep `bailed` / `bailed-needs-user-input` aligned across both tools).


### FINDING_14: Post-ensure stall paths overwrite merge-loop counters with defaults
- **Reviewer(s)**: dyn-merge-log-path-output.txt
- **Severity**: important
- **Concern**: Post-ensure flush/push stall paths call `_write_terminal_state` without `iteration`, `rebase_count`, `fix_attempts`, or `transient_retries`. `_write_ship_state` defaults those to `0`, overwriting counters just written at `ship.py:1434-1440`. This is inconsistent with other stall sites and can lose CI/rebase progress on `open-pr` resume or misclassify the stall for Step 18a recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-log-path-output.txt: Pass through `resume.iteration`, `resume.rebase_count`, `resume.fix_attempts`, and `resume.transient_retries` (or the local variables derived from them immediately below) on every post-ensure `_write_terminal_state` call.


### FINDING_15: Terminal stall after post-ensure flush leaves success-classified committed artifacts
- **Reviewer(s)**: dyn-manifest-reconcile-output.txt
- **Severity**: important
- **Concern**: Post-ensure `flush_logs_pre(..., strict_final_report=True)` is the last blocking committed snapshot on the straight-merge path. It runs while CI/merge outcome is still unknown and `_reconcile_manifest_for_terminal_report` stamps `status=in-progress` for `pr-created`. Terminal stall exits such as `ci-fix-exhausted` return from the merge loop without another blocking flush, so the squash-merged tree can keep `pr-created` / `in-progress` even though the run ultimately stalled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-reconcile-output.txt: On terminal stall paths after PR creation, either run a blocking pre-squash flush while stall signals are present (so reconcile writes non-success outcome/status), or defer the first committed post-PR snapshot until a point where terminal failure signals cannot be overwritten without another publish.


### FINDING_16: Reconcile runs before token/timing/transcript staging; `step7a` can be wrong in committed manifest
- **Reviewer(s)**: dyn-manifest-reconcile-output.txt
- **Severity**: important
- **Concern**: `_reconcile_manifest_for_terminal_report` runs immediately after `final-summary.md` is written but before `_render_ledger_reports`, `_render_token_timing_batches`, and `capture_session_transcript` in `_stage_pre_commit`. If those artifacts are absent at reconcile time, reconcile stamps `steps_ran.step7a=false`. The post-`_stage_pre_commit` reload in `flush_logs_pre` only merges the `step9a1` delta and never re-reconciles `step7a`, so the committed manifest can record `step7a=false` while those files are present in the same flush commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-reconcile-output.txt: Move reconcile to after token/timing/transcript staging, or add a second reconcile pass (or reload `step7a` from on-disk evidence) before `update_manifest` / commit.


### FINDING_17: `_manifest_pr_evidence_matches` accepts non-digit `pr_number` without comparing to `--pr`
- **Reviewer(s)**: dyn-audit-tolerance-output.txt
- **Severity**: important
- **Concern**: `_manifest_pr_evidence_matches` treats any non-empty, non-`"0"` `pr_number` that is not all digits as valid PR evidence (`return True` on line 514) without comparing it to `--pr`. Corrupt or placeholder values such as `"N/A"`, `"pending"`, or `"4897x"` therefore enable stale-bail tolerance for every audited PR, breaking “matching `--pr` when comparable” and “corrupt manifests stay strict” constraints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-tolerance-output.txt: return `False` for non-digit `pr_number` values (same strictness as missing/`"0"`), or require `raw.isdigit()` and `int(raw) == pr` whenever `pr > 0`; only treat PR evidence as present when the manifest value is a positive integer that matches the audited PR.


