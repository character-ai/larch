### OOS_1: Unavailable receipt JSON may duplicate outcome detail after propagation
- **Description**: Unavailable receipt JSON may duplicate outcome detail after propagation. Scenario: Once outcome sidecars carry sanitized `detail` and route-exit surfaces `ASSESSMENT_UNAVAILABLE_DETAIL`, the per-kind unavailable receipt repeats the same diagnostic without a committed-log consumer.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/architectural_assessment.py:674-685
- **Phase**: design



