# Review Round 2

- Mode: `diff`
- 16 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Terminal state conflict preserved; report gate does not verify outcome match
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: When `design-stage-terminal-state.sh` finds an existing terminal state with a different outcome/site/trigger, it exits 0 with `STAGED=false` and `PRESERVED=true` while callers ignore `STAGED=false`. The report gate in `design-failure-report.sh` validates terminal state existence but never checks that `FAILURE_OUTCOME` (or `SUMMARY_OUTCOME`) matches the `--outcome` passed from teardown. A later failure can file a report labeled with one outcome while classifying stale state from an earlier failure (for example `failed-clarify` staged first, then `failed-publish-tail` teardown files using stale classification).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-design-reporting-output.txt: In `design-failure-report.sh`, require `FAILURE_OUTCOME` (and optional `SUMMARY_OUTCOME`) to match `--outcome` before `classify`/`compose-report`, or fail closed to fallback print. Have staging callers (`design-publish.sh`, `review-design-step3-loop.sh`, `design-step5c.sh`) parse `STAGED=false` and treat preservation as a staging failure.


### FINDING_10: test-render-final-summary.sh teardown-gate tests are mostly source greps
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Teardown-gate behavioral tests from plan are mostly source greps. Helper KVs could leak into `final-summary.md` or run in pre phase without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: test-design-publish.sh verifies terminal-state staging by grepping source only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Terminal-state staging is verified by grepping script source, not by driving failures. `design-publish` could stop writing `design-failure-terminal-state.env` on plan-write/publish failure undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: No test covers failed-publish-tail hard-exit staging and summary routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test covers failed-publish-tail hard-exit staging and summary routing. Publish-tail hard failures may abort without terminal state, breaking one-issue reporting acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: failed-publish-tail hard exits cannot produce valid terminal state
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `design-step5c.sh` passes `--trigger publish-tail-failed`, but `stall-recovery-report.sh` rejects that trigger, and `design-publish.sh` shifts staging args so `BAIL_REASON` receives the exit code and `EXIT_CODE` receives the path. Scenario: `design-publish.sh` exits 2, both staging attempts fail validation, then the report gate sees missing terminal state and only prints fallback instead of filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Use an allowed trigger such as `failed`, or add `publish-tail-failed` to the generic trigger vocabulary. Pass trigger and bail as separate args, then add a runtime test that rc 2 creates a valid `design-failure-terminal-state.env`.


### FINDING_15: Tier B duplicate occurrence comments validate against wrong tmpdir
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Tier B duplicate occurrence comments validate against the wrong tmpdir. The comment is created under the helper mktemp at `scripts/file-failure-report-cross-repo.sh:221`, but validation uses `--implement-tmpdir "$body_dir"`, so `validate-tier-b-public-file` rejects it as outside the tmpdir. Scenario: a duplicate `/design` Tier B report with an existing signature falls back with `unsafe-tier-b-comment` instead of posting `+1 occurrence`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Put the assembled comment under the report body directory, or validate with a tmpdir that contains both the comment and copied sensitive corpus.


### FINDING_16: Tier A filing failures can be masked by earlier dedup status
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The code appends normalized dedup output, then appends create output, while `compose_env_key` reads the first `STALL_RECOVERY_REPORT_STATUS`. Scenario: dedup returns `no-match`, issue creation returns `fallback-print-required`, and `handle_compose_outcome` treats the first `no-match` as success and writes a sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Store dedup and create statuses separately, or overwrite `COMPOSE_ENV` with the final create status before handling the outcome.


### FINDING_17: Warning counts go stale when report gate appends warnings but exits 0
- **Reviewer(s)**: codex-generic-output.txt, dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: The report gate refreshes issue counts only when `design-failure-report.sh` exits non-zero. The gate can append warnings to `execution-issues.md` with exit 0 (for example `append_run_log_audit` on invalid terminal state or operator-action audit on cancelled outcomes), leaving stale warning counts in `final-summary.md` until after the summary body is rendered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Refresh counts whenever `execution-issues.md` changes during the gate, or have the helper emit a KV that tells the renderer to refresh before `render_or_fallback`.
  - From dyn-design-reporting-output.txt: After the gate returns, detect new execution-issues content (or parse gate stdout for audit/fallback decisions) and call `refresh_issue_counts` before `render_or_fallback` whenever warnings may have been appended.


### FINDING_18: Report-gate KV isolation lacks runtime integration test
- **Reviewer(s)**: dyn-kv-cleanliness-output.txt
- **Severity**: important
- **Concern**: Report-gate KV isolation is only checked with static `grep` on `render-final-summary.sh` source. There is no runtime test that runs post-publish with a stub `design-failure-report.sh` emitting `DESIGN_FAILURE_REPORT_*` and asserts those lines land in `design-failure-report.stdout.log` but not in captured post-publish stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-cleanliness-output.txt: Add an integration case that stubs `design-failure-report.sh` to print a distinctive KV, runs `--post-publish-only`, and asserts the KV appears only in the sidecar log and not in stdout (while `stdout_starts_with_summary` still holds).


### FINDING_19: Post-publish outcome matrix omits four new failure outcomes
- **Reviewer(s)**: dyn-kv-cleanliness-output.txt
- **Severity**: important
- **Concern**: The post-publish outcome matrix exercises 14 `SUMMARY_OUTCOME` values but omits the four new failure outcomes added in this branch (`failed-postplan`, `failed-clarify`, `failed-judge-panel`, `failed-publish-tail`). There is no runtime check that stdout still starts with `final-summary.md` when the report gate runs for those outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-cleanliness-output.txt: Extend the matrix loop to include the four new outcomes and apply the same `stdout_starts_with_summary` / sentinel checks used for `failed-plan-write` and `failed-publish`.


### FINDING_2: Validator Cancel does not write operator-action sentinel before escalation ledger
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: `validator_autofix_operator_cancel_audit` in `design-step-validator-autofix.sh` only runs when `SUMMARY_OUTCOME` already matches `cancelled-*` at autofix script entry. Autofix runs before the operator prompt; Step 2b / Gate B / discussion-round2 **Cancel** returns to Gate A without setting a cancelled final outcome. Escalation is recorded first (`validator_autofix_record_escalation`), so a later `approved` teardown can still file escalation-success without the operator-action sentinel that should block it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-design-reporting-output.txt: Add a mechanical operator-action writer invoked on validator **Cancel** (or a dedicated helper called from the shared validator-failure path), not gated on `SUMMARY_OUTCOME=cancelled-*` at autofix time. Mirror the plan edge case: validator Cancel after escalation ledger must write the operator-action sentinel before the run can complete successfully.


### FINDING_3: Publish-tail failures invoke duplicate teardown and report-gate passes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-kv-cleanliness-output.txt
- **Severity**: important
- **Concern**: On `design-publish.sh` exit 2 (`publish_tail_fail`), `design-publish.sh` already invokes `render-final-summary.sh` (with report gate). `design-step5c.sh` then deletes captured publish stdout and calls `abort_failed_publish_tail`, which stages terminal state again and invokes `render-final-summary.sh` a second time. The report gate can run twice per failure; correctness depends on sentinels between runs, and the first summary never reaches the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-kv-cleanliness-output.txt: On rc `2`/unexpected rc, either skip the inner `render-final-summary` in `publish_tail_fail` when `design-step5c` will handle teardown, or have `abort_failed_publish_tail` reuse staged state and emit summary from `final-summary.md` without re-invoking the full gate when a sentinel or non-empty summary already exists.


### FINDING_5: handle_compose_outcome writes sentinel on empty compose status
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: `handle_compose_outcome` writes `design-failure-terminal-report.env` when `STALL_RECOVERY_REPORT_STATUS` is empty but `design-failure-chat-print.md` or `design-failure-issue-input.md` is non-empty. Tier A compose can return without status in production; if `gh` filing fails, the sentinel still blocks retry while no issue was created. Partial compose can mark the run as terminal-reported without a confirmed compose/file status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-design-reporting-output.txt: Only write terminal/escalation sentinels on explicit success statuses (`filed`, `dry-run`, `dedup-comment`, etc.). Treat empty compose status as `fallback-print-required` even when a draft artifact exists.


### FINDING_7: Tier A filing ignores passed --repo in forked/multi-remote clones
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier A filing resolves repo from cwd `gh repo view` and ignores `--repo`. Reports from forked or multi-remote clones may file to the wrong GitHub repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: test-design-failure-report.sh covers only a fraction of required teardown-gate scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan harness covers only 4 of ~25 required teardown-gate scenarios. Regressions in terminal precedence, Tier B leak rejection, or operator-sentinel repair could ship without CI failure despite acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: test-design-step3-review.sh is static grep-only without behavioral Step 3 reporting tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Harness is static grep-only; plan required behavioral Step 3 reporting tests. `postplan-failed` might stop staging terminal state or recording escalation while static string checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


