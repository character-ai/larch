### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_models.py:12
- **Concern**: Plan examples call skill=Skill.IMPLEMENT and Skill.DESIGN, but Skill is a Literal alias, not an enum with members. Scenario: If implemented literally, the new report_tokens_issue tests fail before exercising the trim-label behavior
- **Proposed resolution**: Keep the minimum-change contract and pass string literals: skill="implement" and skill="design"

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_report_tokens_cli.py:42-44
- **Concern**: post_issue fake lacks the new skill argument planned for report_tokens_cli.py. Scenario: After report_tokens_cli.py calls post_issue(..., skill=skill), this monkeypatched fake_post raises TypeError and py-test fails before verifying issue posting
- **Proposed resolution**: Add python/test_report_tokens_cli.py to the plan and update fake_post stubs to accept skill, preferably asserting the expected skill value

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:105-116 python/run_logs.py:162-175
- **Concern**: Plan misses the Python implement timing-report caller while making LARCH_TIMING_SKILL=implement mandatory for implement reports. Scenario: If the Python ship/log path is enabled with ambient DESIGN_TMPDIR or LARCH_TIMING_SKILL=design, timing-report.sh can still render SIMPLE/HARD into implement timing JSON, violating the no-workflow implement contract
- **Proposed resolution**: Add python/run_logs.py to the plan: set LARCH_TIMING_SKILL=implement and clear/remove DESIGN_TMPDIR in _report_subprocess_env or on the timing-report subprocess env; add a python/test_run_logs.py env assertion for that subprocess

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:105-116; python/run_logs.py:162-174
- **Concern**: Python implement log refresh is another implement-owned timing-report invocation but the plan does not pin LARCH_TIMING_SKILL=implement or clear DESIGN_TMPDIR there. Scenario: If the Python ship/log path runs with ambient LARCH_TIMING_SKILL=design and DESIGN_TMPDIR, the proposed design-only fallback can still leak SIMPLE/HARD into implement timing-report JSON
- **Proposed resolution**: Extend _report_subprocess_env for implement refresh to set LARCH_TIMING_SKILL=implement and remove DESIGN_TMPDIR before invoking timing-report.sh

### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:93-104 python/run_logs.py:158-173
- **Concern**: Plan misses the Python implement log refresh timing-report caller. Scenario: When LARCH_SHIP_PR_IMPL=python or tests exercise python/run_logs.py, _report_subprocess_env copies ambient LARCH_TIMING_SKILL=design and DESIGN_TMPDIR, then _render_ledger_reports writes an implement timing report that can still resolve SIMPLE/HARD from design run-params, violating the no implement workflow leak acceptance criterion
- **Proposed resolution**: Add python/run_logs.py to the plan: set env["LARCH_TIMING_SKILL"]="implement" and remove or blank DESIGN_TMPDIR for timing-report subprocesses, plus a python/test_run_logs.py polluted-env regression

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/test_report_tokens_cli.py:39-42
- **Concern**: Plan changes post_issue to require skill but omits CLI test fakes. Scenario: After report_tokens_cli.py passes skill=skill into post_issue, the fake_post in test_main_success_posts_issue_and_keeps_single_cache_trailer rejects the unexpected keyword and make py-test fails
- **Proposed resolution**: Update python/test_report_tokens_cli.py fakes to accept skill and assert implement/design forwarding as needed

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-workflow-erasure
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:105-116,162-175,548,593
- **Concern**: Plan omits the Python run-log refresher timing-report caller. Scenario: With LARCH_SHIP_PR_IMPL=python or Python finalize/ship paths, _render_ledger_reports inherits ambient env and calls timing-report.sh for implement without LARCH_TIMING_SKILL=implement or DESIGN_TMPDIR clearing, so the after-state still has a stale implement timing-report path outside the shell callers named in the plan
- **Proposed resolution**: Add python/run_logs.py to scope: set env["LARCH_TIMING_SKILL"]="implement" and remove/blank DESIGN_TMPDIR for the timing-report subprocess; add/update a focused python/test_run_logs.py assertion that the timing-report call receives the implement-pinned env

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-report-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_models.py:12; python/test_report_tokens_issue.py:13-14
- **Concern**: Plan uses nonexistent Skill.IMPLEMENT and Skill.DESIGN constants for new issue-trimming tests. Scenario: Skill is a Literal alias, not an Enum, so implementing the planned test call shape raises AttributeError or import churn before validating trim labels
- **Proposed resolution**: Use skill="implement" and skill="design" string literals, typed as Skill if needed; do not convert Skill to an enum for this minimum-change PR
