### OOS_1: [OUT_OF_SCOPE] correctness: `mechanical_churn` drafter rule softened from MUST to MAY
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `flags.md:67` softened the drafter rule from “must still emit” to “emit” for `mechanical_churn: true`. The normative MUST for plan metadata authors was weakened.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] correctness: stale `parse-argv` script path in `flags.md:15`
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, dyn-dyn-flag-contract, dyn-dyn-closure-ratchet
- **Severity**: nit
- **Concern**: `flags.md:15` still cites nonexistent `skills/design/scripts/python/cli.py design parse-argv`. Runtime entrypoint is `python/cli.py design parse-argv`. Pre-existing docs bug, not introduced by this compression diff, but still misleading for operators tracing the parser.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Update the reference to the actual python/cli.py entrypoint or intended wrapper path
  - From dyn-dyn-flag-contract: **Suggested fix:** Repoint the line to `${CLAUDE_PLUGIN_ROOT}/python/cli.py design parse-argv` in a follow-up doc pass.

### OOS_3: [OUT_OF_SCOPE] correctness: cross-doc drift on `design_argv.py` implementation path
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-flag-contract
- **Severity**: latent
- **Concern**: `flags.md:28` now correctly cites `python/larch/design/design_argv.py`, but `skills/design/SKILL.md` still references `${CLAUDE_PLUGIN_ROOT}/python/design_argv.py` (lines 24 and 698). Pre-existing stale paths are amplified by the `flags.md` correction; readers following `SKILL.md` are sent to a nonexistent module location.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: **Suggested fix:** Align the `SKILL.md` implementation line with `python/larch/design/design_argv.py` in a follow-up (out of this prose-only scope).
  - From dyn-dyn-flag-contract: **Suggested fix:** Align `SKILL.md` positional-tail cross-reference with the `python/larch/design/design_argv.py` path.

### OOS_4: [OUT_OF_SCOPE] architecture: compressed flag bullets lost lazy-load pointers
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Compression removed inline pointers to `references/brainstorm.md` and `references/approval-gates.md` (and the #2930 Gate B note) from public flag bullets. Gate B and brainstorm semantics still load at need via `SKILL.md`, so this is a discoverability tradeoff, not a behavior regression; operators reading only compressed flag bullets lose lazy-load hints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: **Suggested fix:** Restore short `see references/...` clauses only if field experience shows agents missing Gate B or brainstorm detail during Step 0 reads.

### OOS_5: [OUT_OF_SCOPE] code-quality: per-flag bullets omit `run-params.json` recovery context
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Per-flag bullets for `--brainstorm` and `--per-round-approval` no longer name `run-params.json` or `write-run-params`; only the shared paragraph on line 26 does. Behavior is unchanged because Step 0 fences in `SKILL.md` enforce persistence, but a reader scanning only individual flag bullets gets less recovery context after subshell boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: **Suggested fix:** Optional one-token addition (`in run-params.json`) on those two bullets if you want bullet-level parity with `--partition` without much token cost.

### OOS_6: [OUT_OF_SCOPE] risk-integration: pre-existing `--` argv test coverage gap
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: `flags.md:28` adds normative `--` double-dash positional rules, and `_apply_double_dash` in `python/larch/design/design_argv.py` implements that path, but `python/tests/design/test_design_argv.py` still has no parametrized cases for `-- <issue>` or `-- <verbal>`. Pre-existing coverage gap; this diff documents behavior rather than introducing a new execution path, and the plan did not require new argv tests for prose-only work.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] risk-integration: unrelated implement run-log flush bundled in branch
- **Reviewer(s)**: dyn-dyn-flag-contract, dyn-dyn-closure-ratchet
- **Severity**: latent
- **Concern**: Commit `b03780440` adds implement run-log artifacts under `larch-logs/` unrelated to the prose-compress task (`flags.md` + baseline ratchet). Bundling operational artifacts into the same branch widens review surface outside the feature diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-flag-contract: **Suggested fix:** Drop or split that commit if the PR should stay density-only.

