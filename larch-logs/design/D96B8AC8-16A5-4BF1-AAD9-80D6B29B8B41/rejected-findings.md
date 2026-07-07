### [Plan Review] FINDING_2

### FINDING_2: Stub proc.run on the resume path in Test 2
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Test 2 can stop being isolated if the resume path reaches `_refresh_resume_source_env()` and invokes the real `session write-design-env` command. That introduces host-environment side effects and can fail before the ISSUE_NUMBER recovery is actually exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the same `design_step0.proc.run` monkeypatch used by the nearby resume tests, and keep the fake route result on the resume path.

