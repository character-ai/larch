### FINDING_1: Diff-review prompt does not reach the live specialist panel
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Bug Prompt Contract
- **Severity**: major
- **Concern**: The class-or-instance question is planned only in the generated Code Reviewer template and `agents/code-reviewer.md`. The primary `/review` diff and `/implement` Step 5 paths dispatch `review.panel` specialists through `render specialist`, using hand-maintained reviewer agents that do not inherit the Code Reviewer `## Adapt scope` content. As a result, the new question may be absent from the production diff-review path, leaving acceptance criterion 2 and the G-Fix-1 operational check unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the existing ### UPDATED: python/larch/rendering/rendering.py work, also add the advisory [BUG] class-or-instance paragraph to _specialist_tagging for generic diff mode (same pattern as the plan-review checklist), or add the bullet to the three panel agent files and regenerate pre-rendered reviewer bodies; keep reviewer-templates.md as canonical text but do not treat code-reviewer regen alone as sufficient
  - From Cursor-Innovation: Also inject the same concise `[BUG]` class-or-instance checklist in `python/larch/rendering/rendering.py` on the specialist diff path (`_specialist_tagging` or `_render_specialist_text`), matching the plan-review addition in `render_plan_review_main`; keep `skills/shared/reviewer-templates.md` as the pinned canonical text.
  - From Cursor-Pragmatic: Add the [BUG] class-or-instance bullet to the shared specialist diff wrapper in rendering.py (for example _specialist_tagging or _render_specialist_text); keep reviewer-templates.md and code-reviewer regeneration for code-reviewer consumers; pin the rendered specialist smoke output in scripts/test-prompt-template-invariants.sh
  - From Cursor-Requirements: Add the `[BUG]` class-or-instance bullet to `python/larch/rendering/rendering.py` `_specialist_tagging` generic diff text (minimum single injection site), or add firm `### UPDATED:` rows for the three hand-maintained specialists; extend `scripts/test-prompt-template-invariants.sh` with a `render specialist --mode diff` smoke assert, not only a canonical-template grep
  - From Cursor-dyn-Bug Prompt Contract: Add runtime delivery in `python/larch/rendering/rendering.py` `_specialist_tagging()` for generic diff mode (same file already slated for plan-review text), or update the three `review.panel` agent files and run `python3 python/cli.py generate pre-rendered-reviewer-prompts`. Keep canonical wording in `skills/shared/reviewer-templates.md`, but pin the rendered specialist output with `agents/reviewer-correctness.md` in `scripts/test-prompt-template-invariants.sh.


### FINDING_2: Invariants harness does not pin the runtime specialist prompt
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Bug Prompt Contract
- **Severity**: minor
- **Concern**: The planned harness assertions can target canonical template text, `agents/code-reviewer.md`, or a non-dispatched reviewer fixture rather than the `render specialist` output used by the live `review.panel` path. CI could therefore pass while the correctness, edge-cases, and testing specialist prompts omit the new class-or-instance question.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the class-or-instance string on render specialist --agent-file agents/reviewer-correctness.md (or all three panel agents), or assert the new _specialist_tagging paragraph when that path is chosen
  - From Cursor-Innovation: Add `assert_contains` against `python3 python/cli.py render specialist --agent-file agents/reviewer-correctness.md --mode diff ...` output (or the post-injection equivalent), not only the canonical template file.
  - From Cursor-Pragmatic: Assert the exact class-or-instance question in $specialist_out from the existing render specialist smoke block, not only in templates or code-reviewer source files
  - From Cursor-Requirements: Add the `[BUG]` class-or-instance bullet to `python/larch/rendering/rendering.py` `_specialist_tagging` generic diff text (minimum single injection site), or add firm `### UPDATED:` rows for the three hand-maintained specialists; extend `scripts/test-prompt-template-invariants.sh` with a `render specialist --mode diff` smoke assert, not only a canonical-template grep
  - From Cursor-dyn-Bug Prompt Contract: Add runtime delivery in `python/larch/rendering/rendering.py` `_specialist_tagging()` for generic diff mode (same file already slated for plan-review text), or update the three `review.panel` agent files and run `python3 python/cli.py generate pre-rendered-reviewer-prompts`. Keep canonical wording in `skills/shared/reviewer-templates.md`, but pin the rendered specialist output with `agents/reviewer-correctness.md` in `scripts/test-prompt-template-invariants.sh.


### FINDING_4: Plan-review fixture does not exercise the `[BUG]` scope anchor and recovery-surface condition
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Bug Prompt Contract
- **Severity**: minor
- **Concern**: The harness updates the feature fixture to contain `[BUG]` but does not pass it to `render plan-review`; additionally, the fixture plan remains informal instead of using a firm `### UPDATED:` recovery-surface path without a reproduction line. Textual checklist pins could therefore pass without exercising the dual-condition acceptance scenario.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass `--feature-file "$feature_file"` (and copy the fixture plan into `$design_tmpdir` as today) in the plan-review render smoke block.
  - From Cursor-Pragmatic: Add --feature-file "$feature_file" to the render plan-review invocation; set feature_file text to a [BUG] title/body and keep the recovery-surface plan fixture without a repro line
  - From Cursor-Requirements: Pass `--feature-file` with `[BUG]` feature text; rewrite the fixture plan with at least one `### UPDATED:` recovery-surface path and no harness/repro line; keep textual `assert_contains` on the rendered plan-review output
  - From Cursor-dyn-Bug Prompt Contract: Write `$TMP/feature.txt` with `[BUG]` text, pass `--feature-file "$feature_file"`, and reshape `$plan_file` with a `### UPDATED:` heading on a named recovery surface while omitting any reproduction line; keep assertions textual on the rendered prompt only

### FINDING_1: Plan-review fixture is outside the design temporary directory
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan-review smoke harness passes `--feature-file` from `$TMP` without staging it under `design_tmpdir`. `render plan-review` rejects feature-file paths outside `DESIGN_TMPDIR`, so the invocation exits with status 2 before rendering the prompt or exercising the new assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Copy or write the `[BUG]` feature fixture into `$design_tmpdir` (for example `feature-description.txt`) before `render plan-review`, mirroring the existing `plan.txt` copy; pass that in-tree path to `--feature-file`
  - From Cursor-Requirements: Copy or create the [BUG] feature fixture under $design_tmpdir (for example cp "$feature_file" "$design_tmpdir/feature-description.txt") and pass --feature-file "$design_tmpdir/feature-description.txt" in the render plan-review invocation, matching how plan.txt is staged and how python/tests/rendering/test_rendering.py and plan_review_panel.py supply feature files

