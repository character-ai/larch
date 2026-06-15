### OOS_1: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 4. **risk-integration** `python/agents.py:2280-2290` vs `python/agents.py:3536-3550` — `_review_run_with_retries` increments `auth_attempt` on the unclassified bonus retry; `_run_external_agent_with_auth_retries` does not. A sequence of unclassified-then-auth with `LARCH_EXTERNAL_AUTH_RETRIES=2` can consume the auth budget in the review path without a dedicated auth retry test. **Why out of scope:** bundled #4341 change, not the rebase plan; existing tests pin the `LARCH_EXTERNAL_AUTH_RETRIES=1` two-call contract.
- **Suggested revision**: Address the concern above.


