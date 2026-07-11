### FINDING_1: Update fence-shape tests for the adapter-only Step 8 flow
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The plan updates plan/fence counts but does not remove legacy compose-write ordering assertions. The harness may still require per-kind compose writers and a guidelines-only relaunch, causing the approved adapter-only Step 8 flow to fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the `scripts/test-implement-fence-shape.sh` plan item to replace those slices with adapter-first checks: one `step-8-assessment.sh` launcher through `implement-run-$PPID.sh`, no prompt-side assessment start/wait pair, and exactly one post-validation `step-8-ship.sh` relaunch


