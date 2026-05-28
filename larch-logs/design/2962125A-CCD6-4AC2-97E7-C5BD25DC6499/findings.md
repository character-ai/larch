### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-with-waterfall.sh:77-90
- **Concern**: The Item B-1 fixture assumes the cp stub can fail two reuse-copy targets, but the current stub supports one substring and fails only the first matching copy.. Scenario: The proposed PHASE2_RELAUNCH_COUNT=2 scenario will either produce only one relaunch or require unsupported ad hoc env setup.
- **Proposed resolution**: Revise the plan to include the tiny cp-stub change needed for exactly two planned copy failures, then use that explicit knob in the B-1 scenario.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:26-29,680-689
- **Concern**: `COMBINED_FALLBACK_COUNT` initialized to `"0"` breaks absent-KV fallback. Scenario: When panel stdout has `FALLBACK_COUNT>floor_half` but no `COMBINED_FALLBACK_COUNT` line, the guard treats `"0"` as numeric and leaves combined at 0; the loop’s redundant `(( COMBINED > floor_half ))` check never fires even if `DEGRADED_ROUND` were missing or false
- **Proposed resolution**: Initialize `COMBINED_FALLBACK_COUNT=""` (mirror `dispatch-plan-review-panel.sh` / `decompose-panel-dispatch.sh`) so the existing `''|*[!0-9]*)` guard defaults to `$FALLBACK_COUNT`

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-with-waterfall.sh:77-90,542-581
- **Concern**: Item B-1 fixture cannot drive two phase-2 relaunches in one group via “two `CP_STUB_FAIL_TARGET_CONTAINS`”. Scenario: The harness `cp` stub allows only one failing reuse per run (`n==0` exit 73, then `n>=1` succeeds); a single `CP_STUB_FAIL_TARGET_CONTAINS` cannot produce `PHASE2_RELAUNCH_COUNT=2`, so B-1 would fail or be “fixed” by weakening assertions
- **Proposed resolution**: Revise B-1 to induce two `reuse_slot_result` failures (e.g. second fall-through via deleted/stale reuse source, or a minimal stub change such as a second-fail budget); drop the plural “two TARGET_CONTAINS triggers” wording

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:518-522
- **Concern**: Zero-finding exit still hardcodes DEGRADED_PANEL=0. Scenario: The proposed final COMBINED_FALLBACK_COUNT comparison is bypassed when collection yields no findings, so a no-finding round with excessive phase-2 relaunches reports DEGRADED_PANEL=0
- **Proposed resolution**: Compute the panel degradation value before the zero-finding short-circuit or use DEGRADED_ROUND there instead of hardcoded 0

### FINDING_5:
- **Reviewer(s)**: Codex-Edge, Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-with-waterfall.sh:77-90
- **Concern**: Item B-1 needs two reuse-copy failures but the cp stub can only fail one matching copy. Scenario: The proposed PHASE2_RELAUNCH_COUNT=2 scenario cannot be expressed with the current single CP_STUB_FAIL_TARGET_CONTAINS plus one-shot counter behavior
- **Proposed resolution**: Extend the stub minimally to support two explicit fail target substrings or revise the fixture to include that stub change in the plan

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-with-waterfall.sh:77-90
- **Concern**: Item B-1 relies on two cp-failure triggers, but the existing cp stub supports only one target substring and only fails the first matching copy. Scenario: The planned PHASE2_RELAUNCH_COUNT=2 scenario cannot be expressed as written, so the new harness case will either pass with only one relaunch or require an unplanned stub change
- **Proposed resolution**: Add the minimum stub change to support a fail limit or two target substrings, then use it in the new scenario and assert the cp counter equals 2

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-with-waterfall.sh:77-90
- **Concern**: Item B-1 cannot be produced with the current cp stub. Scenario: The plan asks for two phase-2 reuse-copy failures, but the stub supports one CP_STUB_FAIL_TARGET_CONTAINS value and only fails the first matching copy, so the proposed scenario will not reach PHASE2_RELAUNCH_COUNT=2
- **Proposed resolution**: Update the plan to extend the cp stub minimally for this harness, such as a comma/newline list of target substrings or a fail-count setting, then assert the counter saw two failed reuse copies

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh:39-45
- **Concern**: Design-consumer validation is missing for Item A. Scenario: The plan updates three consumers to use COMBINED_FALLBACK_COUNT but leaves their harnesses effectively FALLBACK_COUNT-only, so a consumer could still compare FALLBACK_COUNT while the dispatcher emits the new KV and the tests would pass
- **Proposed resolution**: Add targeted assertions in the existing design harnesses with FALLBACK_COUNT=0 and COMBINED_FALLBACK_COUNT above half, covering dispatch-plan-review-panel, decompose-panel-dispatch, and plan-review-loop without adding new harness files

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-consumer-stub-completeness, Codex-dyn-consumer-stub-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:16-39,79; skills/design/scripts/test-dispatch-plan-review-panel.sh:39-45; skills/design/scripts/test-decompose-panel-dispatch.sh:56-60,218-222; skills/design/scripts/test-plan-review-loop.sh:42-68,73-108,112-117; Makefile:409-410,460-461,496-497
- **Concern**: Plan adds COMBINED_FALLBACK_COUNT parsing/comparison to the design consumers but leaves their consumer harness stubs out of the modification list; the current stubs synthesize only FALLBACK_COUNT, and the Makefile targets named conditionally in the plan do exist.. Scenario: The proposed defensive default from COMBINED_FALLBACK_COUNT to FALLBACK_COUNT would let make test-dispatch-plan-review-panel, make test-decompose-panel-dispatch, and make test-plan-review-loop pass while exercising only the compatibility fallback, so a regression from COMBINED_FALLBACK_COUNT back to FALLBACK_COUNT could avoid unit coverage.
- **Proposed resolution**: Add the affected harness files to the UPDATED list; update their dispatcher-output stubs to emit PHASE2_RELAUNCH_COUNT and COMBINED_FALLBACK_COUNT via W_STUB_* defaults, and add or adjust one degradation threshold case where FALLBACK_COUNT stays below half but COMBINED_FALLBACK_COUNT crosses it.
