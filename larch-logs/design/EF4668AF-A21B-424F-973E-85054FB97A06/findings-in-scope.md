### FINDING_1: Anchor probes invoke full collect-results with retry side effects
- **Reviewer(s)**: Cursor-Arch, Codex-Generic
- **Severity**: blocking
- **Concern**: The reap-loop anchor acceptance path calls `agent collect-results --summary-only` synchronously inside the poll loop. On rc=0 with empty output and retry metadata, collect-results can launch and block on an EMPTY_OUTPUT retry for up to `opts.timeout` plus grace. That stalls the concurrent poll loop while other reviewers keep running, so the adaptive deadline may not fire until after the retry completes. The same probe path is also not idempotent: a fast empty reviewer with launch-review metadata can trigger an external retry during reap, and the later batch collect can launch the same retry again. That adds extra reviewer runs and lets anchor acceptance diverge from final acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement anchor acceptance inline (sentinel plus output read plus shared _apply_collector_block pattern gates) without collect-results retry side effects, or add a collect-results --no-retry flag used only for anchor probes
  - From Codex-Generic: Make the anchor probe side-effect-free, for example a no-retry summary path or pure status reader, and leave retry launches in the existing final collect path only

### FINDING_2: Half-mark anchor uses weaker validation than downstream panel collect
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: `/design` half-mark anchor acceptance uses summary-only collect, but plan-review round collect applies substantive plus structured validation (`python/plan_review_round.py:391-404`). Waterfall anchor validation uses the unvalidated summary collector, not the downstream substantive or structured contract (`python/agent_waterfall.py:512`; `python/review_pipeline.py:1293`; `python/plan_review_round.py:394-400`). A fast rc=0 non-empty but malformed reviewer can return STATUS=OK during reap, arm the half-mark cutoff, and get SIGTERM'd slower reviewers before the later panel collector rejects that output as NOT_SUBSTANTIVE. Fast reviewers can arm the deadline with OK outputs that plan_review_round later demotes; slow reviewers producing the only substantive findings may be dropped. The round can finish with low ok_count or degraded-empty-collector despite the intent to wait for real successes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Fast reviewers can arm the deadline with STATUS=OK outputs that plan_review_round later demotes to NOT_SUBSTANTIVE; slow reviewers still producing the only substantive findings get SIGTERM'd; round may finish with low ok_count or degraded-empty-collector despite the feature intent to wait for real successes Teach _slot_collector_accepted to accept the same collect-results flags the downstream consumer uses; for plan_review_panel dispatch pass substantive-validation validation-mode and structured-reviewer-validation (or one bundled --straggler-anchor-strict flag set only there); count half-mark only when that probe returns OK/cap_hit
  - From Codex-Generic: Thread an anchor-validation mode for opted-in reviewer panels and count only outputs that pass the same substantive or structured validation the panel later applies, or add equivalent required output gates before arming the cutoff

### FINDING_3: Anchor policy diverges from Q&A and issue #4658 (fastest @ 3× vs half-mark @ 2.5×)
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Round 1 Q&A requires anchoring on the fastest successful reviewer at roughly 3× (`clamp(3× fastest_success, 300s, --timeout)`). The plan arms on `ceil(N/2)` collector-validated successes at 2.5× (`plan.txt:11-12,39-43`). Half-mark waits for more completions before arming, so deadlines are later than a fastest-anchor policy in typical panels and may still wait near the full per-reviewer timeout when validated successes arrive slowly. This conflicts with issue #4658 acceptance and prior Q&A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Use the first collector-validated success (not half-mark) as anchor, default multiple 3.0 (keep 2.5 as env override), and align acceptance/docs with that policy

---

**Merge notes**

| Merged ID | Source IDs | Rationale |
|-----------|------------|-----------|
| FINDING_1 | 1 + 6 | Same root risk: synchronous collect-results probes with EMPTY_OUTPUT retry side effects during reap |
| FINDING_2 | 3 + 5 | Same root risk: anchor arms on summary-only OK while downstream collect applies substantive/structured validation |
| FINDING_3 | 4 (standalone) | Distinct policy/requirements mismatch (anchor selection and multiplier), not the validation-contract bug |

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agent_waterfall.py:412-567
- **Concern**: [SCOPE-REDUCTION] Half-mark anchor calls a full `cli.py agent collect-results` subprocess per finished slot inside the reap poll loop. Scenario: The reap loop cannot poll other launches or enforce the straggler deadline while a subprocess runs; with many slots this serializes anchor work and can push the real cutoff well past `clamp(2.5 × anchor, 300s, --timeout)`, partly defeating the feature
- **Proposed resolution**: Implement `_slot_collector_accepted` via an in-process helper imported from `collect_results` (shared with `_apply_collector_block`) that reads the existing `.done` sentinel and returns the same OK/cap_hit + gate predicate without spawning a new Python process per slot
