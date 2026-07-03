# Review Round 2

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Readability preamble lint accepts soft path mentions
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: `python/larch/lint/lint_readability_preamble.py` still treats backticked readability-style path mentions as sufficient, so incidental mentions can satisfy the guard even when the required `MANDATORY — READ ENTIRE FILE` directive is absent and the orchestrator may skip loading `readability-style.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Apply _ORCH_STYLE_ANCHOR_RE to _count_orchestrator_directives and _check_skill_path_form; add a backtick-only soft-mention regression test.
  - From codex-specialist-correctness: Match the full mandatory directive shape, or at least require `MANDATORY` plus `READ ENTIRE FILE` on the same counted line. Add a regression test for a non-mandatory backticked path followed by `.**`.
  - From codex-specialist-edge-cases: Make the counted needle or regex require the full mandatory directive shape, including `**MANDATORY — READ ENTIRE FILE` and the correct path form, and add a regression test for a non-mandatory line that still contains `` `<path>`.** ``.
  - From codex-specialist-testing: Match the full mandatory directive shape, or a strict regex that includes `MANDATORY — READ ENTIRE FILE` and the correct path form; add a negative test for a non-mandatory sentence ending in ``readability-style.md`.**``.


### FINDING_3: /im frontmatter cannot load the mandatory style read
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: `skills/im/SKILL.md` now requires reading `skills/shared/readability-style.md`, but its frontmatter only allows `Skill`, so `/im` cannot load the file before following the directive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add `Read` to `skills/im/SKILL.md` allowed tools, and consider extending the readability lint to fail any `SKILL.md` that has this directive but lacks a permitted file-read path.


