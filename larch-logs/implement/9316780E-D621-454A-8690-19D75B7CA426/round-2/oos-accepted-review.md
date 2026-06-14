### OOS_52: correctness: python/stall_recovery.py:601-603
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] is-larch-dev-clone populate-sensitive-corpus normalize-file-failure-report-env lint are no-op stubs after design-failure-report.sh cutover to Python CLI In larch dev clone /design terminal failure tier_a_eligible never sees LARCH_DEV_CLONE=true; sensitive corpus stays empty; Tier A env normalization skipped Port bash subcommand bodies or delegate to stall-recovery-report.sh until ported; add pytest from retired harnesses
- **Suggested revision**: Address the concern above.


### OOS_53: correctness: python/pr_body.py:532-544
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] MERGE=true is treated as final merged outcome before any merge result exists A PR-create failure or pre-merge refresh during /implement --merge can publish a false merged final summary Use the old outcome precedence or the shared normalize-outcome helper
- **Suggested revision**: Address the concern above.


### OOS_54: risk-integration: python/pr_body.py:592-605
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Final-summary upsert is skipped for --comment-only, uses the wrong marker, and masks upsert failures The post-PR-create refresh in scripts/ship-pr.sh silently does not update the tracking issue with the live PR URL Keep --comment-only API-only but still upsert larch:final-summary and return non-zero on upsert failure
- **Suggested revision**: Address the concern above.


### OOS_55: correctness: python/pr_body.py:775-787
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Production diagram generation writes a static placeholder instead of launching the generator Step 7a reports success and uploads a plausible but false code-flow diagram for every real run Launch python/cli.py agent launch-claude-subprocess by default and keep the stub test-only
- **Suggested revision**: Address the concern above.


### OOS_56: correctness: python/stall_recovery.py:225-238
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] normalize-outcome marks most non-stalled runs completed and successful A bailed run with no PR can skip terminal failure reporting because IMPLEMENT_OUTCOME_SUCCEEDED=true is emitted Restore full outcome precedence and success allowlist
- **Suggested revision**: Address the concern above.


### OOS_57: security: python/stall_recovery.py:601-603
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Security-sensitive stall-recovery subcommands are success stubs design-failure-report proceeds after fake populate-sensitive-corpus success without the corpus or normalization outputs Port the subcommands fully or fail closed until implemented
- **Suggested revision**: Address the concern above.


### OOS_58: risk-integration: python/pr_body.py:590-599
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] --comment-only suppresses the tracking-issue upsert entirely scripts/ship-pr.sh calls --comment-only after PR creation to refresh the final-summary comment with the PR URL, but Python returns ok without posting Make comment_only skip only the committed run-log write and preserve the final-summary tracking marker
- **Suggested revision**: Address the concern above.


### OOS_59: risk-integration: python/pr_body.py:565-589
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Final reports always render with cost_unavailable=True Step 17 and Step 18 summaries emit Cost N/A even when token reports exist Read token data or pass token counters to render_run_summary, falling back only for absent or corrupt data
- **Suggested revision**: Address the concern above.


### OOS_60: risk-integration: python/pr_body.py:590
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Non-comment-only final reports no longer write larch-logs/implement/<run-id>/final-summary.md run-log completeness verification can fail or ship incomplete final-summary batches Restore the run-dir final-summary.md write for normal calls and keep the comment-only carve-out
- **Suggested revision**: Address the concern above.


### OOS_61: risk-integration: python/pr_body.py:775-787
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Production diagram generation writes a static placeholder instead of launching Claude Step 7a can post a generic misleading diagram for runtime changes Call agent launch-claude-subprocess when the test launcher env var is unset and write the real prompt/logs
- **Suggested revision**: Address the concern above.


### OOS_62: correctness: python/step_7a.py:73-145
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Python _run_log_flush omits most pre-ship run-log batch writes from step-7a.sh run_log_flush Pre-ship commit missing codex-impl-transcript parent-issue pre-review token-report timing-report vendor-failure batches Port full run_log_flush sequence from step-7a.sh into _run_log_flush or shared run_logs helpers; extend test_step_7a.py
- **Suggested revision**: Address the concern above.


### OOS_63: correctness: python/stall_recovery.py:601-603
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Several live stall-recovery subcommands are successful no-ops Design and implement recovery can skip Tier A detection, sensitive corpus creation, filing normalization, and lint checks while returning success Port the real subcommand behavior or keep callers on the bash helper until parity tests exist
- **Suggested revision**: Address the concern above.


### OOS_64: correctness: python/stall_recovery.py:225-237
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] normalize-outcome ignores --in-memory-stall-tracking Step 18a.5 can treat an active in-memory stall as a successful run and file escalation-success reports Parse the in-memory flag and require all stall-tracking layers to be false before success
- **Suggested revision**: Address the concern above.


### OOS_65: **correctness** `python/stall_recovery.py:225-238` — `normalize_outcome` collapses almost every non-stalled run to `completed` with `IMPLEMENT_OUTCOME_SUCCEEDED=true`. A bailout with no PR, or `BAIL_NEEDS_USER_INPUT=true`, is now reported as successful, so Step 18a.5 can clear a failed recovery path incorrectly. **Suggested fix:** Port the old decision tree for fork dry-run, design-only, merged, PR-created, draft, bailed, bailed-needs-user-input, and all stall layers including `--in-memory-stall-tracking`.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **correctness** `python/stall_recovery.py:225-238` — `normalize_outcome` collapses almost every non-stalled run to `completed` with `IMPLEMENT_OUTCOME_SUCCEEDED=true`. A bailout with no PR, or `BAIL_NEEDS_USER_INPUT=true`, is now reported as successful, so Step 18a.5 can clear a failed recovery path incorrectly. **Suggested fix:** Port the old decision tree for fork dry-run, design-only, merged, PR-created, draft, bailed, bailed-needs-user-input, and all stall layers including `--in-memory-stall-tracking`.
- **Suggested revision**: Address the concern above.


### OOS_66: **security** `python/file_oos.py:221` — Strict filed-URL evidence accepts any `https://.../issues/<n>` host, so an accepted OOS block can satisfy the disposition gate with `- **Filed URL**: https://example.test/issues/1` without a GitHub issue. This bypasses the required public OOS filing check in `python/file_oos.py:476-480`. **Suggested fix:** Build the strict filed-URL regex from `_github_issue_url_pattern()` and only count `github.com` or configured `GH_HOST` issue URLs.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **security** `python/file_oos.py:221` — Strict filed-URL evidence accepts any `https://.../issues/<n>` host, so an accepted OOS block can satisfy the disposition gate with `- **Filed URL**: https://example.test/issues/1` without a GitHub issue. This bypasses the required public OOS filing check in `python/file_oos.py:476-480`. **Suggested fix:** Build the strict filed-URL regex from `_github_issue_url_pattern()` and only count `github.com` or configured `GH_HOST` issue URLs.
- **Suggested revision**: Address the concern above.


### OOS_67: correctness: python/pr_body.py:588
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] write_final_report hardcodes cost_unavailable=True Final summary always shows Cost N/A despite valid token ledger data Mirror write-final-report.sh token/cost resolution via report_tokens_cost before render_run_summary
- **Suggested revision**: Address the concern above.


### OOS_68: correctness: python/pr_body.py:585
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] write_final_report hardcodes warnings=0 Final summary under-reports warnings when execution-issues.md has Warnings bullets Count warning bullets from execution-issues.md like bash before render_run_summary
- **Suggested revision**: Address the concern above.


### OOS_69: correctness: python/stall_recovery.py:461-471
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] validate_tier_b_public_file swallows OSError on corpus read and still validates public file Unreadable sensitive corpus lets Tier B public comment pass without token rejection Fail closed: emit PUBLIC_FILE_VALID=false on corpus/content read errors
- **Suggested revision**: Address the concern above.


