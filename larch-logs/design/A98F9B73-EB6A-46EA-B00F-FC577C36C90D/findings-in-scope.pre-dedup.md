### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:1402
- **Concern**: `render_plan_review_main()` omits passing `--difficulty` into `_architectural_guidelines_review_section()`. Scenario: The plan adds `--difficulty` to the plan-review parser and threads the flag through `plan_review_panel.py`, but its `render_plan_review_main()` bullets only cover payload-byte accounting. Line 1402 still calls `_architectural_guidelines_review_section()` with no tier input, so TRIVIAL `/design` plan-review prompts would keep the full guidelines block and miss acceptance criterion #1.
- **Proposed resolution**: In `render_plan_review_main()`, call `_architectural_guidelines_review_section(args.difficulty)` (or equivalent) before composing `architectural_guidelines_prompt`, and add a renderer test with `--difficulty TRIVIAL` that asserts invariants present and guidelines absent.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/rendering/test_rendering.py:403-1692
- **Concern**: Existing payload sidecar tests are not listed for update when architectural bytes join telemetry. Scenario: The plan adds architectural-section bytes to `_specialist_payload_bytes()` and `render_plan_review_main()` payload accounting. Tests such as `test_render_specialist_payload_sidecar_counts_inline_diff_context`, `test_render_plan_fidelity_includes_plan_context_for_all_review_modes`, `test_render_specialist_payload_sidecar_counts_description_and_cache_hit`, `test_render_plan_review_payload_sidecar_counts_cursor_plan_and_feature`, and `test_render_plan_review_body_file_payload_sidecar_counts_body_feature_and_plan` hard-code totals that exclude those bytes and will fail once telemetry is fixed.
- **Proposed resolution**: Extend the plan testing strategy to update these existing payload sidecar expectations (or gate fixtures so architectural files are absent) alongside the new TRIVIAL-vs-MODERATE payload assertions.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:1339-1403
- **Concern**: The plan adds `--difficulty` to `render_plan_review_main()` but never states that the renderer must pass it into `_architectural_guidelines_review_section()`.. Scenario: Issue acceptance requires TRIVIAL plan-review prompts to omit guidelines. An implementer can add the parser flag and payload-byte accounting yet leave `architectural_guidelines_section = _architectural_guidelines_review_section()` unchanged, so `/design` plan-review slots keep the full ~7k-token guidelines block at TRIVIAL.
- **Proposed resolution**: Add an explicit `render_plan_review_main()` step mirroring `render_specialist_main()`: `architectural_guidelines_section = _architectural_guidelines_review_section(difficulty_value=args.difficulty)` before prompt assembly and payload counting.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/rendering/test_rendering.py
- **Concern**: The planned renderer tests cover TRIVIAL gating for `render_specialist_main()` but not for `render_plan_review_main()`.. Scenario: Issue acceptance and required change #6 apply to both specialist and plan-review prompts. The plan only lists a missing-difficulty case for plan-review, so a correct specialist gate could ship with an untested plan-review regression.
- **Proposed resolution**: Add `render_plan_review_main()` cases for `--difficulty TRIVIAL` (invariants present, guidelines absent) and `--difficulty MODERATE` (both blocks), matching the specialist coverage already listed in the plan.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:1339-1402
- **Concern**: render_plan_review_main omits wiring args.difficulty into the guidelines gate. Scenario: The plan adds --difficulty to the render plan-review parser and documents passing args.difficulty in render_specialist_main, but the render_plan_review_main section only lists payload-byte accounting. An implementer can add the flag yet still call _architectural_guidelines_review_section() with no difficulty at line 1402, leaving /design plan-review prompts on the full guidelines payload at TRIVIAL.
- **Proposed resolution**: In render_plan_review_main(), call _architectural_guidelines_review_section(difficulty_value=args.difficulty) before building architectural_guidelines_prompt, mirroring render_specialist_main.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/rendering/test_rendering.py
- **Concern**: Plan-review TRIVIAL renderer coverage missing from the test plan. Scenario: Acceptance criterion 1 requires TRIVIAL plan-review prompts to omit guidelines. The plan tests render_plan_review_main only for missing difficulty, not --difficulty TRIVIAL, so a plan-review wiring miss would not be caught even if specialist tests pass.
- **Proposed resolution**: Add a render_plan_review_main test with --difficulty TRIVIAL asserting invariants are present and architectural_guidelines tags are absent; keep the existing missing-difficulty fail-open case. ### 1. **correctness** — `python/larch/rendering/rendering.py:1339-1402` The plan adds `--difficulty` to the `render plan-review` parser and clearly says to pass `args.difficulty` in `render_specialist_main`, but the `render_plan_review_main` section only documents payload-byte accounting. Without an explicit call-site step, `/design` plan-review renders can keep calling `_architectural_guidelines_review_section()` with no tier input and fail the core TRIVIAL slim-prompt requirement. **Suggested revision:** In `render_plan_review_main()`, call `_architectural_guidelines_review_section(difficulty_value=args.difficulty)` before building `architectural_guidelines_prompt`. ### 2. **correctness** — `python/tests/rendering/test_rendering.py` Issue acceptance requires TRIVIAL plan-review prompts to omit the guidelines block. The plan’s test list covers `render_plan_review_main` only for missing difficulty, not for `--difficulty TRIVIAL`, so a plan-review-only wiring gap could slip through. **Suggested revision:** Add a focused `render_plan_review_main` TRIVIAL case alongside the existing missing-difficulty fail-open test.



### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:1339-1403
- **Concern**: Plan-review difficulty is parsed and forwarded by callers, but the plan does not require render_plan_review_main to pass args.difficulty into _architectural_guidelines_review_section, and the listed plan-review test only covers missing difficulty. Scenario: A TRIVIAL plan-review render can still call the helper with its default empty difficulty, fail open to the full guidelines block, and violate the acceptance criterion while the planned direct helper and missing-difficulty tests still pass
- **Proposed resolution**: Add an explicit render_plan_review_main step to call _architectural_guidelines_review_section(difficulty_value=args.difficulty), and add a focused render_plan_review_main --difficulty TRIVIAL assertion that invariants remain and guidelines are omitted



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:1402
- **Concern**: render_plan_review_main() never passes args.difficulty into _architectural_guidelines_review_section(). Scenario: The plan adds --difficulty to the plan-review parser and payload accounting, but unlike render_specialist_main() it omits the call-site wiring. render_plan_review_main() would keep calling _architectural_guidelines_review_section() with no tier input, so /design plan-review prompts stay full-guidelines on TRIVIAL and miss acceptance criterion #1.
- **Proposed resolution**: In render_plan_review_main(), pass args.difficulty into _architectural_guidelines_review_section(difficulty_value=args.difficulty) before building architectural_guidelines_prompt; mirror the render_specialist_main() step explicitly in the plan.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/rendering/test_rendering.py
- **Concern**: Plan-review renderer tests omit required TRIVIAL/MODERATE coverage. Scenario: Acceptance criteria require TRIVIAL plan-review prompts to omit guidelines and non-TRIVIAL prompts to stay byte-identical. The plan only adds a missing-difficulty render_plan_review_main() test, so the plan-review slimming path is not specified as a deliverable test.
- **Proposed resolution**: Add render_plan_review_main() tests for --difficulty TRIVIAL (invariants present, guidelines absent) and MODERATE (both blocks), plus a TRIVIAL-vs-MODERATE payload sidecar reduction assertion once architectural bytes are counted.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/tests/rendering/test_rendering.py:403-438
- **Concern**: Existing payload sidecar tests will break after architectural bytes are added. Scenario: The plan adds architectural section bytes to _specialist_payload_bytes() and render_plan_review_main() payload accounting, but several tests hardcode totals without architectural content (for example test_render_specialist_payload_sidecar_counts_inline_diff_context and test_render_plan_review_payload_sidecar_counts_cursor_plan_and_feature). CI will fail unless those expectations are updated or tests patch guideline presence deterministically.
- **Proposed resolution**: List the affected existing payload sidecar tests under python/tests/rendering/test_rendering.py and require updating their expected byte counts (or patching architectural fixtures) alongside the new TRIVIAL/MODERATE cases. ### 1. **correctness** — `python/larch/rendering/rendering.py:1402` `render_plan_review_main()` never passes `args.difficulty` into `_architectural_guidelines_review_section()`. The plan wires difficulty gating explicitly for `render_specialist_main()` but only adds a parser flag and payload accounting for plan-review. Without the call-site change at line 1402, TRIVIAL `/design` plan-review prompts would still include the full guidelines block, failing acceptance criterion #1. **Suggested revision:** Add an explicit plan step: pass `args.difficulty` into `_architectural_guidelines_review_section(difficulty_value=args.difficulty)` before building `architectural_guidelines_prompt`. ### 2. **risk-integration** — `python/tests/rendering/test_rendering.py` Plan-review renderer tests omit required TRIVIAL/MODERATE coverage. Acceptance criteria require TRIVIAL plan-review prompts to omit guidelines. The plan’s test section only specifies a missing-difficulty case for `render_plan_review_main()`, leaving the plan-review slimming path unverified. **Suggested revision:** Add `render_plan_review_main()` tests for `--difficulty TRIVIAL` and `MODERATE`, including a payload sidecar reduction check once architectural bytes are counted. ### 3. **code-quality** — `python/tests/rendering/test_rendering.py:403-438` Existing payload sidecar tests will break after architectural bytes are added. The plan adds architectural section bytes to payload accounting, but tests like `test_render_specialist_payload_sidecar_counts_inline_diff_context` and `test_render_plan_review_payload_sidecar_counts_cursor_plan_and_feature` assert totals that exclude architectural content. Those tests will fail once the feature lands unless updated. **Suggested revision:** Include updating those existing payload sidecar tests (or patching architectural fixtures) in the plan’s `test_rendering.py` deliverable list. --- Prior-round accepted items (dynamic-slot difficulty threading, Claude launcher forwarding, plan-review payload telemetry, deferred docs-only gating, no control-char validation) are addressed in the current plan. No new gaps found on those paths beyond the omissions above.



### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:1402-1403
- **Concern**: Plan-review renderer does not thread difficulty into the architectural section. Scenario: A TRIVIAL plan-review subprocess receives --difficulty TRIVIAL, but render_plan_review_main still calls _architectural_guidelines_review_section() without args.difficulty, so the default fail-open path includes ARCHITECTURAL_GUIDELINES and violates the TRIVIAL plan-review acceptance criterion
- **Proposed resolution**: Call _architectural_guidelines_review_section(difficulty_value=args.difficulty) in render_plan_review_main and add a TRIVIAL plan-review renderer assertion.



