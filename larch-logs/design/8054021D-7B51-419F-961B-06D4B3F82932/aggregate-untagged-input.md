### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-Step2B5 Self Log
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:3662-3671
- **Concern**: Plan omits explicit LARCH_QUIET_DISABLE preservation when refactoring step2b5 capture. Scenario: An implementer replaces _capture_stdout without keeping the quiet-disable try/finally; emit_kv lines land on the quiet log fd instead of the StringIO buffer; Step 2b.5 orchestrator parsing loses PLAN_SIZE_STATUS and SIZE_TRIGGER KVs on rc=0 and rc=2
- **Proposed resolution**: Add an explicit plan requirement to preserve the existing LARCH_QUIET_DISABLE=1 try/finally around the in-process check_plan_size_main call; add a regression test that stdout capture still contains emit_kv output when parent quiet routing would otherwise be active
