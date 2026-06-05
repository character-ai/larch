### [Plan Review] FINDING_3

### FINDING_3: Planned missing-restored-artifact case duplicates late-step test
- **Reviewer(s)**: Cursor-dyn-test-line-accuracy
- **Severity**: nit
- **Concern**: A planned `missing-restored-artifact` case overlaps the existing late-step test at lines 750–752. That block already asserts `ERROR=missing-restored-artifact` but not `LOAD_OK=false` or marker retention; adding a second parallel block would duplicate setup without new coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-line-accuracy: Extend 750-752 with LOAD_OK=false and marker-present assertions instead of adding a parallel case

