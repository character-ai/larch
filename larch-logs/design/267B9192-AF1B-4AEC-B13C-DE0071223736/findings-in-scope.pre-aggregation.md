### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: python/plan_review.py embedded skills/design/scripts/persist-retally-step3-env.sh:9-10,24-39; plan.txt:84-89
- **Concern**: persist-retally plan adds validate+quiet after argv checks but never says to remove the entry larch_quiet_init. Scenario: Decoded body sources lib-quiet.sh then calls larch_quiet_init at line 10 before DESIGN_TMPDIR is cleared (line 14) or bound from --design-tmpdir (line 26). _run_legacy inherits orchestrator DESIGN_TMPDIR in env; lib-quiet.sh prefers that directory for larch-quiet-*.log. Adding a second quiet init after checks without deleting line 10 leaves the security regression on the MAV retally path.
- **Proposed resolution**: Revise persist-retally bullets to mirror emit-plan: remove the top-level larch_quiet_init; after argv checks and DESIGN_TMPDIR assignment from --design-tmpdir, call session validate-design-tmpdir on that path, then larch_quiet_init once.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: python/plan_review.py embedded skills/design/scripts/persist-retally-step3-env.sh; python/plan_review.py embedded skills/design/scripts/record-plan-review-round-timing.sh; plan.txt:13-19,84-97
- **Concern**: Approach and per-script bullets for persist-retally and record-timing say add validate+quiet but never say remove the entry larch_quiet_init. Scenario: Decoded bodies source lib-quiet.sh and call larch_quiet_init near the top before argv binding or validate-design-tmpdir. _run_legacy inherits orchestrator DESIGN_TMPDIR. Following the add-only bullets leaves entry quiet in place, so larch-quiet-*.log can still be created under a stale disallowed directory before the new validate block runs. run-step3-review.sh explicitly says remove the top-level quiet init; these two scripts do not.
- **Proposed resolution**: Extend Approach: any embedded script with entry larch_quiet_init must remove it, not only scripts that already validate. Mirror run-step3/emit-plan bullets for persist-retally and record-timing: remove top-level larch_quiet_init; bind DESIGN_TMPDIR from --design-tmpdir; validate; then call larch_quiet_init once.

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: python/plan_review.py embedded skills/design/scripts/persist-retally-step3-env.sh:9-10; plan.txt:84-89
- **Concern**: persist-retally bullets add validate+quiet but never require removing the entry larch_quiet_init. Scenario: Decoded body sources lib-quiet.sh then calls larch_quiet_init at line 10 before DESIGN_TMPDIR is cleared or bound from --design-tmpdir. _run_legacy inherits orchestrator DESIGN_TMPDIR; lib-quiet.sh can create larch-quiet-*.log under a disallowed inherited directory before the planned late validate block runs.
- **Proposed resolution**: Mirror emit-plan/run-step3 wording: remove the top-level larch_quiet_init; after binding DESIGN_TMPDIR from --design-tmpdir, call session validate-design-tmpdir on that path, then call larch_quiet_init once.

### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_plan_review.py:20-41
- **Concern**: Proposed tests may add full retired script path literals. Scenario: The retired-script lint scans tracked files for full repo-relative paths from python/migrated-scripts.tsv. The nearby tests already split these names to avoid make lint failures. Following the plan literally for run-step3-review.sh and dispatcher paths can break make lint.
- **Proposed resolution**: Require the new tests to assemble all retired asset paths from tuple parts or split basenames, matching the existing test pattern. Do not write full repo-relative retired script paths in python/test_plan_review.py.

