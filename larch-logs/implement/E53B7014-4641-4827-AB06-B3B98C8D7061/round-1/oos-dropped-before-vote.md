### OOS_1: [OUT_OF_SCOPE] Review skill still enforces hard `wc -l` cap
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `scripts/test-review-structure.sh:60-62` still enforces a hard `wc -l <= 200` cap on `skills/review/SKILL.md`, the same class of line-count proxy this change removes for design. Pre-existing; out of scope for this child issue.

### OOS_2: [OUT_OF_SCOPE] Ratchet failure message names only `SKILL.md`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: On any non-zero exit from the ratchet (growth violation exit `1` or infrastructure/baseline error exit `2`), `scripts/test-design-structure.sh:58-60` prints only `skills/design/SKILL.md closure growth ratchet failed`, even when the violation is on a closure reference (for example `flags.md`) or when the baseline is corrupt/missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: surface stderr from the Python linter or use a message that names the ratchet generally (`design closure growth ratchet`) rather than only `SKILL.md`.

### OOS_3: [OUT_OF_SCOPE] `--skill` flag registration coupled to `allow_write`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: In `python/larch/lint/lint_skill_closure_growth.py:446-451`, `--skill` is registered only when `allow_write=True`, so `report_main()` cannot filter by skill even though docs describe `--skill` as a check-mode feature. This matches the plan today but couples unrelated flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: register `--skill` unconditionally and keep the `--write`+`--skill` rejection in `main()` only.

### OOS_4: [OUT_OF_SCOPE] Missing structural pin for ratchet invocation string
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The new ratchet call in `scripts/test-design-structure.sh:56-57` correctly uses `python3 "$ROOT/python/cli.py"` (not `CLI_PY` / `python/larch/cli.py`), but the harness does not structurally pin that invocation string. A future edit to `$CLI_PY` would silently drop the ratchet while the harness still passes, which is the exact failure mode called out in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a `contains` pin for the `python/cli.py lint skill-closure-growth --skill design` literal, mirroring other structural guards in this file.

### OOS_5: [OUT_OF_SCOPE] Blank-line deletion test lacks end-to-end `main()` assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: In `python/tests/lint/test_lint_skill_closure_growth.py:249-258`, `test_blank_line_only_deletion_leaves_content_tokens_unchanged` asserts scan-level metric equality only; it does not call `main()` after baseline write to prove the ratchet CLI exits `0` on a blank-line-only diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend the test with `write_baseline_from_live()` + blank-line deletion + `assert scg.main([...]) == 0` for end-to-end acceptance.

### OOS_6: [OUT_OF_SCOPE] Missing edge-case fixtures for all-blank and no-trailing-newline files
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Plan edge cases for all-blank files (zero content tokens) and files without a trailing newline (stable content-token output) have no dedicated fixtures. Low regression risk given `_content_text()` simplicity and adjacent coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optional micro-fixtures if you want explicit edge-case documentation in the suite.

---

**Merge notes (brief):** `cursor-specialist-correctness` FINDING_1–9 are plan-verification affirmations with no distinct actionable fix; they are omitted as separate blocks. The slot is attributed on FINDING_2 (`[OUT_OF_SCOPE]`). The sole in-scope actionable concern is FINDING_13 from `codex-specialist-edge-cases` (raw-token baseline gaming). OOS items from `cursor-specialist-edge-cases` and `cursor-specialist-testing` are kept separate because each needs a different fix or targets a different code path.

