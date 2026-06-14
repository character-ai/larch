### OOS_1:
- **Description**: `review_status: panel-skipped` is parsed and refused by publish/preflight, but no Step 3 or publish writer in the plan ever emits `panel-skipped`.. Scenario: Operators hitting `panel-skipped` refusal have no documented producer; the token is dead surface area unless a future path adds it.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/plan_provenance.py:86-87
- **Phase**: design

### OOS_2:
- **Description**: Harness file is listed under `### UPDATED:` but `plan_provenance.py` is a new module with no existing test file.. Scenario: Implementer may skip creating the harness or search for a nonexistent file.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_plan_provenance.py
- **Phase**: design

