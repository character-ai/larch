### OOS_4: decompose _emit_kv is already a thin bool-normalizing forward
- **Description**: decompose _emit_kv is already a thin bool-normalizing forward. Scenario: Deleting it adds churn without parser benefit
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/design/decompose.py:79-81
- **Phase**: design

### OOS_5: admission parent-issue sentinel scan is a small last-wins dict loop outside the plan
- **Description**: admission parent-issue sentinel scan is a small last-wins dict loop outside the plan. Scenario: Tracking sentinel reads are low traffic and can stay ad-hoc briefly
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/state/admission.py:109-114
- **Phase**: design

