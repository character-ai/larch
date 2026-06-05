### [Plan Review] FINDING_8

### FINDING_8: Resume FSM ignores PHASE-based mid-CI entry
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Concern**: The three-way fresh/open-pr/merged resume abstraction does not dispatch from persisted `PHASE` like bash, so resumes from `ci-initial` or `ci-merge` can rerun pr-create/OOS/materialize gates instead of jumping directly back into the appropriate CI phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash-parity: goto_rebase and other mid-CI re-invokes can diverge (extra gh/push churn, OOS re-prompts, wrong ci-merge timing). Teach _resume_plan to read PHASE (and CI_PASSED) from state: done→no-op OK; postmerge→merged; ci-initial/ci-merge→open-pr entry at CI with pr-create skipped; only lower phases run pr-create.
  - From Cursor-dyn-bash-parity: The proposed abstraction is a different FSM; parity gaps above are structural, not accidental omissions in tests. Either narrow the parity claim to counter persistence + skip checks/postbump only, or add PHASE-aware entry inside _resume_plan (minimum change: read PHASE/CI_PASSED, keep counter restore).


### [Plan Review] FINDING_10

### FINDING_10: Repo-unavailable resumes do not mirror bash CI phase skips
- **Reviewer(s)**: Cursor-dyn-bash-parity, Codex-dyn-bash-parity
- **Severity**: important
- **Concern**: Repo-unavailable or missing-PR-number resumes can be routed into fresh checks/pr-create or the CI monitor loop, while bash advances/synthesizes phase transitions without polling or gh access.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash-parity: Fork/OSS PR-only resume paths poll or fix CI against an unreachable repo instead of phase-skipping like bash. Mirror bash: when ctx.repo_unavailable (or empty PR_NUMBER), do not call ci_monitor.monitor; advance/synthesize the same phase transitions bash uses.
  - From Codex-dyn-bash-parity: For repo_unavailable, honor bash's state PHASE skip semantics before PR identity, or exclude repo_unavailable from open-pr resume and preserve the current local-only flow. Never let ensure_pr overwrite a restored PR identity with 0.


### [Plan Review] FINDING_11

### FINDING_11: Merge/draft/fork short-circuits are missing on open-PR resume
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Concern**: Open-PR resume can enter CI merge polling or merge attempts even when bash would short-circuit for `MERGE!=true`, draft PRs, forked targets, or repo-unavailable state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash-parity: Resume after a forked-target or merge=false session can enter merge polling/merge attempts that bash would bypass at ci-merge. After pr-create hydration, apply the same merge/draft/forked_target/repo_unavailable early-return gates as today’s fresh path before entering the loop.


