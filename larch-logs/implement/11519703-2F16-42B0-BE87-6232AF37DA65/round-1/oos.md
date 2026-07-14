### FINDING_1: [OUT_OF_SCOPE] Era auto-boundary tests omit gh-present command failure
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Era auto-boundary tests cover missing gh but not gh-present command failure. Plan acceptance cites command failure coverage; only returncode 127 (missing executable) is exercised on the era path, so `gh_issue_view_unavailable` for a non-zero gh exit with resolved repo is unverified. Add a fake-gh fixture with resolved repo that exits non-zero and assert Reason: `gh_issue_view_unavailable` without Traceback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Repo resolution still uses ad-hoc git subprocess
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Repo resolution still uses ad-hoc git subprocess instead of `gh.resolve_repo`. Duplicate resolution logic remains; umbrella #7054 tracks unification separately. Repoint to `gh.resolve_repo` when #7054 lands; out of scope for this plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
