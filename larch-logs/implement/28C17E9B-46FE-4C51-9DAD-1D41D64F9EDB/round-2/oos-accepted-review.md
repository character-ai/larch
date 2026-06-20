### OOS_1: correctness: python/plan_review_panel.py:410-412
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Panel emits INVALID_SLOT_PANEL_WARNING but plan requires DEGRADED_PANEL_WARNING for invalid-slot drops while shell only replays DEGRADED_PANEL_WARNING Invalid-slot drop plus voter degradation: only voter warning reaches orchestrator-visible stdout; invalid-slot warning is dropped at shell boundary Emit DEGRADED_PANEL_WARNING from dispatch_panel as planned or wire INVALID_SLOT_PANEL_WARNING through design-step3-review.sh and document the two-key split
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/test_plan_review.py:36-49
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Envelope propagation test covers DEGRADED_PANEL_WARNING not the production INVALID_SLOT_PANEL_WARNING key A regression removing INVALID_SLOT_PANEL_WARNING from persist or emit would pass tests while breaking production invalid-slot warning path Add test using INVALID_SLOT_PANEL_WARNING and extend design-step3-review.sh harness to assert shell replay
- **Suggested revision**: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] risk-integration: python/agent_waterfall.py:442-557
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Straggler-cutoff refactor bundled with skip-invalid-slots change Unrelated behavior change increases regression surface for this PR Consider splitting or extra straggler-focused tests in a separate change
- **Suggested revision**: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] correctness: python/review_and_fix.py:908-1986
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] _collect_round_stage_paths returns empty when diff_base missing Unrelated to #4768; may affect review-and-fix path collection Track under its originating issue not this PR
- **Suggested revision**: Address the concern above.


### OOS_5: correctness: python/test_plan_review.py:41-54
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Envelope test covers DEGRADED_PANEL_WARNING for invalid-slot text, not the production INVALID_SLOT_PANEL_WARNING key. A regression that breaks INVALID_SLOT_PANEL_WARNING persist/emit but leaves DEGRADED_PANEL_WARNING handling intact would not be caught by the added envelope test. Add or extend a test that persists and emits INVALID_SLOT_PANEL_WARNING with invalid-slot drop content.
- **Suggested revision**: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] risk-integration: python/review_pipeline.py,python/review_and_fix.py
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Branch diff includes straggler-cutoff and reviewer failure-threshold changes from other commits. Unrelated behavior changes ride on the same branch vs main; not part of #4768 invalid-slot degradation. Review or split in a separate PR; keep #4768 diff focused.
- **Suggested revision**: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] Pre-existing cross-round continuation in `python/plan_review.py:1375-1376` clears `degraded_values` (including carried warnings) when starting a new review round; that behavior predates this branch and affects both warning keys equally.
- **Reviewer**: dyn-step3-propagation-output.txt
- **Concern**: - Pre-existing cross-round continuation in `python/plan_review.py:1375-1376` clears `degraded_values` (including carried warnings) when starting a new review round; that behavior predates this branch and affects both warning keys equally.
- **Suggested revision**: Address the concern above.


### OOS_8: **correctness** `python/test_plan_review.py:36-49` — `test_step3_loop_persist_envelope_persists_and_emits_degraded_panel_warning` exercises `DEGRADED_PANEL_WARNING` with invalid-slot drop text, but production emits `INVALID_SLOT_PANEL_WARNING` for that path (`python/plan_review_panel.py:412`). The test passes while `design-step3-review.sh` omits the production key, so CI does not guard the Step 3 boundary contract for degraded mixed manifests. **Suggested fix:** Rename the test inputs/assertions to `INVALID_SLOT_PANEL_WARNING`, and add an end-to-end assertion that `design-step3-review.sh` replays that key from `.step3-review-result.env` and captured round stdout.
- **Reviewer**: dyn-mixed-manifest-output.txt
- **Concern**: - **correctness** `python/test_plan_review.py:36-49` — `test_step3_loop_persist_envelope_persists_and_emits_degraded_panel_warning` exercises `DEGRADED_PANEL_WARNING` with invalid-slot drop text, but production emits `INVALID_SLOT_PANEL_WARNING` for that path (`python/plan_review_panel.py:412`). The test passes while `design-step3-review.sh` omits the production key, so CI does not guard the Step 3 boundary contract for degraded mixed manifests. **Suggested fix:** Rename the test inputs/assertions to `INVALID_SLOT_PANEL_WARNING`, and add an end-to-end assertion that `design-step3-review.sh` replays that key from `.step3-review-result.env` and captured round stdout.
- **Suggested revision**: Address the concern above.


### OOS_9: [OUT_OF_SCOPE] `python/compose_review.py:129-136` — Still calls `.get` on unchecked `json.loads` results; pre-existing, not introduced by this branch.
- **Reviewer**: dyn-mixed-manifest-output.txt
- **Concern**: - `python/compose_review.py:129-136` — Still calls `.get` on unchecked `json.loads` results; pre-existing, not introduced by this branch.
- **Suggested revision**: Address the concern above.


