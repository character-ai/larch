### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship_pr.py:331-338
- **Concern**: python/larch/report/run_log_flush.py:784-837. Scenario: Ship-layer benign handling keys on `REFRESH_SKIP_PRETERMINAL_OUTCOME`, but post-merge flush never emits it
- **Proposed resolution**: `finalize_postmerge_logs()` delegates to `flush_logs_post()`, which returns `recovery-failed`, `redaction-failed`, or `post-merge-refresh-failed`, not `preterminal-outcome`. Production stalls likely keep `STALL_STEP=postmerge-flush` with another reason while classifier evidence still contains stale `preterminal-outcome` text from pre-push refresh. The ship change alone would not clear stall metadata on the common path; only the classifier fix stops the reship. Keep the classifier short-circuit as the primary fix. In `ship_pr.py`, either document that the OK path is for the mocked/preterminal contract only, or add an explicit plan step if post-merge flush should surface `REFRESH_SKIP_PRETERMINAL_OUTCOME` before ship-layer OK handling can run in production.




### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_pr.py:331-338
- **Concern**: python/larch/implement/ship_pr.py benign-skip gate targets REFRESH_SKIP_PRETERMINAL_OUTCOME but postmerge flush never emits it. Scenario: run_postmerge_phase calls finalize_postmerge_logs which delegates to flush_logs_post; that path returns recovery-failed redaction-failed or post-merge-refresh-failed skips only. REFRESH_SKIP_PRETERMINAL_OUTCOME is emitted exclusively by flush_logs_pre at python/larch/report/run_log_flush.py:765-767. The planned gate never fires on the real postmerge stall path so STALL_TRACKING and postmerge-flush can still be written after a terminal merge.
- **Proposed resolution**: Gate benign handling on state_ctx.merge_result in config.POST_MERGE_MERGE_RESULTS together with the actual flush_logs_post skip reasons or on any skip.skipped after a terminal merge per NEVER 16. Add a regression test that mocks a real flush_logs_post reason such as REFRESH_SKIP_RECOVERY_FAILED not preterminal-outcome.




### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:277-283
- **Concern**: The post-merge classifier guard is broader than the benign skip condition. Scenario: `run_postmerge_phase()` intentionally keeps unexpected skips such as `commit-failed` on the stalled path, but the proposed classifier guard treats every `postmerge` stall with a terminal `MERGE_RESULT` as expected. A real post-merge flush failure after a successful merge would therefore become `operator-action` with no resume hint, hiding the failure and bypassing the intended stalled handling.
- **Proposed resolution**: Require evidence of the exact expected `preterminal-outcome` skip, or persist an explicit expected-skip marker and require it in the classifier guard. Keep `commit-failed` and other unexpected post-merge flush failures on normal classification.




### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_pr.py:331-338
- **Concern**: Ship benign-skip gate keys on preterminal-outcome but post-merge flush never emits it. Scenario: `run_postmerge_phase` calls `finalize_postmerge_logs` → `flush_logs_post`, which only skips with `manifest-recovery-failed`, `redaction-failed`, or `post-merge-refresh-failed`; it never calls `_preterminal_outcome_refresh_skip`. The planned `skip.reason == config.REFRESH_SKIP_PRETERMINAL_OUTCOME` branch is unreachable, so the driver still writes `Outcome.STALLED` / `STALL_STEP=postmerge-flush` on real post-merge skips and `normalize-outcome` keeps reporting `stalled` instead of `merged`
- **Proposed resolution**: Gate the healthy completion path on the skip reasons `flush_logs_post` actually returns after a terminal merge (mirror `git/merge.py` `_post_flush`: warn-and-continue for non-fatal skips; keep stalled only for `redaction-failed` and `manifest-recovery-failed`), or document and implement a post-merge path that can emit `preterminal-outcome` before adding that gate




### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:276-284
- **Concern**: Post-merge classifier short-circuit is broader than ship-layer edge cases. Scenario: The plan short-circuits every `phase == "postmerge"` stall with a terminal `MERGE_RESULT` to `operator-action` before `_classify_text()`, regardless of `STALL_STEP` or flush skip reason. That conflicts with the plan’s own edge case that unexpected failures such as `commit-failed` / `redaction-failed` must stay stalled, and it matches `merge.py` treating `redaction-failed` and `manifest-recovery-failed` as real errors
- **Proposed resolution**: Narrow the guard to `STALL_STEP=postmerge-flush` (and optionally require `preterminal-outcome` in evidence, or an allowlisted benign skip reason echoed in stall detail) so real post-merge refresh/redaction failures still classify through normal `_classify_text()` / stalled handling




### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:275-284
- **Concern**: The proposed short-circuit is broader than the expected preterminal-outcome case and conflicts with the plan's requirement to keep unexpected post-merge flush failures visible. Scenario: A merged run whose post-merge flush returns commit-failed still has PHASE=postmerge and a terminal MERGE_RESULT, so the classifier would return operator-action / none instead of reporting the real failure
- **Proposed resolution**: Require the expected postmerge-flush step and preterminal-outcome reason before short-circuiting; let other post-merge failures use normal classification




### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:224-284
- **Concern**: Classifier postmerge short-circuit is broader than ship-layer commit-failed guard. Scenario: Plan edge cases require unexpected post-merge flush skips such as commit-failed to stay stalled, but the proposed classify() guard fires on phase=postmerge plus any terminal MERGE_RESULT. After ship_pr.py still writes postmerge-flush for commit-failed, classification would become operator-action/none/postmerge-flush-expected and hide a real flush failure.
- **Proposed resolution**: Narrow the short-circuit to the same intentional skip the ship layer exempts: also require skip.reason, stall detail, or evidence to show REFRESH_SKIP_PRETERMINAL_OUTCOME, and exclude unexpected reasons such as commit-failed.




### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_pr.py:331-338
- **Concern**: Ship benign branch may not run on the reported reproduction path. Scenario: finalize_postmerge_logs delegates to flush_logs_post, which today never returns REFRESH_SKIP_PRETERMINAL_OUTCOME; only flush_logs_pre does. The bug report reaches postmerge-flush while classifier evidence contains preterminal-outcome from earlier flush output, so the ship-layer OK path may never execute unless postmerge flush is plumbed to surface that reason.
- **Proposed resolution**: Either wire post-merge flush to propagate preterminal-outcome when appropriate, or state explicitly that the classifier evidence gate is the production fix and keep the ship change defensive; add an integration test through flush_logs_post if ship-layer behavior is required.




### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:289-296
- **Concern**: The plan's postmerge short-circuit can still be overwritten by same-cause attempt handling. Scenario: A resumed run with the same confirmed-merge postmerge stall first classifies as operator-action, but the existing signature match then rewrites it to same-cause-repeat. This can re-enter terminal failure reporting and file the spurious bug the feature must prevent.
- **Proposed resolution**: Preserve operator-action across repeated classification. Exclude it from same-cause-repeat conversion or apply the confirmed-merge postmerge classification after attempt deduplication. Add the repeated-classification case to the planned regression test.




### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-Postmerge Route Auditor
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_pr.py:331-338 and python/larch/report/run_log_flush.py:784-837
- **Concern**: Ship benign-skip gate keys on REFRESH_SKIP_PRETERMINAL_OUTCOME but post-merge flush never emits it. Scenario: run_postmerge_phase stalls on any finalize_postmerge_logs skip (ship_pr.py:333-338); that helper delegates only to flush_logs_post (run_log_flush.py:840-847), which returns recovery/redaction/manifest failures and skipped=False on success, never reason=preterminal-outcome (run_log_flush.py:784-837). The acceptance outcome Outcome.OK for intentional post-merge skip is therefore unreachable on the live merge path unless tests mock the skip. Production reproduction still stalls with postmerge-flush for other reasons while the classifier over-matches preterminal-outcome in evidence (_classify.py:148-182).
- **Proposed resolution**: Either extend flush_logs_post to return REFRESH_SKIP_PRETERMINAL_OUTCOME when post-merge tmpdir finalization hits the same NEVER-16 preterminal policy, or narrow the ship change to classifier-only and drop the Outcome.OK acceptance for a skip reason the post-merge path does not produce.




### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-Postmerge Route Auditor
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:275-284
- **Concern**: Postmerge short-circuit ordering against existing short-circuit is unspecified. Scenario: classify() always applies short_circuit before _classify_text (275-283). _classify_short_circuit returns unrecoverable/none/no-stall when any_stall is false (216-221). A postmerge guard inserted before that frame would misclassify no-stall calls; one inserted only inside _classify_text would still lose to _ship_refresh_preterminal_stall() on evidence containing preterminal-outcome.
- **Proposed resolution**: Insert the postmerge+terminal-merge guard only when short_circuit is None and any_stall is true, as short_circuit or postmerge_guard or _classify_text(...). State this explicitly in the _classify.py plan step.




### FINDING_2: Expected-postmerge guard can hide real flush failures in mixed evidence
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The guard treats any evidence containing `preterminal-outcome` as benign without excluding current post-merge flush failure evidence. Persistent or stale evidence may contain `preterminal-outcome` alongside `redaction-failed`, `post-merge-refresh-failed`, `manifest-recovery-failed`, or `commit-failed`; the guard would then classify the stall as `operator-action` / `none` and suppress a real failure that should remain on normal classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit guard exclusions for post-merge flush failure tokens (at least redaction-failed, post-merge-refresh-failed, manifest-recovery-failed, and commit-failed) even when preterminal-outcome is present; add a negative fixture with both strings in evidence. The plan is narrowly scoped and addresses the round-1 broad-guard concerns well. Two correctness gaps remain in the proposed classifier work. **`_resume_hint_for` override.** The plan targets `operator-action` / `none` / `postmerge-flush-expected`, but `classify()` always recomputes the hint at line 284. `operator-action` is not in the early non-resumable set, `postmerge-flush` sanitizes to `unknown`, and `phase=postmerge` still falls through to `step8-shippr` — the same reship path the bug reports. **Evidence predicate too permissive.** Requiring `preterminal-outcome` in evidence matches the false-positive route, but stale preterminal text from an earlier pre-push refresh can coexist with a real `postmerge-flush` failure. Without explicit exclusions for post-merge flush failure tokens (`redaction-failed`, `manifest-recovery-failed`, etc.), the guard can hide real failures the plan’s edge cases say must stay on normal classification. Everything else in the plan (ordering after `short_circuit`, same-cause handling, token allowlist, tests, and skipping the unreachable `ship_pr.py` branch) looks aligned with the issue scope.
  - From Codex-Pragmatic: Make unexpected failure evidence take precedence over the benign guard, and add one mixed-evidence negative test containing both `preterminal-outcome` and an unexpected post-merge failure reason
  - From Cursor-Requirements: Require the guard to fail when evidence contains unexpected post-merge flush failure markers (at least redaction-failed, post-merge-refresh-failed, manifest-recovery-failed, commit-failed) even if stale preterminal-outcome is present; add a negative test with both preterminal-outcome and redaction-failed in evidence.

