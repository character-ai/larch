## Proposed Design Outline

### Goals
- Stop retrying reviewers on result-quality failure. On `NOT_SUBSTANTIVE`: warn, count as a reviewer failure, drop the output, continue.
- Apply the same "retry only for launch, not results" rule to code voters.
- Harden the round-2+ combined `codex-plan-generic` plan-review prompt so it emits structured findings (Part B), reducing how often the drop fires.

### Non-goals
- Keep launch-level retries unchanged: empty output, transient-net, auth-startup.
- No new minimum healthy-reviewer floor; rely on the existing failure-threshold and degraded-panel handling.
- No alt-tool waterfall fallback on a result-quality failure.

### Approach sketch
- Delete the ns-retry execution stage in `collect_results.py` `collect_results()`; keep the two detection validators; let `NOT_SUBSTANTIVE` records flow to `_emit_records` with a WARN line.
- Remove now-dead ns-retry helpers once unreferenced.
- Ensure the plan-review (`plan_review.py`) and `/review` tallies count `NOT_SUBSTANTIVE` as a failure and drop it from findings.
- Replace the voter result retry (`voting parse-rate-retry`) with classify-only in `voting.py` + `dispatch-code-voters.sh`; count the failed voter.
- Make the combined `codex-plan-generic` prompt format-robust in the plan-review prompt rendering surface.

### Surfaces in scope
- `python/collect_results.py`, `python/test_collect_results.py`
- `python/plan_review.py` (+ legacy plan-review collection path)
- `python/legacy_review_shell/collect-findings.sh`, `check-reviewer-failure-threshold.sh`
- `python/voting.py`, `scripts/dispatch-code-voters.sh`, `scripts/test-dispatch-code-voters.sh`, `python/legacy_review_shell/tally-code-votes.sh`
- Plan-review prompt rendering for the combined codex slot (Part B)
- Docs: `skills/design/references/plan-review.md`, `skills/research/references/{research-phase,validation-phase}.md`, `skills/shared/external-reviewers.md`, `docs/external-reviewers.md`

### Open questions
- None. The three issue open questions plus Part B were resolved in Round 1.
