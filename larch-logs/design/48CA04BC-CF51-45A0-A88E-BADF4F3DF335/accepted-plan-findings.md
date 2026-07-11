### FINDING_6: Tier-A dedup performs GitHub work before authorization gate
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: `file_tier_a_after_compose` calls `dedup_tier_a_report_main` with only `helper_common()` args. `dedup_tier_a_report` then runs `gh repo view` and a `--dedup-only` helper lookup before any mutation-context argument exists. Unauthorized design failure-report fixtures that reach the dedup branch can still hit `gh` even when create filing is gated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Name `dedup_tier_a_report` in the plan; require mutation-context validation at its entry before repo resolution or helper invocation; pass `$DESIGN_TMPDIR/source-env.sh` (and the implement equivalent) through the dedup argv; assert zero `gh` calls on refusal in `test_design_lifecycle.py` / `test_stall_recovery.py`.


### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: Plan Goal section
- **Concern**: [SCOPE-REDUCTION] Goal claims coverage of every known issue-mutation path while firm files omit several live surfaces. Scenario: Binding issue acceptance only requires filing choke-point refusal plus reporter regression; keeping the broad Goal without `tracking_issue.py`, `decompose.py` close-original, or `clarify.py` updates either over-scopes the 865-line plan or leaves a false completeness claim
- **Proposed resolution**: Narrow the Goal to the binding acceptance surfaces explicitly listed in approach steps 3-9, or add firm `### UPDATED:` rows for each remaining live mutation module before claiming full-path coverage


