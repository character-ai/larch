## Plan

## Approach

Implement the three independent parts as one focused change.

1. Extend the existing agent tool-contract lint.
   - Add the issue-specified output-mandate and fail-closed detectors.
   - Add the separate, reason-bearing v2 suppression pragma.
   - Give each `Finding` its own message.
   - Restructure `scan_file` so the existing tool declaration check and the new output mandate check run independently.
   - Preserve the current file scope, frontmatter requirement, exit codes, and no-baseline policy.
2. Add focused regression tests for detection, disarming language, Read-tool independence, and suppression isolation.
3. Update both user-facing descriptions of the lint.
4. Insert the I-Ship-1 and G-Md-3 blocks byte-exact at their approved anchors.

Repository inspection found two current strict-JSONL agent prompts. Both already contain language matched by the proposed fail-closed detectors, so no agent prompt edits are expected.

## Files to modify/create

### UPDATED: python/larch/lint/lint_agent_tool_contract.py

- Replace the module docstring’s reserved-future-work sentence with the supplied description of the second check.
- Add `OUTPUT_MANDATE_MESSAGE`, `OUTPUT_MANDATE_SUPPRESSION_RE`, `OUTPUT_MANDATE_RES`, and `FAIL_CLOSED_RES` next to the existing finding and suppression constants, using the supplied code byte-exact.
- Add `message: str` to the frozen `Finding` dataclass.
- Add `first_output_mandate_line` and `has_fail_closed_language` next to `first_read_intent_line`, using the supplied implementations.
- Replace the early-return tail of `scan_file` with the supplied independent finding accumulation:
  - Keep malformed `tools:` declarations as tool failures.
  - Emit the v1 finding only for explicit Read-less lists with read intent and no v1 suppression.
  - Emit the v2 finding when read intent and a machine-output mandate coexist without fail-closed language or a v2 suppression.
  - Allow both findings for one file when both contracts fail.
- Construct every finding with the correct message.
- Print `finding.message` in `main`.
- Preserve exit codes 0, 1, and 2 and the existing non-recursive agent paths.

### UPDATED: python/tests/lint/test_lint_agent_tool_contract.py

- Keep all existing fixtures and assertions unchanged except for adjustments required by the new `Finding.message` field.
- Add `test_output_mandate_without_fail_closed_flagged`.
  - Use read intent followed by `Emit strict JSONL only.`
  - Assert one v2 finding at the mandate line with `OUTPUT_MANDATE_MESSAGE`.
- Add `test_output_mandate_with_never_invent_passes`.
  - Add the designated `NEEDS_DEEP`, never-invent, and Read-failure language.
  - Assert the v2 check is clean.
- Add `test_output_mandate_without_read_intent_passes`.
  - Assert a strict JSONL mandate alone does not trigger the check.
- Add `test_read_tool_granted_still_requires_fail_closed`.
  - Grant `tools: [Read]`.
  - Assert the v2 finding still appears and no v1 finding appears.
- Add `test_output_mandate_suppression_scopes_to_v2`.
  - Create a fixture that violates both checks.
  - Verify `lint-agent-output-mandate: ok <reason>` suppresses only v2.
  - Verify `lint-agent-tool-contract: ok <reason>` suppresses only v1.
- Retain the live-tree clean test to catch any shipped or dev-only agent prompt that needs fail-closed prose.

### UPDATED: docs/linting.md

- Expand the “Agent tool contract” table row to describe both independent checks:
  - explicit Read-less tool declarations paired with read intent;
  - machine-parsed-only JSON or JSONL mandates paired with read intent but no fail-closed instruction.
- Update the detailed `python/cli.py lint agent-tool-contract` paragraph.
  - Preserve current scope and frontmatter behavior.
  - Explain that granting `Read` does not disarm the output-mandate check.
  - Document `<!-- lint-agent-output-mandate: ok <reason> -->`.
  - Keep the existing v1 suppression documentation.
  - Keep the “no baseline by policy” sentence.

### UPDATED: ARCHITECTURAL_INVARIANTS.md

- Append the supplied `## Ship lifecycle` and I-Ship-1 block byte-exact after the I-Agent-1 paragraph.
- Place exactly one blank line between the existing paragraph and the new section.
- Do not modify the already-landed ship guard or its tests.
- Preserve the `### I-Ship-1:` heading shape so the invariant reader recognizes it.

### UPDATED: ARCHITECTURAL_GUIDELINES.md

- Insert the supplied G-Md-3 block byte-exact inside `## Documentation and Markdown`.
- Place it immediately after G-Md-2 and before `## Migration discipline`.
- Keep one blank line on each side of the new entry.
- Preserve the `### G-Md-3:` heading shape so guideline parsing and coverage indexing recognize it.

## Edge cases

- A file without leading frontmatter remains outside lint scope.
- A missing or scalar `tools:` declaration can still receive a v2 finding because v2 is independent of the tool declaration.
- A `tools: [Read]` declaration disarms v1 only.
- A file may emit both findings, each at its own first matching line and with its own message.
- Each suppression pragma affects only its matching check and requires a non-empty reason.
- Fail-closed wording anywhere in the prompt body disarms v2, as specified by `FAIL_CLOSED_RES`.
- A machine-output mandate without detected read intent remains clean.
- Existing malformed frontmatter tool lists still return exit code 2 rather than partial findings.

## Failure modes

- Retaining the current v1 early returns would silently skip v2 for unrestricted or Read-enabled agents.
- Reusing the v1 suppression regex for v2 would let one pragma hide an unrelated contract failure.
- Printing the global v1 message would misreport v2 findings.
- Broadening the regexes beyond the supplied detectors could create unapproved false positives.
- Reflowing either documentation block would violate the byte-exact acceptance requirement.
- Incorrect blank-line placement could fail the anchor and formatting acceptance checks.

## Testing strategy

Run only checks relevant to the changed files:

1. Run the focused lint tests:
   - `python3 -m pytest python/tests/lint/test_lint_agent_tool_contract.py`
2. Run the lint against the repository:
   - `python3 python/cli.py lint agent-tool-contract`
   - Confirm exit code 0 and no shipped or dev-only agent findings.
3. Verify architectural readers:
   - `python3 python/cli.py architectural-invariants read`
   - Confirm the output includes I-Ship-1.
   - Run the corresponding architectural-guidelines read command exposed by `python/cli.py` and confirm it includes G-Md-3.
4. Run Python validation for the changed module and tests:
   - `make py-lint`
   - `make py-test`
5. Run the repository’s relevant Markdown lint on `docs/linting.md`, `ARCHITECTURAL_INVARIANTS.md`, and `ARCHITECTURAL_GUIDELINES.md`.
6. Compare the inserted I-Ship-1 and G-Md-3 blocks with the issue text byte-for-byte and verify the required blank-line anchors.

## Acceptance

Run only checks relevant to the changed files:

1. Run the focused lint tests:
   - `python3 -m pytest python/tests/lint/test_lint_agent_tool_contract.py`
2. Run the lint against the repository:
   - `python3 python/cli.py lint agent-tool-contract`
   - Confirm exit code 0 and no shipped or dev-only agent findings.
3. Verify architectural readers:
   - `python3 python/cli.py architectural-invariants read`
   - Confirm the output includes I-Ship-1.
   - Run the corresponding architectural-guidelines read command exposed by `python/cli.py` and confirm it includes G-Md-3.
4. Run Python validation for the changed module and tests:
   - `make py-lint`
   - `make py-test`
5. Run the repository’s relevant Markdown lint on `docs/linting.md`, `ARCHITECTURAL_INVARIANTS.md`, and `ARCHITECTURAL_GUIDELINES.md`.
6. Compare the inserted I-Ship-1 and G-Md-3 blocks with the issue text byte-for-byte and verify the required blank-line anchors.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_added: 165
diff_deleted: 20
mechanical_churn: false
diff_lines: 185
