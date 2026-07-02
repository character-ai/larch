### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: code-quality
- **Location**: python/larch/review/review_dispatch_panel.py:720-752
- **Concern**: Code-review panel dispatch producers are missing from the plan. The plan updates plan_review_panel.py and agent_waterfall.py but not review_dispatch_panel.py or agent_voters.py, which own /implement Step 5 and /review specialist and voter waterfall launches. Acceptance requires committed per-slot prompt sizes for those panels. Without forwarding LARCH_PANEL_* (or --panel-artifact-dir / --panel-round-num) into dispatch-waterfall and child Popen env, _panel_logging_enabled() stays false and no rows are written.. Scenario: Implement Step 5 and /review call review dispatch-panel and agent dispatch-voters, not plan-review panel-dispatch. Only design paths get panel env in the current plan, so measure-panel-cost and publish tests for implement/review can pass only on fixtures that inject env manually.
- **Proposed resolution**: Add ### UPDATED: python/larch/review/review_dispatch_panel.py and ### UPDATED: python/larch/agents/agent_voters.py: before each dispatch-waterfall (and direct voter Popen where applicable), set panel env (LARCH_PANEL_ARTIFACT_DIR=review tmpdir or round dir, LARCH_PANEL_ROUND_NUM, LARCH_PANEL_SITE, per-slot LARCH_PANEL_SLOT via agent_waterfall) and pass any new waterfall CLI flags. Extend agent_waterfall _parse_args/_launch_slot to honor panel_artifact_dir and forward env={**os.environ,...} on every launch-review/launch-claude-review Popen.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/review/coder_runner.py:380-381
- **Concern**: Fix-coder implementer instrumentation has no producer that sets panel env. The plan appends implementer rows in coder_runner.py only when LARCH_PANEL_SLOT is already set, but no listed file sets that env before apply_findings_with_coder. Issue scope includes the implementer slot.. Scenario: Issue acceptance and scope list implementer alongside specialist/voter/aggregator. review-and-fix Step 5 can run the fix coder without any LARCH_PANEL_* export, so coder-prompt.md is never measured and implementer bytes are absent from round TSVs and measure-panel-cost.
- **Proposed resolution**: Add ### UPDATED: python/larch/review/round_runner.py (or review_and_fix.py): before apply_findings_with_coder, set LARCH_PANEL_SLOT, LARCH_PANEL_SITE (implement Step 5 / review), LARCH_PANEL_ARTIFACT_DIR=round_dir, LARCH_PANEL_ROUND_NUM, and slot_kind=implementer; keep /implement Step 2 feature coder excluded.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/review/review_aggregate.py:831-895
- **Concern**: Code-review aggregator prompt-size logging is limited to plan mode in the plan. The review_aggregate update sets panel env only when input_mode=plan and round_dir is set. /implement Step 5 and /review still run review.findings_aggregator through the same module without panel env on dispatch-waterfall.. Scenario: Issue scope names aggregator as an instrumented slot. Plan-mode design aggregation may log orchestrator-aggregator.md, but code-review rounds leave aggregator-prompt.md unmeasured, so committed logs understate aggregator panel cost and agent_file ranking skews toward specialists/voters only.
- **Proposed resolution**: Extend the review_aggregate.py change to code-review paths: set LARCH_PANEL_ARTIFACT_DIR to review_tmpdir (or round_dir when used), LARCH_PANEL_SLOT=aggregator, LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md, and pass env= into dispatch-waterfall subprocess.run; add a non-plan harness assertion in test_review_aggregate.py or test_review_pipeline.py.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:842-873
- **Concern**: Code-mode aggregator prompt-size rows lose the aggregator source-agent attribution. Scenario: The plan sets LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md only for input_mode=plan, but /review and /implement Step 5 call review aggregate-findings in default code mode with a prompt_file row built from the same agent. Those rows cannot rank agents/orchestrator-aggregator.md or include its agent bytes for code-review aggregation.
- **Proposed resolution**: Set the same aggregator panel env for code mode before dispatch-waterfall, using round_dir when present or review_tmpdir as the artifact dir, and always include LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md for the aggregator slot.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:360-380
- **Concern**: Implementer prompt logging depends on panel env that this in-process path never receives. Scenario: apply_findings_with_coder composes coder-prompt.md inside the parent Python process, not through agent_waterfall or a launch-review subprocess. With helper gating requiring LARCH_PANEL_SLOT, the planned coder_runner append can skip every review.fix_coder prompt unless an unrelated parent env happens to be set, leaving /implement Step 5 without the implementer slot row the scope requires.
- **Proposed resolution**: In coder_runner, establish an explicit local panel context for the append, or allow append_panel_prompt_size to take an explicit slot_kind=implementer and artifact dir for this scoped in-process caller.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:360-416
- **Concern**: Implementer prompt-size rows are conditional on panel env that nothing in the plan wires. Scenario: The plan appends `slot_kind=implementer` only when `LARCH_PANEL_SLOT` is already set, but no listed file sets panel env for `review.fix_coder`. `apply_findings_with_coder` uses `run-external-agent`, not `launch-review`, so `_review_launcher` never runs and implementer bytes stay unlogged despite acceptance requiring implementer slot coverage
- **Proposed resolution**: In `coder_runner.py`, set `LARCH_PANEL_SLOT`, `LARCH_PANEL_SITE`, `LARCH_PANEL_ARTIFACT_DIR` (and round keys when `round_dir.name` matches `round-<N>`) locally immediately before `append_panel_prompt_size`, or call `append_panel_prompt_size` with explicit fields without relying on unset parent env

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:870-895
- **Concern**: Code-review aggregator dispatch is omitted from panel-env wiring; only `input_mode=plan` is covered. Scenario: Implement Step 5 and `/review` call `aggregate-findings` with default `input_mode=code` and no `--round-dir`. The plan sets `LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md` only for plan mode, so aggregator prompt bytes miss agent attribution and may fall into the generated bucket instead of ranking `agents/orchestrator-aggregator.md`
- **Proposed resolution**: Mirror the plan-mode child-env block for code mode before `subprocess.run(dispatch_argv, env=...)`: set `LARCH_PANEL_SLOT=aggregator`, site from caller context, `LARCH_PANEL_ARTIFACT_DIR` to `round_dir` when `review_tmpdir` is `round-<N>` else `review_tmpdir`, and `LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md`

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:868-880
- **Concern**: Prior aggregator fix remains incomplete: code-review aggregator prompt-size env is only planned for design plan mode. Scenario: review_core_body.py invokes aggregate-findings for /review and /implement Step 5 without --input-mode plan. The plan only sets LARCH_PANEL_SLOT=aggregator and LARCH_PANEL_SOURCE_AGENT_FILE for input_mode=plan, so code-review aggregator prompt bytes are unlogged or lose source-agent attribution.
- **Proposed resolution**: Set the same panel env for every review_aggregate dispatch, using round_dir when supplied or review_tmpdir otherwise, and always set LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md.

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:380-409
- **Concern**: Implementer rows depend on panel env that no planned caller sets. Scenario: append_panel_prompt_size skips unless LARCH_PANEL_SLOT is present. apply_findings_with_coder is called directly from round_runner.py and review_and_fix.py, but the plan only updates coder_runner and says to log when review fix-coder dispatch sets panel env. The required implementer slot can therefore produce no row.
- **Proposed resolution**: Have apply_findings_with_coder supply explicit implementer logging context itself, or set LARCH_PANEL_SLOT=implementer plus artifact dir around its existing calls before appending round_dir/panel-prompt-sizes.tsv.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py:749-752
- **Concern**: Implement and /review panel dispatch never enables prompt-size logging. Scenario: Logging is gated on non-empty LARCH_PANEL_SLOT, but the plan only wires panel env export in plan_review_panel.py and plan-mode review_aggregate.py. /implement Step 5 and /review specialists and voters enter through review_dispatch_panel.py and agent_voters.py, which call agent dispatch-waterfall without setting LARCH_PANEL_ARTIFACT_DIR or LARCH_PANEL_SLOT. Those runs will emit no panel-prompt-sizes.tsv, so the acceptance path for implement and review panels stays empty. Decompose also uses dispatch-waterfall without --site (python/larch/design/decompose.py:465-471), so a site-default heuristic in agent_waterfall would falsely instrument out-of-scope decompose slots.
- **Proposed resolution**: Add ### UPDATED: python/larch/review/review_dispatch_panel.py and ### UPDATED: python/larch/agents/agent_voters.py. Before each dispatch-waterfall subprocess, export the panel env block (artifact dir from --review-tmpdir, round num when known, site, per-slot LARCH_PANEL_SLOT) or pass a new --panel-artifact-dir flag. In agent_waterfall, enable panel logging only when that explicit signal is present; do not key off the default site review Step 2 alone.

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/review/coder_runner.py:360-410
- **Concern**: Implementer prompt-size rows have no panel-env setter. Scenario: The plan appends slot_kind=implementer only when review fix-coder dispatch sets panel env, but no listed file sets LARCH_PANEL_* before apply_findings_with_coder. round_runner.py and review_and_fix.py call the coder directly, so /implement Step 5 and /review fix-coder passes will skip implementer measurement even though the issue scope lists implementer slots.
- **Proposed resolution**: In coder_runner.py (or an explicit caller entry in the plan), seed panel env from round_dir before append_panel_prompt_size: LARCH_PANEL_SLOT=implementer, LARCH_PANEL_ARTIFACT_DIR=<round_dir>, LARCH_PANEL_ROUND_NUM when known, and LARCH_PANEL_SITE for the active review site. Keep /implement Step 2 feature-coder out of scope.

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/review/review_aggregate.py:892-895
- **Concern**: Code-review findings aggregator is not instrumented. Scenario: The plan sets panel env only for input_mode=plan with --round-dir. /implement Step 5 and /review call aggregate-findings with default input_mode=code and launch dispatch-waterfall at review_aggregate.py:895 without panel env, so code-review aggregator prompts are omitted from panel-prompt-sizes.tsv and measure-panel-cost undercounts a listed slot kind.
- **Proposed resolution**: Extend the review_aggregate.py plan step for input_mode=code: before dispatch-waterfall, export the same panel env block with LARCH_PANEL_SLOT=aggregator, LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md, and LARCH_PANEL_ARTIFACT_DIR=<review_tmpdir or round_dir>. Pass env= into the subprocess.run call. Add a focused test in test_review_aggregate.py or test_review_pipeline.py.

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:842-880
- **Concern**: Code aggregator source-agent attribution is only planned for input_mode=plan. Scenario: The code-review aggregator uses agents/orchestrator-aggregator.md on /review and /implement Step 5, but the plan only sets LARCH_PANEL_SOURCE_AGENT_FILE for plan-mode aggregation. Code-mode aggregator rows fall into generated/no-agent buckets, so measure-panel-cost cannot rank a required panel-tier source file.
- **Proposed resolution**: Set LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md for code and plan aggregation dispatches. Keep the round_dir artifact override only for design plan-review.

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:380
- **Concern**: Implementer prompt logging depends on panel env that no planned caller sets. Scenario: apply_findings_with_coder composes coder-prompt.md in-process during /implement Step 5 and /review fix application. The plan gates append_panel_prompt_size on LARCH_PANEL_SLOT, but no planned review_and_fix or round_runner change sets LARCH_PANEL_SLOT=implementer before this in-process append, so implementer rows are skipped.
- **Proposed resolution**: In coder_runner, add explicit implementer panel context for the local append, for example artifact dir=round_dir, slot=implementer, site=review.fix_coder, without instrumenting /implement Step 2.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py:752
- **Concern**: python/larch/agents/agent_voters.py:302-327. Scenario: Implement and standalone /review panel logging never activates on dispatch-waterfall
- **Proposed resolution**: Opt-in gating requires non-empty LARCH_PANEL_SLOT, and the plan says agent_waterfall must not set panel env for non-panel waterfall callers (decompose). The plan updates agent_waterfall.py with optional panel_artifact_dir but does not list review_dispatch_panel.py or agent_voters.py as UPDATED and does not add a dispatch-waterfall CLI flag in _parse_args. Those are the sole Step 5 and /review entrypoints that call dispatch-waterfall with --model-role review or vote. Without passing panel instrumentation (for example --panel-artifact-dir or preset LARCH_PANEL_* on the subprocess env), children keep empty LARCH_PANEL_SLOT, append_panel_prompt_size no-ops, and committed implement/review run logs miss required panel-prompt-sizes.tsv rows. Add review_dispatch_panel.py and agent_voters.py (and a documented dispatch-waterfall flag or env preset in agent_waterfall.py) so panel dispatch passes LARCH_PANEL_ARTIFACT_DIR plus site/round context into dispatch-waterfall; keep decompose and other non-panel waterfall callers unset.

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/review/review_aggregate.py:873-895
- **Concern**: Code-review aggregator prompt-size rows are not wired. Scenario: Scope requires aggregator slots for /implement Step 5 and /review. The plan only sets LARCH_PANEL_* before dispatch-waterfall for input_mode=plan with round_dir. Implement and /review use input_mode=code; aggregate-findings calls dispatch-waterfall without model-role or panel env, so aggregator launches skip _panel_logging_enabled and no aggregator row lands in round-local panel-prompt-sizes.tsv.
- **Proposed resolution**: Mirror the plan-mode child env block for input_mode=code when review_tmpdir is a round directory: set LARCH_PANEL_SLOT=aggregator, LARCH_PANEL_ARTIFACT_DIR to the round dir, LARCH_PANEL_SOURCE_AGENT_FILE=agents/orchestrator-aggregator.md, and LARCH_PANEL_SITE from the caller site before dispatch-waterfall.

### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/review/coder_runner.py:380-416
- **Concern**: Implementer (review.fix_coder) logging has no panel-env producer. Scenario: Scope lists implementer slots, and the plan updates coder_runner.py to append after _compose_coder_prompt only when panel env is present, but no listed file sets LARCH_PANEL_* for review.fix_coder. apply_findings_with_coder never exports panel context, so implementer rows are always skipped even when an external fix-coder runs.
- **Proposed resolution**: In coder_runner.apply_findings_with_coder, set minimal LARCH_PANEL_* (slot=implementer, artifact_dir=round_dir, site/review.fix_coder, round_num when known) immediately before append_panel_prompt_size; keep /implement Step 2 feature coder out of scope.
