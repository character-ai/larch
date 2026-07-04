### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py
- **Concern**: Plan tells implementers to shorten OOS prose in `render_plan_review_main()` while also forbidding edits to `_oos_proposal_instruction()` / `oos_proposal_instruction()`. Scenario: Plan-review OOS cap and materiality text is injected only through the shared helper (`{_oos_proposal_instruction()}` at line 1391). An implementer following the compress-OOS bullet cannot deliver that part of the density pass without violating the do-not-touch boundary, or may edit the helper and break implement/voter surfaces that share it
- **Proposed resolution**: Remove OOS from the compressible-prose list in the `render_plan_review_main()` section. Limit compression to the inline `[OUT_OF_SCOPE]` prefix line in the f-string; keep the shared OOS helper byte-stable



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:1393-1403
- **Concern**: Plan permits shortening TSV instructional prose beyond a short pinned list, but pytest and the prompt-template harness require additional exact substrings. Scenario: The plan names only two harness phrases plus header/example/sentinel, yet also says to shorten response-start/TSV prose. `test_render_plan_review_tsv_contract_hardening` and `scripts/test-prompt-template-invariants.sh` (lines 248-263) also pin `literal constant 1 (the schema_version) on EVERY row`, `NOT a per-row counter`, `focus_area exactly one of code-quality, risk-integration, correctness, architecture, security`, and `no other value such as completeness`. Compression without updating those assertions fails CI even when the two named phrases stay intact
- **Proposed resolution**: In the `render_plan_review_main()` and Testing strategy sections, state that all substrings asserted by `test_render_plan_review_tsv_contract_hardening` and the plan-reviewer block in `scripts/test-prompt-template-invariants.sh` stay byte-identical unless those assertions are updated in the same PR ## Findings 1. **correctness** (`python/larch/rendering/rendering.py`): The plan both forbids `_oos_proposal_instruction()` and tells implementers to shorten OOS prose. Plan-review OOS cap text comes only from that helper, so the compress-OOS bullet is not executable within scope. 2. **correctness** (`python/larch/rendering/rendering.py:1393-1403`): The plan allows shortening TSV explanation prose while only listing two harness-pinned phrases. Pytest and `test-prompt-template-invariants.sh` pin additional exact strings (`literal constant 1...`, `NOT a per-row counter`, focus_area allowlist lines). An implementer can follow the plan, pass the listed pytest targets for other areas, and still break CI.



