### FINDING_1: Escalated panel-dispatch must not assert `PRUNED_COUNT`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `python/tests/review/test_plan_review_panel.py` should prove escalated pruning through `PANEL_PRUNED_EMPTY=false` plus manifest/monkeypatch checks, not by grepping `panel-dispatch` stdout for `PRUNED_COUNT=0`, because that KV is not emitted there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Assert `PANEL_PRUNED_EMPTY=false`, non-empty `plan-review-slots.ndjson`, and optionally monkeypatch `_filter_pruned` to prove `prune_round_num=0`; do not require `PRUNED_COUNT=` in dispatch stdout.
  - From Cursor-Innovation: Drop the `PRUNED_COUNT=0` stdout assertion; prove the short-circuit with a non-empty `plan-review-slots.ndjson`, `PANEL_PRUNED_EMPTY=false`, and no `plan-review-slots.pre-prune.ndjson` (or use the optional `_filter_pruned` monkeypatch to assert `prune_round_num=0`)
  - From Cursor-Pragmatic: Keep the escalated-round proof on manifest non-emptiness plus `PANEL_PRUNED_EMPTY=false` in stdout, and/or a narrow monkeypatch that `_filter_pruned` was called with `prune_round_num=0`. Drop `PRUNED_COUNT` from the design dispatch assertions.
  - From Cursor-Requirements: Assert `PANEL_PRUNED_EMPTY=false`, a non-empty `plan-review-slots.ndjson`, and no `plan-review-slots.pre-prune.ndjson` after dispatch with `--round-num 3 --escalated-round true` and a ledger that would empty the panel if pruning ran; optionally monkeypatch `_filter_pruned` to assert `prune_round_num=0`. Do not require `PRUNED_COUNT` on stdout.


### FINDING_2: Tier-case tmpdir isolation is required
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-implement-review-token-propagation.sh` can leak `difficulty-rating.json` across tier cases, so reusing one `IMPLEMENT_TMPDIR` after a `--difficulty` run can break the default MODERATE assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require a fresh `IMPLEMENT_TMPDIR` per tier case, or delete `difficulty-rating.json` between cases; run the existing default MODERATE assertion before any override cases, or keep it on its own tmpdir


### FINDING_3: Counter-only proof is insufficient for HARD round-3
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `skills/design/scripts/test-step3-review-cap.sh` needs a fail-closed assertion that round 3 actually launched, not just that the round counter ended at 3, because other non-cap paths can increment the counter without ever dispatching round 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Make fail-closed loop-stub capture of dispatched `--round-num 3` the required positive proof. Treat `review-round-count.txt == 3` or a `plan-review/round-3` artifact as optional secondary checks only, not sufficient alone.


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review_panel.py (plan.txt:95-99)
- **Concern**: [SCOPE-REDUCTION] The escalated-pruning plan still asks the design panel test to assert PRUNED_COUNT=0, but that KV is only emitted by the prune filter/code-review panel surface, not by plan-review panel-dispatch.. Scenario: A test that follows the plan can fail despite correct design behavior, or pressure the implementer to add a runtime PRUNED_COUNT emission, violating the test-only/no-runtime-change scope.
- **Proposed resolution**: Revise the planned assertion to use the existing design-panel surface: assert the manifest stays non-empty and PANEL_PRUNED_EMPTY=false, and prove the short-circuit by monkeypatching or capturing _filter_pruned receiving prune_round_num=0.


