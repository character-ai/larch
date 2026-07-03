## Goal
Implement issue #6153: [IMPLEMENTING] [BUG] /analyze-bugs report masks deep verdicts behind mechanical NEEDS_DEEP.

## Implementation Plan
[BUG] /analyze-bugs report masks deep verdicts behind mechanical NEEDS_DEEP

## Summary

The Stage 3 report of /analyze-bugs shows NEEDS_DEEP for bugs that already have ingested deep verdicts. `_final_verdict` in `python/larch/issue/analyze_bugs.py` returns `bundle.mechanical_verdict` before consulting the ledger record. Bundles routed to deep verification carry `mechanical_verdict="NEEDS_DEEP"`, so the deep-verdict branch is unreachable for exactly the bugs deep verification covers.

## Observed

Run: `/analyze-bugs -n 5 --deep-model fable` on larch v52.3.1, main at 26b74fe1d (2026-07-03). Run dir: `~/.cache/larch/analyze-bugs/character-ai-larch/runs/1783104313`.

- The deep verifier returned CONFIRMED_FIXED for #5507 and #5508.
- Ingest accepted both rows (`INGEST_ACCEPTED=2`). The ledger rows hold `deep_verdict=CONFIRMED_FIXED` with `stages_complete=["deep"]`.
- The rendered report still shows both issues as NEEDS_DEEP with the mechanical reason "no exact Fixes reference". The counts table shows `Confirmed or likely fixed: 0` and `Needs deep: 2`.

## Root cause

In `_final_verdict` (python/larch/issue/analyze_bugs.py):

```python
if bundle.mechanical_verdict:
    return bundle.mechanical_verdict, bundle.mechanical_reason, (), False
if record and record.deep_verdict:
    return record.deep_verdict, record.deep_reason, (), record.sampled
```

Mechanical NEEDS_DEEP is a routing signal, not a terminal verdict. The first branch swallows it anyway.

Supporting evidence: later in the same function, a second `if bundle.mechanical_verdict:` fallback repeats the first condition and is unreachable dead code. The first branch was likely meant to short-circuit only for terminal mechanical verdicts (NOT_FIXED, WONTFIX).

## Impact

- Deep verification results never reach the report, `report.md`, or the counts table. Deep Task spend is invisible at report time.
- Worse: a deep verdict of NOT_FIXED, INCOMPLETE, or REGRESSED on a NEEDS_DEEP bundle is also masked. Those verdicts drive TERMINAL_FOLLOWUP_VERDICTS, so the workflow can silently skip follow-up filing for real regressions.

## Suggested fix

Short-circuit only on terminal mechanical verdicts:

```python
if bundle.mechanical_verdict and bundle.mechanical_verdict != "NEEDS_DEEP":
    return bundle.mechanical_verdict, bundle.mechanical_reason, (), False
```

The later fallback then becomes reachable and keeps the current behavior for NEEDS_DEEP bundles that have no ledger record.

Preserve: mechanical NOT_FIXED must keep overriding a stale deep verdict. `test_render_report_overrides_stale_deep_and_writes_follow_up` pins that behavior.

## Test gap

`python/tests/issue/test_analyze_bugs.py` covers mechanical NOT_FIXED plus a stale deep verdict, and an empty mechanical verdict plus a deep verdict. No test covers mechanical NEEDS_DEEP plus a fresh deep verdict, the exact shape every deep-verified bug has in production. Add a report test asserting the deep verdict surfaces in the issue row and the counts table.

## Test plan
(no test plan section in plan-file)
