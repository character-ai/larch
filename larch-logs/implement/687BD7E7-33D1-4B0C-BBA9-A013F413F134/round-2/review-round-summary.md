# Review Round 2

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Final summary post-fence prose omits WAIT-when-absent branch
- **Reviewer(s)**: dyn-dyn-design-wait-contracts-output.txt
- **Severity**: important
- **Concern**: At `skills/design/SKILL.md:307-315`, the pre-fence Parameters `extra guards` correctly inlines `` `WAIT` when absent is expected `` and the yield branch, but the retained post-fence paragraph at line 315 still duplicates premature-notification recovery without that clause (it stops at “may confirm durable completion” and empty-output no-probe). A literal orchestrator that treats the nearer post-fence text as authoritative can probe `.completed/step-final-summary`, get `WAIT`, and advance or re-parse markers instead of yielding until the terminal sentinel exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-design-wait-contracts-output.txt: Collapse line 315 to the plan-allowed one-line `Wait for <task-notification> before…` summary, or extend it with the same `` `WAIT` when absent is expected `` / yield-without-`ps`-polling branch from line 307 and drop the duplicated probe wording now owned by `skills/shared/design-background-wait.md`.


