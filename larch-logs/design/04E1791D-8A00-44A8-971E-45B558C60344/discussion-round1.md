## Decision 1: Item scope
- **Question**: Which of issue #4756's 10 items should the replacement plan cover?
- **Resolution**: All 10 items. Fix the confirmed defects (1 probe-timeout retry, 2 bounded diagnostic reads, 3 Cursor keychain mutex, 10 panel-stderr redaction); conditionally handle the verify-items (4 /research lane routing, 6 collector stderr-tail resolver, 7 implement/review failure-source parity) by pinning a concrete gap and fixing only that, else closing as no-defect with recorded working-tree evidence; add pytest coverage (8, 9); sync item-5 docs.
- **Source**: user

## Decision 2: Default probe behavior preserved
- **Question**: Should default probe behavior and health-gate latency stay unchanged?
- **Resolution**: Preserve all current defaults. The new timeout-retry budget defaults to 0 (opt-in only). Health-gate latency stays unchanged. Auth, transient (`rc == 1`), and timeout retry budgets stay independent.
- **Source**: user

## Decision 3: Item 3 fix is Python-only
- **Question**: Should the Cursor keychain mutex fix touch the retired Bash surface `scripts/lib-cursor-auth.sh`?
- **Resolution**: No. That surface is retired (listed in `python/migrated-scripts.tsv`); the fix lives in `python/agents.py` only. Do not edit retired Bash launcher surfaces. Verify retirement at drafting.
- **Source**: issue

## Decision 4: Conditional verify-items close-out
- **Question**: How should items flagged "re-derive / may be no-defect / may drop" (4, 6, 7) be handled?
- **Resolution**: Keep them conditional. Inspect the cited symbols at drafting; fix only where a concrete gap remains; otherwise record working-tree evidence and close as no-defect (Item 4 may be dropped if `/research` already keys on binary presence with per-lane fallback).
- **Source**: user
