### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step0.py:383-411,415-550
- **Concern**: Rehydrate the live resume env before routing and stdout emission, not only inside the post-route refresh.. Scenario: The plan only repairs `source-env.sh` after `design route` runs. On a resumed session whose launcher env still lacks `ISSUE_NUMBER`/`REPO`, the route subprocess and `_emit_step0_route_rows` can still see blanks, so the Step 0b stdout contract and resume path remain broken.
- **Proposed resolution**: Merge the recovered route-state values into `ctx.env` before building `route_cmd`, then reuse that merged mapping for `_emit_step0_route_rows` and `_refresh_resume_source_env`; add a resume test that asserts stdout includes non-empty `ISSUE_NUMBER` and `REPO`.

