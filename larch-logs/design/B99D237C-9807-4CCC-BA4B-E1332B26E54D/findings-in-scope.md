### FINDING_1: Resume branch validation must retain main/master guard
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The resume branch validation can allow `main`/`master` on a non-forked checkout if the state branch matches the current branch, bypassing the existing bash safety guard and risking CI/postmerge on the base branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: When adding _resume_plan branch validation, reuse the bash guard semantics: reject main/master for non-forked and non-forked_target resumes even when the current branch matches

### FINDING_2: Resume must hydrate durable state flags before routing
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: Resume routing reads only partial state and can rely on stale argv/context for durable mode flags, causing repo-unavailable/forked/merge/draft state to be misclassified, GitHub calls to run when they should be skipped, CI to run for `merge=false`, or state writes to overwrite durable flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Read and hydrate or validate REPO_UNAVAILABLE, FORKED_TARGET, MERGE, and DRAFT from state before gh-skip classification, PR-only exits, and non-fresh state writes
  - From Codex-Pragmatic: Read these durable keys from ship-pr-state.sh when a state file exists and use them for gh-skip classification, base_remote, PR-only exits, monitor, and state writes; fall back to ctx only when the state key is absent or invalid

### FINDING_3: Non-fresh GitHub resume routes must verify PR head matches checkout
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: MERGED or done resume routing can trust a stale/corrupt `PR_NUMBER` for a different PR and proceed to postmerge/done without verifying that the PR head matches the validated current branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Require successful gh.pr_view head_ref to match the validated branch before any normal-repo non-fresh route, including MERGED and done; treat wrong head as fresh or safe-refuse and cover it in the wrong-head test.

### FINDING_4: Fresh fallback after state validation can use stale ctx.branch
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: When state exists and the checkout branch validates, fallback-to-fresh paths after invalid/closed/wrong-head PR identity can still use stale `ctx.branch`, causing state rewrites or PR creation/update for the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: For any state-present resume whose checkout validates, build a working context with branch and branch_name set to the validated resume branch before the first fresh-path state write, postbump, title, and ensure_pr call; clear stale PR fields when routing fresh
  - From Codex-Requirements: Hydrate the state-present fresh context with the validated current branch while clearing stale PR identity and zeroing counters; add a closed/wrong-head fresh-fallback test with stale ctx.branch.

### FINDING_5: Repo-unavailable local-only resume needs PR identity exemption
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: A strict valid PR identity requirement conflicts with repo-unavailable PR-only resumes, where state may legitimately contain blank or zero `PR_NUMBER`, potentially forcing fresh checks/postbump instead of the intended local-only PR-only resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Explicitly exempt repo_unavailable local-only resume from the PR identity requirement, allowing pr_number=None/pr_url="" for the PR-only OK path; keep strict identity for routes that need a real PR and test blank/0 PR_NUMBER repo_unavailable resume.
