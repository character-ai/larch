### FINDING_1: Keep tier tests under the Makefile selector
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: New tier and escalated-pruning pytest cases can be silently skipped by `make test-dispatch-plan-review-panel` unless their function names include `panel_dispatch`, because the Makefile target filters with `-k 'panel_dispatch and not usage'`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Name new tests test_panel_dispatch_* (or include panel_dispatch in the name) and note the Makefile filter in the Testing strategy section."
  - From Cursor-Innovation: "Name new tier tests `test_panel_dispatch_<tier>_...` (and keep `panel_dispatch` in the escalated-round test name) so the existing Makefile filter executes them"
  - From Cursor-Pragmatic: "Name every new tier/role/pruning test `test_panel_dispatch_<...>` so the existing Makefile target executes them; note the naming rule in Testing strategy."
  - From Cursor-Requirements: "Name new tier and escalated-pruning tests `test_panel_dispatch_*` (or include `panel_dispatch` in the function name) and note that contract beside the pytest edits"


### FINDING_2: Read Step 5 env/capture, not wrapper stdout
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Harness Coverage Reviewer, Codex-dyn-Harness Coverage Reviewer
- **Severity**: important
- **Concern**: The Step 5 token-propagation harness is asserting `PANEL_SHAPE` and round-cap KVs on wrapper stdout, but those values are produced in the review-core capture path; it also needs to separate tier-derived shape/cap semantics from the threshold `simple/hard` token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Assert PANEL_SHAPE in $IMPLEMENT_TMPDIR/round-1/review-core.env or CORE_CAPTURE from the stub, not review-and-fix or step-5-review.sh stdout. Drop the wrapper-output wording or narrow it to the review-core capture path."
  - From Cursor-Innovation: "Assert `PANEL_SHAPE` (and tier-derived cap) from `$IMPLEMENT_TMPDIR/round-1/review-core.env` after `review-and-fix step5 --mode single`, or from the stub capture file; drop the wrapper-stdout requirement"
  - From Cursor-Pragmatic: "Assert tier→`--panel`/`--tier` via `CORE_CAPTURE` argv; assert `PANEL_SHAPE`/`PANEL_ROUND_CAP` (if kept) by grepping `$IMPLEMENT_TMPDIR/round-1/review-core.env`, not step-5 wrapper stdout."
  - From Cursor-Requirements: "Assert `PANEL_SHAPE` / `PANEL_ROUND_CAP` in `$IMPLEMENT_TMPDIR/round-1/review-core.env` (or the stub capture of review-core stdout), not step-5 wrapper stdout"
  - From Cursor-dyn-Harness Coverage Reviewer: "Grep $IMPLEMENT_TMPDIR/round-1/review-core.env for PANEL_SHAPE/PANEL_TIER/EFFECTIVE_ROUND_CAP (and argv capture for --panel/--tier). Use singles/pairs for PANEL_SHAPE per panel_shape_for_tier (python/larch/calibration/difficulty.py:162-163), not simple/hard."
  - From Codex-dyn-Harness Coverage Reviewer: "PANEL_SHAPE is not on review-and-fix step5 stdout. Scenario: review_and_fix single mode ends with _emit_round_kvs (python/larch/review/round_runner.py:653-681), which omits PANEL_SHAPE, PANEL_TIER, and cap KVs. review_core_capture persists stub stdout to round-1/review-core.env (python/larch/review/round_runner.py:90-117). Asserting wrapper stdout will fail even when propagation works."
  - From Cursor-Arch: "A TRIVIAL case must assert --panel simple in argv and PANEL_SHAPE=singles in stub-derived KVs or review-core.env. Keep the two checks separate per the plan failure-modes note."
  - From Cursor-Pragmatic: "Stub `PANEL_SHAPE=simple` mismatches production semantics. Scenario: Runtime uses `difficulty.panel_shape_for_tier` (`singles`/`pairs`) and `threshold_panel_for_tier` (`simple`/`hard`) as separate concepts. A stub that echoes `simple`/`hard` into `PANEL_SHAPE` would pass while mis-documenting the contract the issue cites."
  - From Cursor-Pragmatic: "Teach the stub to emit `PANEL_SHAPE` from `--tier` using `panel_shape_for_tier` (`TRIVIAL`→`singles`, `MODERATE`/`HARD`→`pairs`) and `PANEL_ROUND_CAP` from tier ceiling; keep `--panel simple|hard` as a separate assertion"
  - From Cursor-Pragmatic: "Implement stub should emit EFFECTIVE_ROUND_CAP not PANEL_ROUND_CAP. Scenario: Shipped review-core stdout uses EFFECTIVE_ROUND_CAP from tier_ceiling (python/larch/review/review_core_body.py:1146-1147). PANEL_ROUND_CAP is dispatch-panel stdout only (python/larch/review/review_dispatch_panel.py:758-760). A stub/assert on PANEL_ROUND_CAP pins a KV the step5 review-core path never emits."
  - From Cursor-Innovation: "Assert PANEL_SHAPE in $IMPLEMENT_TMPDIR/round-1/review-core.env or CORE_CAPTURE from the stub, not review-and-fix or step-5-review.sh stdout. Drop the wrapper-output wording or narrow it to the review-core capture path."
  - From Cursor-Innovation: "Plan asserts `PANEL_SHAPE` through step-5 wrapper stdout. Scenario: `round_runner._emit_round_kvs` and `_emit_step5_envelope` do not print `PANEL_SHAPE`. Wrapper stdout will not contain it even when review-core emits it correctly"
  - From Cursor-Requirements: "[ALREADY_ADDRESSED] Plan targets PANEL_SHAPE on step-5 wrapper stdout. Scenario: `review-and-fix step5 --mode single` emits round KVs via `_emit_round_kvs` without `PANEL_SHAPE`; only `review-core.env` (or captured review-core stdout) carries it, so grepping wrapper stdout yields a false gap or a brittle test"
  - From Cursor-dyn-Harness Coverage Reviewer: "PANEL_SHAPE is not on review-and-fix step5 stdout. Scenario: review_and_fix single mode ends with _emit_round_kvs (python/larch/review/round_runner.py:653-681), which omits PANEL_SHAPE, PANEL_TIER, and cap KVs. review_core_capture persists stub stdout to round-1/review-core.env (python/larch/review/round_runner.py:90-117). Asserting wrapper stdout will fail even when propagation works."


### FINDING_4: Persist the Gate-C HARD seed before cap checks
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-dyn-Harness Coverage Reviewer, Codex-dyn-Harness Coverage Reviewer
- **Severity**: important
- **Concern**: The Gate-C and hard-cap cases need a persisted, explicit HARD difficulty record with no escalations; otherwise the harness can fall back to the old D5 smoke, re-audit, or clobber the seeded tier before it proves the no-round-3 cap behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "In the Gate-C case, write difficulty-rating.json with panel_tier/applied_tier HARD and an empty escalations array, then assert LOOP_STATUS=cap-reached and no round-3 launch artifact."
  - From Codex-Arch: "Seed `audit_evaluated=false` and `audit_upgrade=false`, or build the record with `difficulty.build_record`, so the non-HARD case cannot re-audit."
  - From Cursor-Pragmatic: "In the Gate-C planned edit, require an explicit HARD record without escalation entries and assert `effective_authorized_cap` behavior (cap stays 2) before `LOOP_STATUS=cap-reached`; keep D5 as the generic cap-reached smoke."
  - From Cursor-dyn-Harness Coverage Reviewer: "Write seeds via difficulty.build_record/write_record, or include audit_evaluated/audit_upgrade, escalations, or override_source=operator so _record_resolution_is_persisted is true before run_driver."
  - From Codex-dyn-Harness Coverage Reviewer: "Cap-harness difficulty seed must be resolution-persisted. Scenario: Hand-rolled JSON with only panel_tier is not persisted (python/larch/calibration/difficulty.py:366-371). plan-review run calls resolve_plan_review_tier before cap checks (python/larch/review/plan_review.py:367-368), which re-runs audit when resolved_once is false (python/larch/calibration/difficulty.py:408-424) and can clobber seeded MODERATE/HARD before round-3 or Gate-C assertions."


### FINDING_1: HARD round-3 test needs a direct launch proof
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The HARD round-3 cap harness can pass without proving round 3 actually launched; the current guard only excludes `cap-reached`, so no-op, `panel-failed`, or `tally-error` stubs can still satisfy it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit round-3 observable: a fail-closed stub that records the dispatched round number, review-round-count.txt advancing to 3 after a successful loop, or a plan-review/round-3 artifact. Keep LOOP_STATUS!=cap-reached as a secondary guard.


### FINDING_2: Escalated pruning test should assert the prune short-circuit
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The escalated-round pruning test needs to verify the `prune_round_num=0` early-exit path; a ledger seeded for round-3 pruning does not prove the escalated bypass unless the test asserts that pruning was skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Seed a ledger that would empty a round-3 panel if pruning ran, dispatch with `--round-num 3 --prune-round-num 3 --escalated-round true`, and assert the manifest still has rows plus PRUNED_COUNT=0 / PANEL_PRUNED_EMPTY=false. Optionally monkeypatch _filter_pruned to assert prune_round_num=0 was passed.

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


