### FINDING_1: /implement diagram failure logs still copied into committed run logs
- **Reviewer(s)**: Cursor-Arch, Codex-Generic
- **Severity**: important
- **Concern**: The plan targets diagram chat/run-log exclusion for `/design` but does not stop `/implement` diagram failure captures from landing in committed run logs. `_copy_diagram_failure_log` in `python/step_7a.py` still copies `code-flow-diagram.failure.log` into `larch-logs/implement/<RUN_ID>/`, and `python/pr_body.py` writes generator stdout/stderr (which may contain partial Mermaid) to that failure log on non-zero exit. `python/test_step_7a.py` asserts the copy. This violates the scope requirement that diagram content not be flushed to run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Stop copying diagram failure logs into the committed run-log tree (or exclude `code-flow-diagram*.md` / `code-flow-section.md` / `code-flow-diagram.failure.log` from publish); update `python/step_7a.py` and `python/test_step_7a.py`, not only `skills/implement/SKILL.md` NEVER prose
  - From Codex-Generic: Extend the plan to update python/step_7a.py to stop copying code-flow-diagram.failure.log into larch-logs, or replace it with a bounded non-diagram status sidecar, and update python/test_step_7a.py to assert the log copy is absent


### FINDING_2: Design sanitizer failure log not excluded from committed run logs
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds `architecture-diagram-generation.failure.log` to top-level publish exclusions in `python/design_log_publish_flow.py` but not `architecture-diagram-sanitizer.failure.log`. `skills/design/scripts/design-step3b-sanitize.sh` still writes full sanitizer output to that basename on fail-closed paths, and it is not matched by `_PUBLISH_EXCLUDE_SUFFIXES`. Sanitizer rejection after the relocated Step 5b.5 can still commit Mermaid-bearing failure captures to design run logs despite the no-diagram-in-logs goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Exclude architecture-diagram-sanitizer.failure.log in design_log_publish_flow.py (or retire the file once design_diagram_log bounded sidecars replace it); assert exclusion in python/test_design_log_publish_flow.py
  - From Cursor-Pragmatic: Add architecture-diagram-sanitizer.failure.log to _PUBLISH_EXCLUDE_TOPLEVEL_NAMES (and cross-test in python/test_design_log_publish_flow.py); wire sanitize append-failure to design_diagram_log bounded sidecar instead of the raw sanitizer log


