### FINDING_1: **Important** `risk-integration` `scripts/test-ship-pr.sh:652`, `scripts/test-ship-pr.sh:777` — The ship-pr harness still asserts the removed post-create push and removed `pr_number` manifest update. With the new `scripts/ship-pr.sh:951-1008` flow, `git-push.sh` is no longer called after PR creation and `larch-log.sh manifest --field pr_number=...` is gone, so `make test-ship-pr-postmerge` will fail these assertions. Update the harness to expect the pre-PR `larch-log.sh commit`, no post-create push, no `pr_number` manifest write, and add coverage that a post-create `write-final-report.sh` failure records a warning without stalling.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/test-ship-pr.sh:652`, `scripts/test-ship-pr.sh:777` — The ship-pr harness still asserts the removed post-create push and removed `pr_number` manifest update. With the new `scripts/ship-pr.sh:951-1008` flow, `git-push.sh` is no longer called after PR creation and `larch-log.sh manifest --field pr_number=...` is gone, so `make test-ship-pr-postmerge` will fail these assertions. Update the harness to expect the pre-PR `larch-log.sh commit`, no post-create push, no `pr_number` manifest write, and add coverage that a post-create `write-final-report.sh` failure records a warning without stalling.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `code-quality` `skills/implement/SKILL.md:1680` — The updated prose still says the first deterministic `larch:final-summary` projection is written after `ship-pr.sh` persists `PR_NUMBER`/`PR_URL`, but the new script writes the committed placeholder summary before `create-pr.sh`. Reword this to distinguish the pre-PR committed placeholder from the post-create API-only tracking comment refresh.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `skills/implement/SKILL.md:1680` — The updated prose still says the first deterministic `larch:final-summary` projection is written after `ship-pr.sh` persists `PR_NUMBER`/`PR_URL`, but the new script writes the committed placeholder summary before `create-pr.sh`. Reword this to distinguish the pre-PR committed placeholder from the post-create API-only tracking comment refresh.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Nit** `risk-integration` `docs/run-logs.md:229` — The section still says `larch:final-summary` is written at Step 18, while the new behavior also writes it during PR creation with placeholder PR fields. Update the timing sentence so the canonical run-log docs match the new PR-create placeholder plus later live-comment refresh behavior.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Nit** `risk-integration` `docs/run-logs.md:229` — The section still says `larch:final-summary` is written at Step 18, while the new behavior also writes it during PR creation with placeholder PR fields. Update the timing sentence so the canonical run-log docs match the new PR-create placeholder plus later live-comment refresh behavior.
- **Suggested revision**: Address the concern above.

### FINDING_4: **Nit** `risk-integration` `scripts/ship-pr.md:70`, `scripts/ship-pr.md:95-98` — The ship-pr helper contract still documents the deleted `pr_number` manifest update and post-create log-refresh push. Bring this file in sync with `scripts/ship-pr.sh:951-1008`: pre-PR final-summary commit rides on `create-pr.sh`’s push, and the post-create refresh is API-only.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 4. **Nit** `risk-integration` `scripts/ship-pr.md:70`, `scripts/ship-pr.md:95-98` — The ship-pr helper contract still documents the deleted `pr_number` manifest update and post-create log-refresh push. Bring this file in sync with `scripts/ship-pr.sh:951-1008`: pre-PR final-summary commit rides on `create-pr.sh`’s push, and the post-create refresh is API-only. I could not run the harness in this read-only sandbox; `mktemp` failed with `Operation not permitted`.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:965-967 skills/implement/scripts/write-final-report.sh:51-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Possible RUN_ID mismatch between ship-pr flush_run_id and write-final-report RUN_ID resolution. If parent-issue RUN_ID and ship-pr-state RUN_ID diverge, final-summary could be written under a different implement run directory than the one committed. Pre-existing class of issue; unchanged ID-resolution split vs prior manifest+commit pairing.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/ship-pr.sh:964-977
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Empty flush_run_id skips pre-PR larch-log commit. Push #1 may omit committed final-summary.md though pre-create write succeeded; edge path. Warn on skip or document alongside LARCH_NO_LOGS_COMMIT.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: docs/run-logs.md:227-231
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] larch:final-summary section says Written at Step 18 only while Content notes ship-pr mid-run updates. Minor reader confusion about when the marker comment is first written. Clarify that marker upserts occur during ship-pr and again in Step 18 or similar.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/ship-pr.sh:951-1008
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated write-final-report invocation pattern. Future edits may miss updating one of two copies. Optional factor shared block if consistent with rest of ship-pr.sh style.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/implement/SKILL.md:1680
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 7a prose still says first larch:final-summary projection happens immediately after PR_NUMBER PR_URL persist. Contradicts new pre-create placeholder final-summary and pre-PR log commit; misleads orchestrators about when PR URL appears on disk versus tracking issue. Remove or rewrite the stale sentence so a single accurate timeline remains.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: docs/run-logs.md:229-231
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] 'Written at Step 18' unchanged while content describes earlier pr-create placeholder and canonical URL in comment. Doc readers assume no final-summary activity until Step 18 despite ship-pr doing pre-create writes. Update timing line to cover Step 8+ pr-create and Step 18 (or say marker may update multiple times).
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/test-ship-pr.sh:769-785
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness pr_create_flush still expects post-create larch-log manifest pr_number plus commit. run_pr_create_phase no longer calls larch-log manifest for pr_number; ship-pr test harness fails on grep for manifest + commit. Update stub expectations and test narrative to match pre-PR commit-only flow or remove manifest assertion.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/implement/SKILL.md:1665-1675
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Step_7a_prose_contradicts_new_ship-pr_flow Readers_may_believe_first_final-summary_only_after_PR_URL_persist_while_text_also_describes_pre-create_placeholder_write Reword_or_drop_the_immediately_after_persist_clause_to_match_pre-PR_and_post-PR_write-final-report_behavior
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/implement/SKILL.md:1680
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 7a prose still says the first larch:final-summary projection is written immediately after PR_NUMBER/PR_URL persist, but ship-pr now runs write-final-report before PR creation with placeholder PR fields. Operators or automation assume no final-summary tracking upsert until after PR_URL exists, or mis-order audits relative to the real two-phase GitHub comment updates. Reword to reflect two upserts (pre-PR placeholder vs post-persist live URL) or remove the incorrect first/immediately-after clause.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/implement/SKILL.md:1680
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Contradictory prose: claims first deterministic larch:final-summary after PR_NUMBER/PR_URL persist while also describing pre-create placeholder write. Readers mis-order API upserts vs state_set_many and mis-debug when tracking comment shows N/A before create. Rewrite clause so first upsert pre-create placeholder vs post-state_set live URL is explicit and ordered.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/implement/SKILL.md:1680
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Stale clause claims first larch:final-summary projection happens immediately after ship-pr persists PR_NUMBER/PR_URL while ship-pr.sh now invokes write-final-report.sh before create-pr and before state_set_many. Operators or tooling authors rely on Step 7a prose for ordering and mis-model when placeholder vs live PR URL exists or when the tracking-issue comment is first updated. Reword or delete the stale clause so the paragraph matches scripts/ship-pr.sh run_pr_create_phase (~951-1008): pre-create write with placeholder PR fields optional pre-PR larch-log commit then post-create best-effort API refresh.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/ship-pr.md:70,scripts/ship-pr.md:95-98
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Authoritative ship-pr.md still documents post-create manifest write log commit and push-before-CI-wait for final-summary. Operators and reviewers follow stale contract; debugging pr-create ordering against docs yields wrong conclusions. Rewrite invariant and Log Refresh sections to match scripts/ship-pr.sh pre-PR write-final-report optional pre-PR commit create-pr push and best-effort post write-final-report.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/ship-pr.sh:999-1008
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-create write-final-report.sh is best-effort only. PR exists but tracking-issue final-summary can stay PR N/A until later refresh if API fails; old path stalled here. Optional retry or stronger failure surfacing if stale comment is unacceptable; else document operator expectation.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/ship-pr.sh:999-1008
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Best_effort_post_write-final-report_can_leave_tracking_comment_at_PR_N/A If_pre-PR_API_succeeds_and_post-API_fails_PR_exists_but_larch_final-summary_can_still_show_N_A Document_edge_case_add_retry_or_stronger_failure_handling_if_canonical_URL_must_be_guaranteed
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/ship-pr.sh:999-1008 skills/implement/scripts/write-final-report.sh:68-79
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Post-create write-final-report.sh rewrites tracked larch-logs/.../final-summary.md on disk without a commit after the pre-PR commit froze PR:N/A. After a successful pr-create phase, git status shows a modified tracked final-summary.md; dirty-tree guards or clean-tree expectations can false-positive. Make the post pass API-only (new flag), or restore the committed file after upsert, or split helpers so the second pass does not mutate the log tree.
- **Suggested revision**: Address the concern above.

