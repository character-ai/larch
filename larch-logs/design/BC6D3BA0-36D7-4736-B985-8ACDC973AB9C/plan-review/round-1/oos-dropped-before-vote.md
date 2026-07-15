### OOS_9: Path validation helper already exists; plan does not reference it
- **Description**: Path validation helper already exists; plan does not reference it. Scenario: `_valid_repo_relative_path` at 3365-3377 already enforces bounded in-repo paths for sweep findings. A parallel validator risks drift.
- **Reviewer**: Cursor-dyn-Runtime Evidence Integrity
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/issue/analyze_bugs.py:3365-3377
- **Phase**: design

### OOS_10: Evidence tail cap constant already exists
- **Description**: Evidence tail cap constant already exists. Scenario: `SCAN_REASON_CAP` (500) and `_scan_failure_reason` at 851 bound failure text for scans. The plan asks for bounded single-line tails without pointing at this existing cap.
- **Reviewer**: Cursor-dyn-Runtime Evidence Integrity
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/issue/analyze_bugs.py:851-851
- **Phase**: design

