### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/checks.py:2147-2205
- **Concern**: Fast-fail on policy rejection still leaves `run_lint_fix` on the `codex_rc != 0` branch, so post-dispatch delta capture and `no-changes` never run. Post-dispatch logic at lines 2206+ executes only when a tier returns exit 0. If Codex applies file edits and then triggers a blocked `exec_command`, fast-fail returns non-zero, `coder_tool` stays unset, and `review_and_fix.py` routes `main-agent-required` to a full Step 5 stall even though lint may already be fixed on disk.. Scenario: After a policy-rejection marker in `${output}.diag`, still run the existing post-dispatch tracked/untracked delta probe (or treat policy rejection like a salvageable non-success) before returning `main-agent-required`; preserve `applied` / `no-changes` when workspace edits exist and only the verification shell was blocked.
- **Proposed resolution**:

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:45-53
- **Concern**: Codex appendix is appended after the shared prompt tail, so the Codex-only instructions come after the FIXED/UNFIXABLE contract.. Scenario: The existing `_compose_prompt` tail in `python/checks.py:1451-1480` ends with the result-shape instructions. Concatenating `_codex_lint_fix_prompt_appendix(site)` afterward moves those rules away from the prompt tail. The new smoke test only checks for marker presence, so this regression could ship even though Codex may treat the appendix as the last instruction instead of the result contract.
- **Proposed resolution**: Insert the Codex appendix before the result-shape section, or split `_compose_prompt` into body and tail and insert the appendix between them. Add a test that the FIXED/UNFIXABLE block remains the final prompt section.
