### [Plan Review] FINDING_4

### FINDING_4: Fresh fallback after state validation can use stale ctx.branch
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: When state exists and the checkout branch validates, fallback-to-fresh paths after invalid/closed/wrong-head PR identity can still use stale `ctx.branch`, causing state rewrites or PR creation/update for the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: For any state-present resume whose checkout validates, build a working context with branch and branch_name set to the validated resume branch before the first fresh-path state write, postbump, title, and ensure_pr call; clear stale PR fields when routing fresh
  - From Codex-Requirements: Hydrate the state-present fresh context with the validated current branch while clearing stale PR identity and zeroing counters; add a closed/wrong-head fresh-fallback test with stale ctx.branch.


