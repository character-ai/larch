### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/step_7a.py:95-106
- **Concern**: Plan omits stopping implement diagram failure logs from landing in committed run logs. Scenario: Issue scope requires /implement diagrams stay off run logs; `_copy_diagram_failure_log` still copies `code-flow-diagram.failure.log` into `larch-logs/implement/<RUN_ID>/` and `test_step_7a.py` asserts that copy
- **Proposed resolution**: Stop copying diagram failure logs into the committed run-log tree (or exclude `code-flow-diagram*.md` / `code-flow-section.md` / `code-flow-diagram.failure.log` from publish); update `python/step_7a.py` and `python/test_step_7a.py`, not only `skills/implement/SKILL.md` NEVER prose



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_log_publish_flow.py:131-136
- **Concern**: Top-level publish exclusions add architecture-diagram-generation.failure.log but not architecture-diagram-sanitizer.failure.log; current design-step3b-sanitize.sh still writes full sanitizer stdout to that basename and it is not matched by _PUBLISH_EXCLUDE_SUFFIXES. Scenario: Sanitizer rejection after Step 5b.5 can still commit mermaid-bearing failure captures to design run logs despite the no-diagram-in-logs goal
- **Proposed resolution**: Exclude architecture-diagram-sanitizer.failure.log in design_log_publish_flow.py (or retire the file once design_diagram_log bounded sidecars replace it); assert exclusion in python/test_design_log_publish_flow.py



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-sanitize.sh:136
- **Concern**: Plan retargets sanitizer breadcrumbs and append-failure --site to 5b.5 but does not list updating mermaid sanitize --warnings-step still hardcoded to 3b. Scenario: Warnings/diagnostics and any consumer keyed on warnings-step stay tied to the pre-move Step 3b label after diagram work moves to Step 5b.5
- **Proposed resolution**: Add --warnings-step 5b.5 (or equivalent) to the design-step3b-sanitize.sh update list and pin it in scripts/test-design-structure.sh if needed



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_log_publish_flow.py:131-135
- **Concern**: Plan excludes architecture-diagram-generation.failure.log from committed design logs but not architecture-diagram-sanitizer.failure.log. Scenario: Sanitizer fail-closed paths still write full sanitizer output to architecture-diagram-sanitizer.failure.log (see skills/design/scripts/design-step3b-sanitize.sh:158); log publish can commit Mermaid-bearing captures, violating the issue no-run-log-diagram requirement
- **Proposed resolution**: Add architecture-diagram-sanitizer.failure.log to _PUBLISH_EXCLUDE_TOPLEVEL_NAMES (and cross-test in python/test_design_log_publish_flow.py); wire sanitize append-failure to design_diagram_log bounded sidecar instead of the raw sanitizer log



### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/step_7a.py:95-105,273-278; python/pr_body.py:708-716
- **Concern**: /implement failure-log copy still sends diagram-generation stdout/stderr into committed run logs. Scenario: If the code-flow generator exits non-zero after emitting partial Mermaid on stdout or stderr, pr_body.py writes that capture to code-flow-diagram.failure.log and step_7a.py copies it into larch-logs/implement/<run>/, violating the issue requirement that diagram content not be flushed to run logs
- **Proposed resolution**: Extend the plan to update python/step_7a.py to stop copying code-flow-diagram.failure.log into larch-logs, or replace it with a bounded non-diagram status sidecar, and update python/test_step_7a.py to assert the log copy is absent



