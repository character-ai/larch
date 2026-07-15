### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:2305-2610
- **Concern**: RUNTIME promotion eligibility is undefined. Scenario: Plan text says a passing runtime run promotes an otherwise qualifying static verdict but never pins which verdicts qualify. A fix already judged NOT_FIXED, REGRESSED, or INCOMPLETE could still gain tier RUNTIME when pytest and a mapped harness pass, certifying a failed fix because runtime only checked commit-local tests.
- **Proposed resolution**: Pin promotion to the same fixed-family verdicts used elsewhere (CONFIRMED_FIXED, FIXED_CLEAR, FIXED_LIKELY). Absent or non-qualifying static verdicts keep their tier; runtime failure still downgrades to SUSPECT/RUNTIME.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:2606-2610
- **Concern**: Runtime overlay order conflicts with _final_verdict_with_tier edit site. Scenario: render_report applies DEEP_TRUNCATED after _final_verdict_with_tier today. Plan also says to update _final_verdict_with_tier for runtime while separately applying overlay after truncation. Runtime inside the helper still runs before the truncation block, so a runtime SUSPECT/RUNTIME row can be replaced by NEEDS_DEEP when the issue is deep-capped, undoing accepted FINDING_5.
- **Proposed resolution**: Keep base verdict selection in _final_verdict_with_tier without runtime. Apply DEEP_TRUNCATED next. Call a dedicated _apply_runtime_overlay only after that block in render_report. State explicitly that runtime overlay must not live inside _final_verdict_with_tier.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py
- **Concern**: HARNESS_MAP seed rows still imply a one-to-one dict. Scenario: FINDING_6 added concrete rows but lists skills/implement/ twice with different make targets. A dict[str, str] would silently keep only one harness for that prefix.
- **Proposed resolution**: Define HARNESS_MAP as an ordered tuple of (prefix, target) pairs per G-Cfg-1. Resolve every matching row, dedupe targets, and test the exact seed tuple shape.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:2327-2328
- **Concern**: Certifiable verdict set is not pinned for RUNTIME promotion and verified accounting. Scenario: `_verified_issue` today treats any non-`NEEDS_DEEP` row with a tier as verified. After runtime, a static `NOT_FIXED`/`UNVERIFIABLE` row could get tier `RUNTIME` on passing pytest/harness while keeping that verdict, then land in `verified_issues`, newly-verified deltas, and snapshots even though `_counts` never treats it as fixed.
- **Proposed resolution**: Pin one shared certifiable verdict set (at least `{FIXED_CLEAR, FIXED_LIKELY, CONFIRMED_FIXED}`) for both RUNTIME tier promotion and runtime-aware `_verified_issue`; add a negative test that passing runtime on `NOT_FIXED` does not promote or verify.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py
- **Concern**: HARNESS_MAP seed row maps anti-halt harness to the wrong path prefix. Scenario: The plan maps `test-implement-anti-halt` to `skills/implement/`, but the harness script is `scripts/test-implement-anti-halt.sh`. A fix that only touches that script matches `scripts/` and runs `test-lint-bash32`, not the halt-rate harness the feature scope names.
- **Proposed resolution**: Add an explicit `scripts/test-implement-anti-halt.sh` (or `scripts/test-implement-anti-halt`) → `test-implement-anti-halt` seed row, or otherwise ensure scripts-only anti-halt edits resolve that make target; extend harness-map tests for this path.



