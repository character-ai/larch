### [Plan Review] FINDING_3

### FINDING_3: test_timing.py plan bullet incomplete for new task kinds
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The `test_timing.py` update is an incomplete sentence and does not name the new task kinds. The plan says to extend accepted-kind tests and assert no unknown task-kind warning, but the parameterized kinds line is blank. Without `claude-relevant-checks` and `claude-lint-fix` in `test_timing.py`, allow-list drift can ship and every new wrapper call will emit stderr warning noise despite `timing.py` being updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Complete the bullet: parametrize claude-relevant-checks and claude-lint-fix in a test_timing_record_vendor_task_accepts_* test mirroring the existing review-fix parametrized pattern, and assert unknown task-kind is absent.
```

**Merge summary**

| Merged ID | Source inputs | Rationale |
|-----------|---------------|-----------|
| `FINDING_1` | Cursor-Arch #1 + Cursor-Innovation #5 | Same fix: timing helper must use `Runner.run`, not subprocess-only recording |
| `FINDING_2` | Cursor-Arch #2 + Cursor-Innovation #4 | Same fix: `run_lint_fix` needs the full timing envelope mirrored from `run_relevant_checks` |
| `FINDING_3` | Cursor-Arch #3 only | Distinct surface: `test_timing.py` allow-list coverage, separate from helper/wrapper specs |

