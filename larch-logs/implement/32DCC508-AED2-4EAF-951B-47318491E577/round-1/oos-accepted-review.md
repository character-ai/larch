### OOS_1: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **risk-integration** `skills/design/scripts/design-step5b-annotate.md:20` — The wrapper doc still says annotate failure never writes `.completed/step-5b`, but `step5b_annotate_main` has long written that marker when `oos-issue.stdout.txt` is non-empty on non-zero exit, and this PR updated `skills/design/SKILL.md` to document that. **Suggested fix:** Align `design-step5b-annotate.md` with the SKILL/Python behavior so wrapper docs do not contradict the orchestrator contract.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **code-quality** `skills/design/scripts/design-step5b-annotate.md:20` — Still says annotate failure does not write `.completed/step-5b`, but `step5b_annotate_main` and updated `SKILL.md` prose allow completion when `oos-issue.stdout.txt` is non-empty. **Why OOS:** file not in the plan’s touch list; behavior is already tested in `python/test_design_oos.py`.
- **Suggested revision**: Address the concern above.


### OOS_3: **risk-integration** `python/design_lifecycle.py:4307-4338` — `_step5b_next_action()` returns `""` for unknown or missing `FILE_DESIGN_OOS_STATUS`, and `_step5b_emit_prepare_success()` omits `NEXT_ACTION=` in that case while still exiting `0`. That pushes recovery entirely to prompt-side fallback, which is currently broken (finding above). The plan’s edge case called for stopping on unrecognized status when `NEXT_ACTION` is absent; today prepare succeeds silently and leaves only `STEP5B_STATUS=<unknown>`, which can stall Step 5b.5 (no `.completed/step-5b`) or invite improvised routing. **Suggested fix:** Fail closed in Python for unrecognized statuses (non-zero rc plus explicit `STEP5B_STATUS=unknown-oos-status`), or always emit `NEXT_ACTION` and emit a dedicated repair action; add a test for the missing/unknown-status path.
- **Reviewer**: dyn-dyn-skill-contracts-output.txt
- **Concern**: - **risk-integration** `python/design_lifecycle.py:4307-4338` — `_step5b_next_action()` returns `""` for unknown or missing `FILE_DESIGN_OOS_STATUS`, and `_step5b_emit_prepare_success()` omits `NEXT_ACTION=` in that case while still exiting `0`. That pushes recovery entirely to prompt-side fallback, which is currently broken (finding above). The plan’s edge case called for stopping on unrecognized status when `NEXT_ACTION` is absent; today prepare succeeds silently and leaves only `STEP5B_STATUS=<unknown>`, which can stall Step 5b.5 (no `.completed/step-5b`) or invite improvised routing. **Suggested fix:** Fail closed in Python for unrecognized statuses (non-zero rc plus explicit `STEP5B_STATUS=unknown-oos-status`), or always emit `NEXT_ACTION` and emit a dedicated repair action; add a test for the missing/unknown-status path.
- **Suggested revision**: Address the concern above.


