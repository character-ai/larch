### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md
- **Concern**: Plan SKILL.md edit leaves an unclosed bash fence and mixes prose with the fence body. Scenario: Copying the plan verbatim into skills/design/SKILL.md breaks the Abort-branch fence and can swallow the operator-postpone guidance into a code block
- **Proposed resolution**: Close the bash fence immediately after the --tool degraded-tools-gate line; keep the non-degraded/postpone note and example in separate prose or a second complete fenced invocation



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_lifecycle.py
- **Concern**: Step 0 abort path has no no-reap-on-cleanup-failure regression test while Step 6 coverage is planned. Scenario: A step0_abort_cleanup_main regression could call reap_pid_residuals despite non-zero tmpdir cleanup (or reorder the gate) and ship with only Step 6 guarding the shared contract
- **Proposed resolution**: Add a test that forces cleanup-tmpdir failure (via the existing subprocess.run monkeypatch), asserts reap_pid_residuals is not invoked, and asserts the three PID cache files remain under Path.home()/.cache/larch/sessions/



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step0_env.py:123-169
- **Concern**: _parse_wrapper_args needs pinned ns.reason/ns.tool initializer defaults. Scenario: Step0WrapperNs uses manual flag scanning; adding --reason/--tool only to value_flags leaves omitted flags as empty strings, so the degraded-tools Abort caller regresses to a blank banner and empty failure-log tool=
- **Proposed resolution**: Initialize ns.reason and ns.tool to the degraded-tools default strings in the _parse_wrapper_args setup block before argv scan; let value_flags override when present



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_lifecycle.py
- **Concern**: Step 0 abort cleanup-failure no-reap test still missing. Scenario: Plan mandates Step 6 no-reap when cleanup_tmpdir_main is non-zero but not the symmetric Step 0 abort gate from the same failure mode; reorder or reap-after-failure regressions on abort would slip through
- **Proposed resolution**: Add a step0_abort_cleanup_main test that mocks cleanup_tmpdir_main returning non-zero, asserts reap_pid_residuals is not called, and PID cache files remain



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md
- **Concern**: Planned SKILL.md bash fence is unclosed. Scenario: The Step 0a Abort example omits the closing fence before prose continuation; copying it verbatim breaks SKILL.md markdown
- **Proposed resolution**: Close the bash fence after the --tool degraded-tools-gate line; keep the operator-postpone example in a separate fenced block



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:119-125
- **Concern**: SKILL.md update leaves the Abort bash fence unclosed. Scenario: The ### UPDATED: skills/design/SKILL.md section opens a ```bash fence for step0-abort-cleanup but never closes it before the prose note and operator-postpone example. An implementer can copy that block verbatim and break the shipped skill markdown, hiding or corrupting later Step 0 orchestration text.
- **Proposed resolution**: Close the bash fence after the --tool degraded-tools-gate line, then add the caller-specific --reason/--tool note and postpone example outside the fence (or in a second fenced block). ### 1. [correctness] `skills/design/SKILL.md:119-125` — Unclosed Abort bash fence The plan’s `### UPDATED: skills/design/SKILL.md` section opens a ` ```bash ` fence for the degraded-tools **Abort** invocation but never closes it before the “Add a short note…” prose and operator-postpone example. If copied as written, the shipped skill doc breaks. **Suggested revision:** Close the fence after the `--tool degraded-tools-gate` line, then place the caller-attribution note and postpone example outside that fence (or in a separate fenced block).



### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:21-39,292
- **Concern**: Moving the `step0-parsed-` literal into `session_env.py` leaves the design-structure harness pointed at the old combined design module scan. Scenario: The planned `_parsed_cache_path` delegation removes the only `step0-parsed-` literal from the files concatenated into `DESIGN_LIFECYCLE`; `make test-design-structure` then fails even though the new canonical helper exists in `session_env.py`.
- **Proposed resolution**: Add `scripts/test-design-structure.sh` to the plan and update the check to include `python/larch/state/session_env.py` or assert `step0-parsed-` against `SESSION_ENV` plus `_parsed_cache_path` delegation in the design module.



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:116-122
- **Concern**: The proposed Abort-branch edit opens a bash fence for the launcher example but never closes it before the required prose. Scenario: If copied into the runtime skill, the non-degraded abort guidance and following headings render as shell code, so the documented caller-specific `--reason`/`--tool` contract is ambiguous or hidden.
- **Proposed resolution**: Close the bash fence immediately after `--tool degraded-tools-gate`; put the operator-postpone note in prose and, if needed, use a separate closed bash fence for the two example flags.



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:116-122
- **Concern**: Planned Abort branch bash fence is left open. Scenario: The proposed SKILL.md edit starts a bash fence for the explicit --reason/--tool invocation but never closes it before explanatory prose, so the non-degraded guidance can land inside the shell block and the skill docs become malformed
- **Proposed resolution**: Close the bash fence immediately after --tool degraded-tools-gate, then put the non-degraded note and postpone example in prose or in a separate closed bash block



