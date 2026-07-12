## Decision 1: Migration scope for test_closeout.py and test_final_report.py
- **Question**: Are test_closeout.py and test_final_report.py in-scope for migration in this piece?
- **Resolution**: Yes, migrate both.
- **Source**: user

## Decision 2: Import path for session.py helpers
- **Question**: How should test files outside tests/support/ import the new builders?
- **Resolution**: Re-export from test_support.py (flat module). Requires adding tests/__init__.py to enable from tests.support.session import ... inside test_support.py.
- **Source**: user
