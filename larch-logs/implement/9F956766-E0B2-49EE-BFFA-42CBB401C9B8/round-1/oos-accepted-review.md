### OOS_1: [OUT_OF_SCOPE] risk-integration — no runtime harness for stale `LARCH_TOKEN_SESSION_ID` with empty/missing `session_id` (`scripts/test-sessionstart-health.sh`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Neither SessionStart nor Stop has a runtime harness case that exports a stale `LARCH_TOKEN_SESSION_ID`, invokes the hook with an empty/missing `session_id`, and verifies the resolver child sees a cleared env. Coverage is pattern-matching plus Python unit tests. A dedicated hook integration test would guard the exact stale-inheritance bug; out of scope here because the plan relied on mirroring the SessionStart pattern and existing static checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: A dedicated hook integration test would guard the exact stale-inheritance bug; out of scope here because the plan relied on mirroring the SessionStart pattern and existing static checks.


