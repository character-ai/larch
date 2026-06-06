### OOS_1:
- **Description**: Reader hardening (awk + python + gate doc + three test harnesses) is a third layer beyond the two production breakpoints (#3550). Scenario: Producer normalization plus emit-tally skip already canonicalize accepted output and stop the overwrite chain; layer 3 adds six-file touch surface without changing the review-core tally→emit path
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/oos.py:32-33; skills/implement/scripts/oos-non-security-block-count.awk:7-11
- **Phase**: design

