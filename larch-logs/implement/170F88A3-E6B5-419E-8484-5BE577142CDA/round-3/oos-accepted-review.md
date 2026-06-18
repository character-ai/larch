### OOS_1: risk-integration: python/test_preflight.py:62-84
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] The non-emergency missing-plan refusal path (BLOCK_PRESENT=false without --emergency) is not tested after retiring scripts/test-implement-preflight.sh. A regression that skips the exit-2 branch at python/preflight.py:385-388 could let /implement proceed without a vetted larch:plan on the default path. Add a stubbed test expecting rc==2, the no larch:plan refusal message, and no PLAN_PATH= in stdout.
- **Suggested revision**: Address the concern above.


