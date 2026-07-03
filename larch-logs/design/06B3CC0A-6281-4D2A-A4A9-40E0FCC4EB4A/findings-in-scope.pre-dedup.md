### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_review_and_fix.py
- **Concern**: Shim intercept must match the absolute cli.py argv path, not a standalone python/cli.py token. Scenario: Wrappers invoke python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5; argv[1] is an absolute path. A shim or assertion that looks for a literal python/cli.py token will never intercept or will delegate to the real review-and-fix loop, so the test can hang, flake, or miss DIFFICULTY_OVERRIDE forwarding.
- **Proposed resolution**: Match review-and-fix step5 when argv has review-and-fix at index 1 and step5 at index 2 after the cli.py path (or when argv[1].endswith("python/cli.py")), then assert flags on that captured slice only.



### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-resume.sh:115-146
- **Concern**: Resume-wrapper harness must clear STEP5_HANDOFF_READY_TO_COMMIT from the subprocess env. Scenario: step-5-resume.sh routes to implement commit-route when STEP5_HANDOFF_READY_TO_COMMIT is true even without --ready-to-commit. A polluted parent env can skip the review-and-fix argv path the test targets, so captured argv is empty and wrapper exit may be non-zero.
- **Proposed resolution**: test_implement_dispatch.py already delenv's this key; mirror that in the helper env (e.g. STEP5_HANDOFF_READY_TO_COMMIT=false or omit it) for every step-5-resume.sh invocation.



