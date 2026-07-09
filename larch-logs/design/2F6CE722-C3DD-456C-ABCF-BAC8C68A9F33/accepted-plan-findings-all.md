### FINDING_3: Fail closed on stale disposition recompute failures
- **Reviewer(s)**: Codex-Arch, Cursor-dyn-Scope Gate Security, Codex-dyn-Scope Gate Security
- **Severity**: major
- **Concern**: Advisory fallback still bypasses stale scope-disposition records when recompute cannot run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: If scope-disposition.json exists, fail closed when recompute cannot prove the current plan. Do not return the advisory success path unless no disposition record is present.
  - From Cursor-dyn-Scope Gate Security: Tighten validate_disposition_for_ship or the new gate helper: when relevance artifacts exist and recompute cannot run (missing/unreadable plan.txt), fail closed even if persisted coverage marks disposition_required=false; narrow the planned advisory test to cases where recompute succeeds or plan.txt is readable.
  - From Codex-dyn-Scope Gate Security: Change the mutation gate to block on any gate-relevant recompute failure. Do not downgrade to advisory solely because persisted coverage was non-required. Raise NeedsUserInput for the stale or missing-plan case instead.


### FINDING_7: Treat manifest-only tmpdirs as in-scope
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Gate relevance ignores the resolved manifest, so a tmpdir with only `manifest.json` can skip validation even when disposition is still required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Include manifest presence or manifest-derived todo state in the relevance check, or call the validator whenever the manifest is present and fail closed on required disposition.


### FINDING_10: Handle `NeedsUserInput` before the broad `Exception` handler
- **Reviewer(s)**: Cursor-dyn-Scope Gate Security, Codex-dyn-Scope Gate Security
- **Severity**: major
- **Concern**: `create_main` still downgrades a scope-disposition refusal to generic `PR_STATUS=error` instead of the required needs-user route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Scope Gate Security: Add an explicit except NeedsUserInput handler before the broad except in create_main (and assert in test_pr.py) that emits the same KVs as ship pre-driver and returns config.EXIT_NEEDS_USER_INPUT without calling gh or git push.
  - From Codex-dyn-Scope Gate Security: Add an explicit except NeedsUserInput block before the broad handler. Emit needs_user_reason=scope-disposition, NEXT_ACTION=halt-scope-disposition, return config.EXIT_NEEDS_USER_INPUT, and leave the generic catch for unexpected errors only.


