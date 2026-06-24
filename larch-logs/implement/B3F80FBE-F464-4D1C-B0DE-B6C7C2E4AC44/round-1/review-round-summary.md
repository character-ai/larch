# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Inconsistent bootstrap-completion predicates block valid paths and allow pre-Step-0 edits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: NEVER #21, Preflight item 6, and the Step 0 pre-fence gate use different bootstrap-completion predicates (`BOOTSTRAP_NEXT=step2` vs “bootstrap completes” / “before this fence returns”). Bootstrap can return `BOOTSTRAP_NEXT=rebase-routing` (conflict resolution requires repo edits) or `BOOTSTRAP_NEXT=dirty-recovery` (exit 0 after the Step 0 fence) without ever emitting `step2`. On `rebase-routing`, NEVER #21 blocks conflict-resolution edits until a `step2` token that never arrives. On `dirty-recovery`, the orchestrator can treat bootstrap as completed and edit on `main` without a feature branch. Unify all guard surfaces on one completion predicate (or explicitly carve out allowed paths such as rebase-routing conflict resolution).
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_3: NEVER #21 forbids stale-notice path that Preflight item 6 requires
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Preflight item 6 requires composing `$PREFLIGHT_TMPDIR/stale-notice.md` and posting `gh issue comment` when staleness is detected. NEVER #21 read literally forbids Write and repo-mutating Bash in that window with no carve-out for `$PREFLIGHT_TMPDIR` or the stale-notice comment path. Carve out `$PREFLIGHT_TMPDIR` writes and the stale-notice `gh issue comment`; forbid only git working-tree mutations.
- **Suggested revisions (informational for voters; coder decides)**:


