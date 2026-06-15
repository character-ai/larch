### FINDING_1: AUTOFIX ok path omits ORIGINAL_VALIDATE_LOG_FILE contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `AUTOFIX_STATUS=ok` wrapper append does not require the `ORIGINAL_VALIDATE_LOG_FILE` `--output-file` contract from `skills/design/SKILL.md`. After revalidation overwrites `validate-plan-commands.log`, a Warnings row without `--output-file "${_autofix_log_file:-$DESIGN_TMPDIR/validate-plan-commands.log}"` can reference stale or empty evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the ok branch, append exactly one Warnings row via run-log append-failure using --tool "validate-plan-commands(auto-fixed:${_autofix_fixed_by})" --exit-code 0 --category Warnings --output-file "${_autofix_log_file:-$DESIGN_TMPDIR/validate-plan-commands.log}" --redact; extend the AUTOFIX_STATUS=ok harness case to assert that path when ORIGINAL_VALIDATE_LOG_FILE is set


### FINDING_3: SKILL.md ok branch will double-append Warnings row after wrapper change
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Wrapper-owned `AUTOFIX_STATUS=ok` audit leaves the prompt-side audit in place. After the plan adds an ok branch to `design-step-validator-autofix.sh`, the wrapper appends `validate-plan-commands(auto-fixed:...)` and the unchanged `skills/design/SKILL.md` ok branch still instructs the orchestrator to append the same Warnings row again. This violates the exactly-one-row edge case and the issue's double-logging gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update the plan to include skills/design/SKILL.md. Change the ok branch to say the wrapper already records the auto-fixed Warnings row, then continue the success re-entry path without a second prompt-side append.
  - From Codex-Pragmatic: Update the plan to include skills/design/SKILL.md. Change the ok branch to say the wrapper already records the auto-fixed Warnings row, then continue the success re-entry path without a second prompt-side append.


### FINDING_4: Collect-mode harness must stub agent collect-results
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned collect-mode harness stubs only `dirty-tree checkpoint`, not `agent collect-results`. `design-step1d5.sh --mode collect` always runs `python3 ... agent collect-results` before `design_collect_launch_failures` and `design_brainstorm_dirty_checkpoint`. A `python3` stub that handles only `dirty-tree checkpoint` makes collect exit non-zero, writes `brainstorm-collect.failure.log`, and pollutes `execution-issues.md` before launch-failure, idempotency, and dirty-tree cases run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the NEW harness section, require the PATH python3 stub to no-op `agent collect-results` with exit 0 (minimal stdout), stub `dirty-tree checkpoint` per the dirty-tree cases, and ignore or stub `design pause-save` so collect reaches the launch-failure and dirty-tree assertions


### FINDING_5: Checkpoint plan misses sentinel-only recovery evidence contract
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The checkpoint plan misses the sentinel-only recovery evidence contract. The plan adds `oos disposition-checkpoint` to idempotent sentinel recovery after writing recovered `oos-issues.ndjson`, but the existing checkpoint rejects a nonempty ndjson with filed URLs when none of the accepted-OOS files exists. A sentinel-only rerun that currently returns idempotent success can become `disposition_checkpoint_failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Specify sentinel recovery ordering or evidence materialization so the real checkpoint passes for sentinel-only recovery, and cover it with the real disposition checkpoint rather than only a fake CLI.


### FINDING_6: Direct-target regression test must cover all design modules
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Design direct-target tests only sample representative modules. Item 2 requires focused rows for each planned `python/design_*.py` module except the approved `design_legacy.py` carve-out. A representative-only `_direct_targets` test can pass while an un-sampled required design module still falls through to broad `py-test` and misses the focused harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Make the new `_direct_targets` regression test parameterize every planned design module-to-target row, plus the explicit no-dedicated-row assertion for `python/design_legacy.py`.




### FINDING_1: Collect harness python3 stub omits run-log append-failure
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The collect-mode harness `python3` stub list omits `run-log append-failure`. Collect mode calls `design_append_brainstorm_failure` for per-slot launch failures and for agent collect-results failures; both invoke `python/cli.py run-log append-failure`. A stub that only handles agent collect-results dirty-tree checkpoint and design pause-save will exit 99 or skip External Reviewer Issues rows, so launch-failure and idempotency assertions never exercise real collect behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add run-log append-failure to the required python3 stub commands (mirror test-design-clarify.sh) and assert execution-issues.md updates in the launch-failure cases.


### FINDING_4: Collect harness section omits minimum wrapper environment contract
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The new collect harness section omits the minimum wrapper environment contract. Invoking `design-step1d5.sh --mode collect` without `DESIGN_TMPDIR`, `CLAUDE_PLUGIN_ROOT`, and `ISSUE_NUMBER` (as sibling harnesses set) fails at `design_require_plugin_root` or produces non-reproducible collect assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document required env exports in the NEW harness section: DESIGN_TMPDIR temp root, CLAUDE_PLUGIN_ROOT repo root, ISSUE_NUMBER dummy, plus PATH python3 stub; mirror test-design-step-validator-autofix.sh / test-design-step3-entry.sh setup


### FINDING_5: test-design-step1d5.sh absent from design SKILL.md wrapper contract inventory
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The new harness `test-design-step1d5.sh` is absent from the wrapper contract inventory. `agent-lint` S030 treats `skills/design/scripts/test-*.sh` as orphaned unless pinned in the parent `SKILL.md` (peer harnesses like `test-design-step3-review.sh` are listed); `make lint` can fail after Item 4 lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/test-design-step1d5.sh` to the `skills/design/SKILL.md` wrapper contract inventory beside the other `test-design-step*` entries


### FINDING_7: Checkpoint failure before step9a1 stamp can re-file same OOS batch on retry
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The new checkpoint failure path can re-file the same accepted OOS batch on retry. If a newly filed batch writes `oos-issues-created.md` and `oos-issues.ndjson`, then the planned disposition checkpoint fails before run statistics and `steps_ran.step9a1`, the next `oos file` run still sees `prior_sentinel` plus the original accepted blocks, enters the create loop again, and may create duplicate public OOS issues before the checkpoint can pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add retry idempotency for checkpoint-failed filed batches before calling issue create-one, for example parse persisted sentinel titles or store an input digest and skip already-filed blocks when the accepted batch matches; add the planned failing-checkpoint test to assert a rerun does not call issue create-one again


### FINDING_8: Autofix ok audit branch runs before status normalization and rc override
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned ok audit branch is placed before existing status normalization and rc failure override. A helper can print `AUTOFIX_STATUS=ok` but exit nonzero; if the new branch runs immediately after parsing, it appends a false auto-fixed Warnings row before lines 179-187 convert the result to failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Place the ok-path run-log append after the case normalization, the _autofix_rc nonzero override, and the log-file default; guard it with the final normalized _autofix_status == ok before escalation handling




### FINDING_1: Checkpoint-failed OOS rerun can duplicate filed issues
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: After a successful issue batch writes `oos-issues-created.md` and `oos-issues.ndjson` but disposition-checkpoint fails before success markers, a rerun still has accepted blocks without embedded filed URLs. The idempotent guard (`prior_sentinel and not blocks`) is false, so `_run_issue_batch` runs again and can create duplicate public issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In _file() treat existing sentinel plus ndjson as batch-level already-filed evidence before _maybe_combine_with_codex/_run_issue_batch: recover persisted URLs skip create-one and proceed to checkpoint then stats/stamp; extend the rerun test to assert this path when blocks is non-empty


### FINDING_2: Ok-path Warnings append missing required `--site`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: On the ok-path, the Warnings append for append-failure omits required `--site`. `python/run_logs.py` requires `--site`; the wrapper ok-path spec lists only tool/exit-code/category/output-file/redact, so append-failure exits 1 and no auto-fixed Warnings row is recorded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add --site "$SITE" (or the same site token mapping used in skills/design/SKILL.md) to the ok-path append-failure invocation; extend test-design-step-validator-autofix.sh to assert the row is written


### FINDING_3: Checkpoint failure leaves provisional ndjson marked Step 9a.1 complete
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan writes `oos-issues.ndjson` before the checkpoint; on checkpoint failure it only suppresses run-statistics and the success stamp. Existing completion heuristics treat a non-empty `oos-issues.ndjson` alone as Step 9a.1 complete, so a failed checkpoint can still look complete in final-report stamping, audit, or run-log verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: On checkpoint failure, either stamp steps_ran.step9a1=false when the manifest exists, or update the completion heuristics to require run-statistics or an explicit true stamp for this provisional ndjson state. Extend the failing-checkpoint test to prove downstream completion detection stays false.



### FINDING_1: OOS retry can duplicate public issues when sentinel/ndjson already exist
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: After a checkpoint failure, if `oos-issues-created.md` and provisional `oos-issues.ndjson` already exist but accepted-OOS blocks still lack inline filed URLs, `_working_batch()` keeps those blocks and the flow may call `_maybe_combine_with_codex()` / `_run_issue_batch()` again, creating duplicate public OOS issues on retry. The retry helper does not spell out partial re-file behavior (match persisted sentinel/ndjson titles to accepted blocks, move matched items into `already`, run combine/issue-cap/batch only on remaining unfilled blocks).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make the retry helper explicit: match persisted sentinel/ndjson titles to accepted blocks, move matched items into the `already` set, and run combine/issue-cap/batch only on the remaining unfilled blocks; add a `test_oos_filer.py` case with sentinel+ndjson plus one new accepted block


### FINDING_2: Provisional ndjson-only Step 9a.1 heuristic should return False, not None
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan text allows incomplete or `None` for ndjson-only `_step9a1_heuristic` results. `_refresh_run_log` only writes `steps_ran.step9a1` when the heuristic is not `None`, so `None` leaves a prior `step9a1=true` in place after a checkpoint failure that already wrote `oos-issues.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Require ndjson without `run-statistics.md` (and without explicit manifest `step9a1=true`) to return False from `_step9a1_heuristic`; update `python/test_run_logs.py` matrix accordingly


### FINDING_4: Collect harness does not assert per-slot collection output or argv
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The new collect harness does not explicitly assert per-slot collection output or argv. `test-design-step1d5.sh` could pass even if collect mode drops one brainstorm output path or stops relaying `agent collect-results` stdout, leaving Item 4's per-slot logging requirement unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add a stub assertion that `agent collect-results` receives every supplied output path and emits distinct per-path stdout, then assert the wrapper relays or records both slot lines


### FINDING_5: Sentinel-only recovery guard can skip evidence creation incorrectly
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The sentinel-only recovery guard is phrased as if `_accepted_input_paths(tmpdir)` can be absent. `_accepted_input_paths()` always returns candidate paths, so a literal implementation can skip recovery evidence creation; the real checkpoint then fails when provisional `oos-issues.ndjson` has URLs but no accepted files exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Specify the guard as `not any(path.is_file() for path in _accepted_input_paths(tmpdir))` and write recovered evidence using the strict `- **Filed URL**: <url>` form before invoking the checkpoint




### FINDING_3: Shipped `/implement` SKILL.md Step 9a.1 completion semantics conflict with Python-path checkpoint behavior
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The plan changes Python Step 9a.1 completion semantics but omits updates to the shipped `/implement` prompt contract. Current SKILL.md text (NEVER #14–15 at `skills/implement/SKILL.md:58-60`, pre-ship `oos file` hook at `768-774`, bail-time invariant at `792`) still treats pre-gate `oos-issues.ndjson` as proof Step 9a.1 ran or as evidence that suppresses `steps_ran.step9a1=false`, and describes disposition-checkpoint primarily on the bash `OOS_PENDING` path. After a checkpoint-failed Python OOS filing leaves provisional `oos-issues.ndjson` without `run-statistics.md`, orchestrator and audit tooling can disagree on whether Step 9a.1 completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `skills/implement/SKILL.md` update: Step 9a.1 complete only with `run-statistics.md` or explicit `steps_ran.step9a1=true`; provisional ndjson alone is not completion
  - From Codex-Generic: Add `skills/implement/SKILL.md` to the plan and update the Python `oos file` and bail-time invariant text so only post-checkpoint `run-statistics.md` or explicit `steps_ran.step9a1=true` marks Step 9a.1 complete


### FINDING_4: OOS retry dedup keyed on title can miss after combine rewrites titles
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Retry matching in `python/oos_filer.py` (`_working_batch`, lines 104-124) keys dedup on normalized title. If checkpoint fails after partial issue creation and a combine step rewrites titles, a retry with the same accepted blocks and persisted ndjson may fail to match prior filings and re-file duplicate public issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Match persisted sentinel and ndjson by Filed URL first; secondary-match titles via existing `_normalize_title`; reuse `_FILED_URL_LINE_RE` and `_working_batch` patterns


### FINDING_6: Plan omits `test_pr_body.py` coverage for bail-time `step9a1` stamping
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan names only `python/test_ship.py` or an unspecified final-report test for Step 9a.1 false stamping, but `_stamp_skipped_steps_for_terminal_report` lives in `python/pr_body.py:854-868` and neither `python/test_pr_body.py` nor `python/test_ship.py` covers `step9a1` stamping today. The ndjson-only fix in `pr_body.py` can ship without regression coverage because the plan does not pin `python/test_pr_body.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: python/test_pr_body.py` with an explicit test of `_stamp_skipped_steps_for_terminal_report` asserting ndjson without `run-statistics.md` still stamps `steps_ran.step9a1=false`



