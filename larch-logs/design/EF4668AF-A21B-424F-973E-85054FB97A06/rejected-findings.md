### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:662-705
- **Concern**: `--straggler-cutoff` applies to phase2/phase3 because `_collect_phase` passes the same `opts` to every `_reap_phase` call; straggler-dropped slots skip `failed` and never reach phase3. Scenario: `/design` plan-review keeps fallback active. When several phase1 slots fail and phase2 launches ≥2 alternate-tool fallbacks, a slow phase2 peer can be SIGTERM'd as `straggler-dropped` instead of failing into phase3 Claude. That breaks acceptance "Genuine crashes/empty outputs still fall back as today" and Round 1 intent (disable fallback only for timed-out original panel stragglers, not for fallback-chain slots)
- **Proposed resolution**: Pass a phase discriminator into `_collect_phase`/`_reap_phase` (e.g. `enable_straggler_cutoff=(opts.straggler_cutoff and phase==1)`) so only the initial parallel reviewer launch is subject to the adaptive deadline; keep phase2/phase3 on today's wait-to-outcome behavior. Add a pytest where phase1 failure triggers phase2 and a delayed fallback is not cut before phase3 can launch




### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agent_waterfall.py:736-773
- **Concern**: Observability emits a second `WARN=` for stragglers but does not define coexistence with the existing `WARN=cost-fallback-exceeded-threshold`; `_kv_parse` keeps only the last duplicate key. Scenario: When `/design` drops stragglers and `COMBINED_FALLBACK_COUNT` exceeds the cost threshold in the same dispatch, only one `WARN` survives parsing. Operators or harnesses that read `kv["WARN"]` may miss straggler drops or cost-threshold advisory despite `STRAGGLER_DROPPED_COUNT`
- **Proposed resolution**: Either combine both tokens in one `WARN` value (space-separated) with a test for dual-fire, or document that `WARN` is not authoritative when stragglers drop and require scanning stdout/`STRAGGLER_DROPPED_COUNT` plus `COMBINED_FALLBACK_COUNT`




### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:412-567
- **Concern**: Half-mark anchor treats rc0 plus non-empty output as substantive success. Scenario: The cutoff can arm on malformed reviewer text, NOT_SUBSTANTIVE output, or STATUS=cap_hit before collector-side validation, then kill remaining reviewers and skip fallback even though the anchor outputs are later rejected
- **Proposed resolution**: Make the anchor predicate use the same collector or format-gate validation that accepts a slot, or defer arming until a completed output is collector-validated; add the malformed rc0 non-empty case to the planned tests




### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agent_waterfall.py:736-780
- **Concern**: Second WARN= KV overwrites cost-fallback warning. Scenario: Plan emits WARN=reviewer-straggler-dropped after the existing WARN=cost-fallback-exceeded-threshold, but stdout KV parsing (_kv_parse in python/review_pipeline.py:92-100) keeps only one WARN= line. When phase-3 fallback volume and a straggler cut both occur, operators lose the cost-fallback signal the plan claims is preserved.
- **Proposed resolution**: Merge warnings into one emit: build a single WARN value (space-separated tokens) or add a dedicated STRAGGLER_WARN key; extend python/test_agent_waterfall.py cost-fallback WARN coverage for the combined case.




### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:498-567
- **Concern**: Half-mark anchor treats any non-empty rc0 output as substantive. Scenario: A reviewer can exit 0 with non-empty malformed output; the cutoff still arms before collector validation and can drop valid slower reviewers
- **Proposed resolution**: Fix the anchor to count only collector-validated OK/cap_hit outputs, or do not count malformed non-empty rc0 output; add that test case




### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agent_waterfall.py:736-773
- **Concern**: Plan emits a second WARN=reviewer-straggler-dropped KV alongside cost-fallback-exceeded-threshold but dispatch_waterfall uses one warn string and one emit_kv("WARN") and _kv_parse keeps the last WARN= only. Scenario: When fallback volume and straggler cuts co-occur the cost-fallback warning is dropped and downstream WARN consumers see only one token
- **Proposed resolution**: Combine both tokens in one WARN value (for example space-separated) or emit a single WARN that lists every active warning token




### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:1945-1950
- **Concern**: Gap 1 fixes check_reviewer_failure_threshold dropped-slots counting but the plan does not update _static_coverage_reason which still requires every static archetype to have a successful output. Scenario: After straggler cuts remove the only surviving slot(s) for an archetype (both vendors slow while other archetypes arm the deadline) THRESHOLD_OK can stay true yet review_core sets threshold_ok=false via COVERAGE_GATE and returns panel-failed contradicting Round 1 proceed-with-collected-reviews
- **Proposed resolution**: Extend review_pipeline.py (coverage gate or _static_coverage_reason) to read DROPPED_SLOTS_FILE and exclude straggler-dropped static slugs from the missing-archetype set when proceeding with a partial panel; add a test_review_pipeline.py case mirroring the threshold exclusion test




### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agent_waterfall.py _reap_phase
- **Concern**: [SCOPE-REDUCTION] Plan switches Round 1 Q&A fastest-success x ~3X anchor to half-mark substantive quorum x 2.5X adding needed counter and per-finish substantive probes. Scenario: Half-mark never arms when fewer than ceil(N/2) substantive successes finish so slow stragglers still wait until per-reviewer --timeout in sparse-success rounds; acceptance text still cites fastest_success x 3
- **Proposed resolution**: Anchor on earliest substantive success elapsed (rc==0 plus _has_nonempty_output) with default multiple 3.0 to match Q&A and Gap 2 without half-panel quorum state




### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:412-567
- **Concern**: Anchor treats non-empty output as substantive. Scenario: Two fast rc 0 reviewers emit non-empty malformed output; the half-mark arms, the deadline kills slower valid reviewers, and later collection rejects the anchors
- **Proposed resolution**: Count the anchor only after the same collector or gate validation that would keep a review; add a non-empty invalid-output test




### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_pipeline.py:1573-1601,1936-1950
- **Concern**: Straggler drops still fail the static coverage gate. Scenario: A single-vendor hard panel can get two valid static reviews and one straggler drop; threshold skips the drop, but _static_coverage_reason reports the missing archetype and panel-fails instead of proceeding
- **Proposed resolution**: Thread straggler-dropped rows into static coverage and subtract only those slugs from expected; add a focused review-core test




### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:28-33
- **Concern**: The plan replaces the binding fastest-success anchor with a half-mark (ceil(N/2) substantive successes) at 2.5x, but acceptance and Round 1 Q&A require clamp(3x fastest_success, 300s, --timeout) anchored on the first successful completion.. Scenario: In the cited 37:30 example, fastest substantive success is ~115s, so acceptance implies a ~345s cap. Half-mark may not arm until the 4th substantive finish (~277s+), yielding ~692s+ and still letting a 1674s straggler run far longer than specified. Worse: if fewer than ceil(N/2) slots ever produce substantive rc==0 output, no deadline arms and the round reverts to wait-for-all up to per-slot --timeout, failing the core straggler problem when only one or two reviewers succeed early.
- **Proposed resolution**: Re-anchor on the first substantive rc==0 success (fastest elapsed) with default multiple 3 (2.5 acceptable per Q&A), keeping _has_nonempty_output so exit-0-empty never anchors (Gap 2). Drop the half-mark quorum unless explicitly re-scoping acceptance.




### [Plan Review] FINDING_12

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:5-12
- **Concern**: [SCOPE-REDUCTION] Plan replaces the required fastest-success cutoff with a half-panel quorum. Scenario: The stated scope caps reviewer wall time from the fastest successful reviewer. This plan waits for ceil(N/2) successes before arming. If one valid reviewer finishes quickly and the rest hang, the panel still waits to --timeout.
- **Proposed resolution**: Restore the anchor to the fastest accepted reviewer completion. Keep the opt-in caller scope, but remove half-mark quorum behavior and its tests/docs.




