### OOS_1:
- **Description**: Parallel timing-ledger extraction in Python duplicates shell awk logic. Scenario: The approved outline requires progress to import `gantt` while keeping `--no-gantt` on the shell call, so row extraction will live in both `render-review-phase-detail.sh` and new `progress_report.py` helpers. Tests reduce drift risk but do not remove duplicate domain logic.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/progress_report.py:375-406
- **Phase**: design

