### OOS_1: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **risk-integration** `python/design_summary.py:364-376` — The post-render block uses `except OSError: pass` around read, append, write, and stdout. A disk/quota error on `write_text` after a successful renderer call drops detail silently while upsert may still publish the compact body and return `0`. Implement’s `write_final_report` does not swallow write failures. Rare; observability-only; pre-existing swallow pattern extended to the new write.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `python/checks.py` — There is no `_DIRECT_TARGET_RULES` entry mapping `python/review_phase_detail.py` / `python/test_review_phase_detail.py` to a focused harness. Edits to the helper alone may not pull `test_review_phase_detail.py` into `/implement` Step 3 `run-relevant` direct targets; full `make py-test` and harness shards still cover it. **Suggested fix:** Add a direct-target rule pairing the module and its test file (similar to `design_summary.py` → `test-render-final-summary`).
- **Suggested revision**: Address the concern above.


