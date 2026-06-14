### OOS_1: correctness: python/step_7a.py:210-212
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Step 7a drops LARCH_RUN_ID when session-id is absent because of conditional-expression precedence. A run with session-env.sh containing LARCH_RUN_ID but no session-id computes an empty run_id, causing _run_log_flush() to skip run-log publication. Split the fallback into explicit statements and add a test for session-env-only LARCH_RUN_ID.
- **Suggested revision**: Address the concern above.


### OOS_2: **correctness** `python/step_7a.py:209-212` — **Important:** `run_id` only falls back to `session-env.sh` when `session-id` also exists, because the conditional expression binds to the whole `or` expression. A tmpdir with `session-env.sh` containing `LARCH_RUN_ID=run-99` but no `session-id` makes Step 7a pass an empty run ID, so log flushing, transcript capture, and run-log commit are skipped. **Suggested fix:** Parenthesize the `session-id` fallback and add a test for `LARCH_RUN_ID` without `session-id`.
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: - **correctness** `python/step_7a.py:209-212` — **Important:** `run_id` only falls back to `session-env.sh` when `session-id` also exists, because the conditional expression binds to the whole `or` expression. A tmpdir with `session-env.sh` containing `LARCH_RUN_ID=run-99` but no `session-id` makes Step 7a pass an empty run ID, so log flushing, transcript capture, and run-log commit are skipped. **Suggested fix:** Parenthesize the `session-id` fallback and add a test for `LARCH_RUN_ID` without `session-id`.
- **Suggested revision**: Address the concern above.


### OOS_3: **correctness** `python/pr_body.py:717-723` — **Important:** Final report issue counts count one NDJSON record per category, not the number of issue bullets in that record. An `execution-issues.ndjson` row with `category="Tool Failures"` and body `- a\n- b\n` renders `Exec issues: 1` instead of `2`. **Suggested fix:** Count bullet lines inside each row body by category, or reconstruct section text and reuse the markdown counting path.
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: - **correctness** `python/pr_body.py:717-723` — **Important:** Final report issue counts count one NDJSON record per category, not the number of issue bullets in that record. An `execution-issues.ndjson` row with `category="Tool Failures"` and body `- a\n- b\n` renders `Exec issues: 1` instead of `2`. **Suggested fix:** Count bullet lines inside each row body by category, or reconstruct section text and reuse the markdown counting path.
- **Suggested revision**: Address the concern above.


### OOS_4: **correctness** `python/execution_issues.py:173-181` — **Important:** `execution-issues append` appends to the end of the file when a category already exists, even if that category is not the last section. If `### Warnings` appears before `### Tool Failures`, appending another warning writes it under `Tool Failures`, and later flush/report logic misclassifies it. **Suggested fix:** Reuse `run_logs.append_execution_issue` or insert the entry before the next `### ` heading in the target section.
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: - **correctness** `python/execution_issues.py:173-181` — **Important:** `execution-issues append` appends to the end of the file when a category already exists, even if that category is not the last section. If `### Warnings` appears before `### Tool Failures`, appending another warning writes it under `Tool Failures`, and later flush/report logic misclassifies it. **Suggested fix:** Reuse `run_logs.append_execution_issue` or insert the entry before the next `### ` heading in the target section.
- **Suggested revision**: Address the concern above.


