# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Verbal gap-fill happens too early
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-resume-env
- **Severity**: major
- **Concern**: Route-state gap-fill runs before the verbal guard, so a reused `DESIGN_TMPDIR` can inject a stale `ISSUE_NUMBER` into a fresh verbal `/design` run and let routing proceed when it should fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Run verbal guard before gap-fill, or skip gap-fill when kind==verbal; add test with stale route-state.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Skip route-state gap-fill for verbal invocations or run the verbal guard before gap-fill; add a regression test with stale route-state plus POSITIONAL_KIND=verbal.
  - From cursor-specialist-testing: Skip route-state gap-fill for verbal invocations until after the verbal ISSUE_NUMBER guard, or restrict gap-fill to resume@ paths; add a test with stale route-state plus POSITIONAL_KIND=verbal.
  - From codex-specialist-testing: Restrict recovery to resume@ paths or move the verbal guard before recovery, and add a stale-sidecar verbal regression test.
  - From dyn-dyn-resume-env: Run the verbal precondition first, or skip route-state gap-fill for ISSUE_NUMBER/REPO when POSITIONAL_KIND=verbal.


