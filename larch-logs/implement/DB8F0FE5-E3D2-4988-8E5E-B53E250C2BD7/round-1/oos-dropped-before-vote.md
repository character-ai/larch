### OOS_1: [OUT_OF_SCOPE] `_format_relocation_key` duplicates `format_key`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `_format_relocation_key` in `python/lint_subprocess_via_runner.py:392-395` and `python/lint_env_via_config_constant.py:543-545` duplicates `format_key` with no functional benefit, adding minor maintenance noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove _format_relocation_key and call format_key in error messages.

### OOS_2: [OUT_OF_SCOPE] Check mode lacks relocation-aware matching
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Check mode in both AST ratchet linters still matches exact `(file, …)` keys only; relocated code fails pre-commit until `--write` refreshes baseline paths. This matches plan scope (`--write` only) but preserves the operator footgun that triggered ST-5599: after a package move, check mode keeps failing until someone runs `make regen-subprocess-via-runner-baseline` / `make regen-env-via-config-constant-baseline` (now viable without `--initial-reason`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Optional: add check-mode relocation hint per plan (optional item).
  - From cursor-specialist-edge-cases-output.txt: Document that package moves require both ratchet --write invocations before pre-commit check mode passes.

### OOS_3: [OUT_OF_SCOPE] Duplicated relocation write logic across both linters
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Relocation write logic in `python/lint_subprocess_via_runner.py:404-464` is duplicated in `python/lint_env_via_config_constant.py` with identical control flow. Future edits to ambiguity rules or relocation-key shape may be applied to one linter and missed in the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Extract shared relocation-resolution helper when a third consumer appears or during the next touch of both files.

### OOS_4: [OUT_OF_SCOPE] Duplicate-live ambiguity tests lack bare `--write` symmetry
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: In `python/test_lint_subprocess_via_runner.py:275-291` and `python/test_lint_env_via_config_constant.py:380-396`, duplicate-live ambiguity tests only assert exit `2` with `--initial-reason`, while duplicate-old tests assert both bare `--write` and `--initial-reason`. Behavior is still guarded because a regression that skipped ambiguity would exit `0`; this is weaker symmetry, not a coverage hole for the new path.

### OOS_5: [OUT_OF_SCOPE] No test for file move plus `qualified_symbol` rename as new debt
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test covers the plan edge case where a file is moved and `qualified_symbol` is renamed, which should count as new debt. Relocation keys include `qualified_symbol`, so behavior should be correct; an explicit negative test would lock that contract but is not plan-required.

---

**Subsumed inputs (not emitted as separate findings):** FINDING_7 through FINDING_11 from `cursor-specialist-testing-output.txt` are positive plan-traceability and coverage attestations, not actionable defects. FINDING_15 from `codex-generalist-output.txt` duplicates FINDING_1 and was merged there.

