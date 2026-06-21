# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_2: correctness: python/rendering.py:1192
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan-required prompt-contract regression test not added Prompt hardening strings can be removed in a future edit without CI failure because test-prompt-template-invariants.sh and test_rendering.py do not assert literal constant 1 or focus_area enum text Extend test-prompt-template-invariants.sh or test_rendering.py with assert_contains for the new schema_version and focus_area contract lines
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: python/test_rendering.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan work item 1 required a prompt-contract regression test for render plan-review TSV hardening but no test asserts the new schema_version constant or focus_area enum prose A future edit can remove the hardening lines at python/rendering.py:1192 and make test-prompt-template-invariants plus test_rendering still pass, re-opening the Cursor conformance gap Add test_render_plan_review_tsv_contract_hardening or extend scripts/test-prompt-template-invariants.sh to assert literal constant 1 NOT a per-row counter and the focus_area allowlist including rejection of completeness
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: python/rendering.py:1188-1192
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Prompt hardening lacks the required prompt-contract regression test CI would not catch removal of the literal schema_version or focus_area enum instructions Add a plan-review rendering test asserting the schema constant wording and allowed focus_area values
- **Suggested revision**: Address the concern above.


### FINDING_17: **code-quality** `python/test_rendering.py:358-394` — Work item 1 in the #4994 plan called for a prompt-contract regression test alongside the hardened TSV text in `python/rendering.py:1192`, but no test asserts the new contract strings (`literal constant 1`, `NOT a per-row counter`, enumerated `focus_area` values, or the explicit `completeness` rejection). Existing coverage only checks that `schema_version\tscope\tseverity` appears somewhere in the prompt, so a future edit could drop the hardening without failing CI. **Suggested fix:** Add a `test_render_plan_review` case that renders a minimal plan-review prompt and asserts the full TSV contract block from line 1192 is present verbatim (or match key substrings tied to `_STRUCTURED_HEADER` / `_ALLOWED_FOCUS`).
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **code-quality** `python/test_rendering.py:358-394` — Work item 1 in the #4994 plan called for a prompt-contract regression test alongside the hardened TSV text in `python/rendering.py:1192`, but no test asserts the new contract strings (`literal constant 1`, `NOT a per-row counter`, enumerated `focus_area` values, or the explicit `completeness` rejection). Existing coverage only checks that `schema_version\tscope\tseverity` appears somewhere in the prompt, so a future edit could drop the hardening without failing CI. **Suggested fix:** Add a `test_render_plan_review` case that renders a minimal plan-review prompt and asserts the full TSV contract block from line 1192 is present verbatim (or match key substrings tied to `_STRUCTURED_HEADER` / `_ALLOWED_FOCUS`).
- **Suggested revision**: Address the concern above.


