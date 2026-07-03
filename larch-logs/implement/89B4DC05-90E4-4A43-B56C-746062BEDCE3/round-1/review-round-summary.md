# Review Round 1

- Mode: `diff`
- 3 accepted, 6 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Readability routing misses design/rendering manifest paths
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Relevant-checks routing for readability changes still keys off stale or incomplete paths, so edits to `python/larch/design/design_step2b.py`, `python/larch/rendering/rendering.py`, or `scripts/lint-readability-preamble.tsv` can skip `test_rendering.py`, `test-design-structure`, or `test-brainstorm-prompts`; one rule also still points at a nonexistent `python/rendering.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Add `test-design-structure` and `test-brainstorm-prompts` to the manifest/doc row, or merge that row with the readability rule at line 467. Add a direct-target test for `scripts/lint-readability-preamble.tsv`.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Add `scripts/lint-readability-preamble.tsv` to the new readability routing row, or expand the existing manifest row to include `test-design-structure` and `test-brainstorm-prompts`; add a direct-target test for that path.


### FINDING_4: Readability lint should require a mandatory anchor
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, dyn-dyn-skill-surface
- **Severity**: important
- **Concern**: The new coverage lint accepts bare or incidental mentions of `skills/shared/readability-style.md` instead of requiring the counted `MANDATORY — READ ENTIRE FILE ... readability-style.md` anchor, so a skill can pass without actually directing the orchestrator to load the style file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Require at least one orchestrator-anchor line match per non-exempt SKILL.md, matching manifest anchor semantics.
  - From codex-specialist-correctness: Check an anchored directive form, not just the path. Reuse that check for counted rows and per-skill coverage, and add negative tests for bare path mentions and non-MANDATORY lines.
  - From dyn-dyn-skill-surface: Extend `_check_skill_path_form` to require at least one line matching `_orchestrator_anchor(rel)` (or the dev/public path inside a `MANDATORY — READ ENTIRE FILE` prefix) on every non-exempt `SKILL.md`, and add a negative test fixture that fails on comment-only mentions.


### FINDING_5: Alias skills need the readability directive
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `/alias` still generates alias skills with only `allowed-tools: Skill` and no readability directive, so newly generated aliases will fail the lint and lose the restored style contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Update `alias_skill.generate_main` to emit the correct public or dev readability directive, or pass the target kind into the generator so it can choose `${CLAUDE_PLUGIN_ROOT}` vs `$PWD`. Add `Read` to generated `allowed-tools` if the alias must load the style file, and update `python/tests/core/test_alias_skill.py`.


