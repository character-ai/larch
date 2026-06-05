### FINDING_1: Use string literal skills in issue tests
- **Reviewer(s)**: Codex-Arch, Codex-dyn-report-contracts
- **Severity**: important
- **Concern**: Planned tests use `Skill.IMPLEMENT` / `Skill.DESIGN`, but `Skill` is a `Literal` alias rather than an enum, so the tests would fail before validating trim-label behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the minimum-change contract and pass string literals: skill="implement" and skill="design"
  - From Codex-dyn-report-contracts: Use skill="implement" and skill="design" string literals, typed as Skill if needed; do not convert Skill to an enum for this minimum-change PR


### FINDING_2: Update CLI post_issue test fakes for skill argument
- **Reviewer(s)**: Codex-Edge, Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes `post_issue` to receive a `skill` argument, but existing CLI test monkeypatch fakes do not accept it, causing tests to fail before verifying issue posting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add python/test_report_tokens_cli.py to the plan and update fake_post stubs to accept skill, preferably asserting the expected skill value
  - From Codex-Requirements: Update python/test_report_tokens_cli.py fakes to accept skill and assert implement/design forwarding as needed


### FINDING_3: Pin Python run-log timing reports to implement env
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-workflow-erasure
- **Severity**: important
- **Concern**: The plan misses the Python run-log/timing-report caller, which can inherit ambient `LARCH_TIMING_SKILL=design` or `DESIGN_TMPDIR` and leak design SIMPLE/HARD workflow data into implement timing reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add python/run_logs.py to the plan: set LARCH_TIMING_SKILL=implement and clear/remove DESIGN_TMPDIR in _report_subprocess_env or on the timing-report subprocess env; add a python/test_run_logs.py env assertion for that subprocess
  - From Codex-Pragmatic: Extend _report_subprocess_env for implement refresh to set LARCH_TIMING_SKILL=implement and remove DESIGN_TMPDIR before invoking timing-report.sh
  - From Codex-Requirements: Add python/run_logs.py to the plan: set env["LARCH_TIMING_SKILL"]="implement" and remove or blank DESIGN_TMPDIR for timing-report subprocesses, plus a python/test_run_logs.py polluted-env regression
  - From Codex-dyn-workflow-erasure: Add python/run_logs.py to scope: set env["LARCH_TIMING_SKILL"]="implement" and remove/blank DESIGN_TMPDIR for the timing-report subprocess; add/update a focused python/test_run_logs.py assertion that the timing-report call receives the implement-pinned env

