### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:412-430
- **Concern**: Reap-loop anchor probes call full collect-results synchronously. Scenario: _slot_collector_accepted is specified to run agent collect-results --summary-only inside the _reap_phase poll loop; on rc=0 empty output with retry metadata collect_results launches and waits for a retry up to opts.timeout plus grace, blocking the poll loop while other reviewers keep running so the adaptive deadline may not fire until after the retry wait completes
- **Proposed resolution**: Implement anchor acceptance inline (sentinel plus output read plus shared _apply_collector_block pattern gates) without collect-results retry side effects, or add a collect-results --no-retry flag used only for anchor probes



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agent_waterfall.py:412-567
- **Concern**: [SCOPE-REDUCTION] Half-mark anchor calls a full `cli.py agent collect-results` subprocess per finished slot inside the reap poll loop. Scenario: The reap loop cannot poll other launches or enforce the straggler deadline while a subprocess runs; with many slots this serializes anchor work and can push the real cutoff well past `clamp(2.5 × anchor, 300s, --timeout)`, partly defeating the feature
- **Proposed resolution**: Implement `_slot_collector_accepted` via an in-process helper imported from `collect_results` (shared with `_apply_collector_block`) that reads the existing `.done` sentinel and returns the same OK/cap_hit + gate predicate without spawning a new Python process per slot



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:14-19
- **Concern**: python/plan_review_round.py:391-404. Scenario: /design half-mark anchor uses summary-only collect acceptance but plan-review round collect applies substantive plus structured validation
- **Proposed resolution**: Fast reviewers can arm the deadline with STATUS=OK outputs that plan_review_round later demotes to NOT_SUBSTANTIVE; slow reviewers still producing the only substantive findings get SIGTERM'd; round may finish with low ok_count or degraded-empty-collector despite the feature intent to wait for real successes Teach _slot_collector_accepted to accept the same collect-results flags the downstream consumer uses; for plan_review_panel dispatch pass substantive-validation validation-mode and structured-reviewer-validation (or one bundled --straggler-anchor-strict flag set only there); count half-mark only when that probe returns OK/cap_hit



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:11-12,39-43
- **Concern**: Round 1 Q&A requires anchor on the fastest successful reviewer at ~3×; plan arms on ceil(N/2) collector-validated successes at 2.5×. Scenario: Issue #4658 acceptance and Q&A describe clamp(3× fastest_success, 300s, --timeout). Half-mark waits for more completions before arming, so deadlines are later than fastest-anchor in typical panels and may still wait near the full per-reviewer timeout when validated successes arrive slowly
- **Proposed resolution**: Use the first collector-validated success (not half-mark) as anchor, default multiple 3.0 (keep 2.5 as env override), and align acceptance/docs with that policy



### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:512; python/review_pipeline.py:1293; python/plan_review_round.py:394-400
- **Concern**: Anchor validation uses waterfall's unvalidated summary collector, not the downstream substantive or structured collector contract. Scenario: A fast rc0 non-empty malformed reviewer can return STATUS=OK during reap, arm the half-mark cutoff, and kill slower reviewers before the later panel collector rejects that same output as NOT_SUBSTANTIVE
- **Proposed resolution**: Thread an anchor-validation mode for opted-in reviewer panels and count only outputs that pass the same substantive or structured validation the panel later applies, or add equivalent required output gates before arming the cutoff



### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/collect_results.py:908-972; python/agent_waterfall.py:512
- **Concern**: Per-finish collect-results probes are not idempotent because summary-only still launches EMPTY_OUTPUT retries. Scenario: A fast empty reviewer with launch-review metadata can trigger an external retry during reap, then the unchanged batch collect can launch the same retry again, adding extra reviewer runs and allowing anchor acceptance to diverge from final acceptance
- **Proposed resolution**: Make the anchor probe side-effect-free, for example a no-retry summary path or pure status reader, and leave retry launches in the existing final collect path only



