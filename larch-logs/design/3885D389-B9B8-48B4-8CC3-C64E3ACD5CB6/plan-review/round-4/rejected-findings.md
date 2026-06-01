### [Plan Review] FINDING_1

### FINDING_1: Step 0 structure `awk` still enforces legacy bootstrap / `--resume-plan-tail` literals
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: After migrating bootstrap/resume to `implement-bootstrap-invoke.sh --mode initial` and `--mode resume`, Step 0 `awk` in `scripts/test-implement-structure.sh` (roughly lines 550–575) still fails on exit codes **10** and **13** by counting direct `implement-bootstrap.sh --up-to-phase coder` calls and exactly one `--resume-plan-tail` mention inside Step 0 bash blocks. A faithful SKILL.md refactor can have zero such literals while still being correct, so `make test-implement-structure` fails even when the wrapper migration matches the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Replace exit 10/13 with counts for `implement-bootstrap-invoke.sh --mode initial` and `--mode resume` as the plan’s awk retarget prose describes
  - From Cursor-Innovation: Replace exit 13 logic with pins for zero --resume-plan-tail / zero direct implement-bootstrap.sh in step:0 bash plus at least one --mode resume wrapper call

---


