## Decision 1: Scope coverage — all 7 items
- **Question**: Cover all 7 rollup items in one plan, or split out the complex Item 5 (round-2+ re-raise)?
- **Resolution**: Design all 7 items together. For items already partly closed in current code (Item 2 empty-session-id rejection exists; Item 3 render-failure emission already gated), apply the smallest change: add the missing test coverage and residual hardening rather than re-implementing closed behavior. Plan-size gates may split later only if the plan grows too large.
- **Source**: user

## Decision 2: Item 7 probe-timeout policy — keep 60s
- **Question**: `LARCH_PROBE_TIMEOUT_SECONDS` was bumped 30→60s deliberately in #4801/#4852. Revert to 30s for lower latency, or keep 60s?
- **Resolution**: Keep the 60s default. Resolve Item 7 as intentional and document the rationale; do NOT revert. Reverting risks re-introducing probe-timeout false-negatives that falsely trip the degraded-tools gate. Timeout-retries already default to 0, so no retry-count lever exists. The "two defaults" premise is partly inaccurate — only `LARCH_PROBE_TIMEOUT_SECONDS` moved 30→60 (in #4852); `LARCH_PROBE_TTL_SECONDS` has been 60 since #4166.
- **Source**: user + codebase

## Decision 3: Hard constraint — design_publish.py overlaps in-flight #4865
- **Question**: Does the fix surface overlap any in-flight /design or /implement issue?
- **Resolution**: `python/design_publish.py` is a SECONDARY surface here (Items 1–2: publish stdout fd capture, session-id) and overlaps in-flight `[DESIGNING]` #4865 Item 3 (secret-scrub/redact path — a DIFFERENT region, speculative, #4865 has no plan block yet). Per saved guidance this is a secondary-surface overlap: proceed, but write the design_publish.py edits merge-order-agnostically (describe edits by function/behavior, not brittle line numbers) so whichever lands second adapts cleanly. #4864's primary surface (design_lifecycle.py, plan_review.py, plan_review_panel.py, agents.py) does not overlap any in-flight issue.
- **Source**: codebase

## Decision 4: Hard constraints — preserve Step 5c / plan-review contracts
- **Question**: What existing behavior must not break?
- **Resolution**: Preserve: the FD3 quiet contract stream and `emit_kv` grammar; the `LARCH_FINAL_SUMMARY_BEGIN`/`LARCH_FINAL_SUMMARY_END` marker pair the orchestrator extracts; the Step 5c publish driver exit-code contract ({0,1,3,4} normal; 2/5/other abort); `.completed/step-5c-terminal` vs `.completed/step-5c` sentinel semantics; `PLAN_WRITE_OK`/`PUBLISH_OK` gating of rename + cleanup; the static + dynamic plan-review slot manifest contract; the `_slot_row` one-line fallback shape (Item 6 adds a WARNING on render miss, it must not change the static-path fallback). All changes must keep `make py-lint` and `make py-test` green and add same-PR harness coverage per launcher/test rules.
- **Source**: codebase
