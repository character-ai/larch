# Review Round 1

- Mode: `diff`
- 1 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: no-em-dash regression test missing for run summaries
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: The renderer updates still lack the plan-required regression test that renders both implement and design summaries and asserts the run-summary block never contains —, so a future renderer regression could slip past the current positive substring checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add one focused test that exercises both summaries through the existing helpers/CLIs and fails if — appears anywhere in the emitted run-summary block.
  - From cursor-specialist-testing: Add parametrized tests on pr_body.render_run_summary (implement + design) asserting "\u2014" not in the sentinel-bounded block.


