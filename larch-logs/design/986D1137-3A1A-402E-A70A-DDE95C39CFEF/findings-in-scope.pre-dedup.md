### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review_panel.py
- **Concern**: Drop PRUNED_COUNT from design escalated-pruning stdout assertions. Scenario: `plan-review panel-dispatch` only emits `PANEL_PRUNED_EMPTY` on stdout (`plan_review_panel.py` ~605); `PRUNED_COUNT` stays internal in `prune_kv`. Code-review `review dispatch-panel` does emit `PRUNED_COUNT`, so mirroring that assertion here would fail under the test-only constraint.
- **Proposed resolution**: Assert `PANEL_PRUNED_EMPTY=false`, non-empty `plan-review-slots.ndjson`, and optionally monkeypatch `_filter_pruned` to prove `prune_round_num=0`; do not require `PRUNED_COUNT=` in dispatch stdout.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review_panel.py (plan.txt:95-99)
- **Concern**: [SCOPE-REDUCTION] The escalated-pruning plan still asks the design panel test to assert PRUNED_COUNT=0, but that KV is only emitted by the prune filter/code-review panel surface, not by plan-review panel-dispatch.. Scenario: A test that follows the plan can fail despite correct design behavior, or pressure the implementer to add a runtime PRUNED_COUNT emission, violating the test-only/no-runtime-change scope.
- **Proposed resolution**: Revise the planned assertion to use the existing design-panel surface: assert the manifest stays non-empty and PANEL_PRUNED_EMPTY=false, and prove the short-circuit by monkeypatching or capturing _filter_pruned receiving prune_round_num=0.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review_panel.py
- **Concern**: Gap 3 escalated-pruning assertions include PRUNED_COUNT on panel-dispatch stdout. Scenario: `plan_review_panel.dispatch_panel` emits `PANEL_PRUNED_EMPTY` on success but never forwards internal `PRUNED_COUNT`; a test that greps dispatch stdout for `PRUNED_COUNT=0` fails even when escalated rounds correctly bypass pruning via `prune_round_num=0`
- **Proposed resolution**: Drop the `PRUNED_COUNT=0` stdout assertion; prove the short-circuit with a non-empty `plan-review-slots.ndjson`, `PANEL_PRUNED_EMPTY=false`, and no `plan-review-slots.pre-prune.ndjson` (or use the optional `_filter_pruned` monkeypatch to assert `prune_round_num=0`)



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-review-token-propagation.sh
- **Concern**: Gap 1 tier-case isolation is underspecified in the planned edits. Scenario: `resolve_panel_tier` writes `$IMPLEMENT_TMPDIR/difficulty-rating.json` on the first `--difficulty` call; reusing one tmpdir and only clearing `CORE_CAPTURE` leaves a persisted tier that makes the trailing default MODERATE path (no `--difficulty`) assert the wrong `--panel`/`PANEL_SHAPE` pair
- **Proposed resolution**: Require a fresh `IMPLEMENT_TMPDIR` per tier case, or delete `difficulty-rating.json` between cases; run the existing default MODERATE assertion before any override cases, or keep it on its own tmpdir schema_version scope severity focus_area location what scenario_or_breakage suggested_fix



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review_panel.py
- **Concern**: Gap 3 escalated-pruning assertions include PRUNED_COUNT on panel-dispatch stdout. Scenario: `plan_review_panel.dispatch_panel` emits `PANEL_PRUNED_EMPTY` on success but never forwards internal `PRUNED_COUNT`; a test that greps dispatch stdout for `PRUNED_COUNT=0` fails even when escalated rounds correctly bypass pruning via `prune_round_num=0`
- **Proposed resolution**: Drop the `PRUNED_COUNT=0` stdout assertion; prove the short-circuit with a non-empty `plan-review-slots.ndjson`, `PANEL_PRUNED_EMPTY=false`, and no `plan-review-slots.pre-prune.ndjson` (or use the optional `_filter_pruned` monkeypatch to assert `prune_round_num=0`)



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-review-token-propagation.sh
- **Concern**: Gap 1 tier-case isolation is underspecified in the planned edits. Scenario: `resolve_panel_tier` writes `$IMPLEMENT_TMPDIR/difficulty-rating.json` on the first `--difficulty` call; reusing one tmpdir and only clearing `CORE_CAPTURE` leaves a persisted tier that makes the trailing default MODERATE path (no `--difficulty`) assert the wrong `--panel`/`PANEL_SHAPE` pair
- **Proposed resolution**: Require a fresh `IMPLEMENT_TMPDIR` per tier case, or delete `difficulty-rating.json` between cases; run the existing default MODERATE assertion before any override cases, or keep it on its own tmpdir ### Findings 1. **correctness** — `python/tests/review/test_plan_review_panel.py`: The escalated-round pruning case should not assert `PRUNED_COUNT=0` on `panel-dispatch` stdout. Design dispatch only surfaces `PANEL_PRUNED_EMPTY`; use manifest non-emptiness, `PANEL_PRUNED_EMPTY=false`, absent `pre-prune` artifact, or the documented monkeypatch. 2. **correctness** — `skills/implement/scripts/test-implement-review-token-propagation.sh`: Tier cases need tmpdir isolation beyond clearing `CORE_CAPTURE`. Either use a fresh `IMPLEMENT_TMPDIR` per tier (and for the default MODERATE case) or remove `difficulty-rating.json` between runs; otherwise the preserved default-path check can fail after override cases.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_panel.py:603-605
- **Concern**: Escalated-pruning test must not assert PRUNED_COUNT on panel-dispatch stdout. Scenario: `plan-review panel-dispatch` success output emits `PANEL_PRUNED_EMPTY` (and slot/path KVs) but never `PRUNED_COUNT`; only `review dispatch-panel` emits that KV. A new `test_panel_dispatch_*` escalated-round case that grep-checks `PRUNED_COUNT=0` on dispatch stdout will fail even when escalated rounds correctly force `prune_round_num=0` and skip pruning.
- **Proposed resolution**: Keep the escalated-round proof on manifest non-emptiness plus `PANEL_PRUNED_EMPTY=false` in stdout, and/or a narrow monkeypatch that `_filter_pruned` was called with `prune_round_num=0`. Drop `PRUNED_COUNT` from the design dispatch assertions.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review_panel.py
- **Concern**: [INCOMPLETE] Escalated-pruning case still targets PRUNED_COUNT on design panel-dispatch stdout. Scenario: `plan_review_panel.dispatch_panel` only emits `PANEL_PRUNED_EMPTY` from `_filter_pruned`; unlike code-review `review_dispatch_panel`, it never prints `PRUNED_COUNT`. A test that greps dispatch stdout for `PRUNED_COUNT=0` fails even when escalated rounds correctly short-circuit pruning to `prune_round_num=0`.
- **Proposed resolution**: Assert `PANEL_PRUNED_EMPTY=false`, a non-empty `plan-review-slots.ndjson`, and no `plan-review-slots.pre-prune.ndjson` after dispatch with `--round-num 3 --escalated-round true` and a ledger that would empty the panel if pruning ran; optionally monkeypatch `_filter_pruned` to assert `prune_round_num=0`. Do not require `PRUNED_COUNT` on stdout.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-step3-review-cap.sh
- **Concern**: [INCOMPLETE] HARD round-3 case still allows counter-only launch proof. Scenario: `plan_review.py` increments `review-round-count.txt` to the launched round on `panel-failed` and other non-cap paths. Asserting only that the counter reached `3` does not prove round 3 actually launched; it matches the false-positive path the prior review flagged.
- **Proposed resolution**: Make fail-closed loop-stub capture of dispatched `--round-num 3` the required positive proof. Treat `review-round-count.txt == 3` or a `plan-review/round-3` artifact as optional secondary checks only, not sufficient alone.



