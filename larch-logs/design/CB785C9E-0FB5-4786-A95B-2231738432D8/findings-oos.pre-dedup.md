### OOS_1:
- **Description**: LC_ALL=C parity not called out in classify_diff plan. Scenario: Bash classify-diff-mode.sh sets LC_ALL=C before path matching; the plan does not mention locale pinning for the Python port. On case-variant paths, mode routing could diverge from bash on some hosts.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/review_dispatch.py (proposed)
- **Phase**: design

### OOS_2:
- **Description**: Separate classify_diff() library API is extra surface versus CLI-only. Scenario: The in-process API is justified for rendering.py, but a CLI-only port with subprocess from rendering would be a smaller library surface. Not required for this slice to ship.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:35-44
- **Phase**: design

