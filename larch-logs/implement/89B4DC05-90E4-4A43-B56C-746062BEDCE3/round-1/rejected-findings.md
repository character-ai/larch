### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Rendering default readability path needs a regression test
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: No focused test pins the default readability path after the move to `skills/shared/readability-style.md`, so a revert in `python/larch/rendering/rendering.py` could still pass current rendering tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add a test that omits `--readability-style-file` and asserts shared readability content or the resolved default path in the rendered prompt.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Step 2b drafter prompt should assert shared style embedding
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: `python/larch/design/design_step2b.py` only embeds readability when the shared file exists, and no test pins that shared path or embedded content; a wrong path or missing file can silently drop style guidance from drafter prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a compose_drafter_prompt test with a tmp skills/shared/readability-style.md marker and assert it appears in the prompt output.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Step 2b drafter prompt should test shared-style embedding
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: `python/larch/design/design_step2b.py` needs a focused assertion that the shared readability file is actually embedded, so a wrong path or missing file does not silently strip style guidance from the drafter prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a compose_drafter_prompt test with a tmp skills/shared/readability-style.md marker and assert it appears in the prompt output.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Brainstorm preamble read should be counted
- **Reviewer(s)**: dyn-dyn-skill-surface
- **Severity**: important
- **Concern**: The external-prompt substitution path in `skills/design/references/brainstorm.md` uses a soft `read ${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md` line that is not covered by any manifest `expected_count` row, so regressions to a bare repo-relative path or removal of the read step would go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-surface: Add an `external-prompt` or `orchestrator-inline` manifest row for the brainstorm preamble read line (or fold it into the counted MANDATORY anchor pattern), and pin the `${CLAUDE_PLUGIN_ROOT}` path in `scripts/test-design-structure.sh` or `test-brainstorm-prompts.sh`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

