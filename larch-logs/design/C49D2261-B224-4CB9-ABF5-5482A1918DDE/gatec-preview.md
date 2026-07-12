## Final Design Plan

## Plan

## Approach

Add the two bug-fix review questions as prompt-side guidance and pin their exact text in the existing invariant harness. Do not add runtime gating, title/path parsing, or new harness machinery.

The plan-review instruction applies only when both conditions hold:

- The source issue carries `[BUG]`.
- The firm plan files touch the recovery surfaces named by G-Fix-2.

It requires either a named offline harness or test case that replays the failure, or an explicit one-line no-repro justification.

The diff-review instruction applies to `[BUG]` fixes in the live generic diff-specialist path. It asks reviewers to classify the change as class-wide or instance-only and requires sibling sites checked, or an explicit statement that a grep found none. Keep the shared template wording for Code Reviewer consumers, but inject the same rule into the runtime specialist wrapper used by `/review` and `/implement` Step 5.

## Files to modify/create

### UPDATED: ARCHITECTURAL_GUIDELINES.md

- Add `G-Fix-2` after `G-Fix-1`, the next free ID in the Fix discipline section.
- Match the file’s existing `### G-…`, `Why`, and `Deviate when` grammar so the architectural-guideline reader and coverage indexer recognize it.
- State that a recovery-path bug fix must add or extend an executable offline harness or test case that replays the failure and passes with the fix.
- Name the recovery surfaces: implement steps, ship and postmerge routing, bgjob, design publish and resume, CI fixer, and stall classifiers.
- Define close criteria as reproduced-then-passed, not merely merged or CI-green.
- Preserve the live-vendor or GitHub-state exception: the PR must explain why no harness can replay the failure and name the manual verification performed.

### UPDATED: python/larch/rendering/rendering.py

- Add a concise advisory checklist instruction to the common `render_plan_review_main` scaffold so static and dynamic plan reviewers receive the same rule.
- State that when the bound source issue carries `[BUG]` and the firm `### NEW:` / `### UPDATED:` / `### REWRITTEN:` plan file set touches a named G-Fix-2 recovery surface, the plan must name the replaying harness or test case, or include a one-line no-repro justification.
- Keep the instruction scoped to the proposed firm file set; do not imply that all bugs, unrelated files, or non-bug issues require a recovery reproduction.
- Add the matching `[BUG]` class-or-instance instruction to `_specialist_tagging()` for generic diff mode, the shared runtime wrapper used by `render specialist` and the live `review.panel` paths.
- Require the runtime specialist prompt to ask whether the fix addresses the class or only an instance, and to name sibling sites checked or explicitly state that a grep for the defect pattern found none.
- Keep both additions advisory only. Do not add parsing, issue-title detection, recovery-path classifiers, or hard gates.

### UPDATED: skills/shared/reviewer-templates.md

- Add one `[BUG]`-specific bullet under `## Adapt scope`.
- Use the same class-or-instance wording as the generic specialist wrapper: name sibling sites checked, or state that a grep for the defect pattern found none.
- Keep this as canonical shared reviewer text for Code Reviewer and generated-reviewer consumers.
- Do not require changes at unrelated siblings; existing scope and proportionality rules continue to determine whether a sibling is in scope or needs follow-up.

### UPDATED: agents/code-reviewer.md

- Regenerate the checked-in Code Reviewer from `skills/shared/reviewer-templates.md` using `python3 python/cli.py generate code-reviewer-agent`.
- Confirm the generated agent contains the canonical `[BUG]` class-or-instance instruction and has no hand-edited divergence.

### UPDATED: scripts/test-prompt-template-invariants.sh

- Change the feature fixture to contain a `[BUG]` source title/body.
- Copy or write that feature fixture under `$design_tmpdir` (for example, `$design_tmpdir/feature-description.txt`) before the `render plan-review` smoke invocation, matching the existing staging of `plan.txt`.
- Pass the staged in-tree fixture with `--feature-file "$design_tmpdir/feature-description.txt"`; do not pass a `$TMP`-rooted feature-file path, because `render plan-review` rejects feature files outside `DESIGN_TMPDIR`.
- Rewrite the plan fixture into firm plan grammar with at least one `### UPDATED:` entry naming a G-Fix-2 recovery-surface file, while deliberately omitting any reproduction, harness, test-case, or no-repro line.
- Keep the fixture plan copied under `$design_tmpdir` before rendering, preserving the existing prompt-file validation setup.
- Add exact textual `assert_contains` pins for:
  - the G-Fix-2 executable-reproduction guideline text;
  - the rendered plan-review harness-or-one-line-no-repro checklist;
  - the canonical Code Reviewer/template class-or-instance wording;
  - the rendered generic diff-specialist class-or-instance instruction.
- Exercise the runtime diff-specialist path with `render specialist --mode diff --agent-file agents/reviewer-correctness.md` and assert against that rendered output, rather than relying only on the template or generated Code Reviewer file.
- Keep assertions textual. Do not simulate reviewer judgment, validate an actual plan-review finding, or introduce a behavioral merge gate.

## Edge cases

- A `[BUG]` issue that changes ordinary product or documentation files must not imply that recovery-specific reproduction guidance applies.
- A recovery-path feature not sourced from a `[BUG]` issue must not be described as subject to the bug-only plan-review checklist.
- A valid live-state exception satisfies the plan-review prompt when the plan supplies a one-line no-repro reason and names manual verification.
- A diff reviewer may find no sibling sites; the runtime prompt must accept an explicit grep-found-none result.
- The generic specialist wrapper must deliver the class-or-instance question to the correctness, edge-cases, and testing panel paths without requiring hand-maintained panel-agent edits.
- Generated Code Reviewer content must remain synchronized with its canonical template.

## Failure modes

- Delivering the class-or-instance question only through `agents/code-reviewer.md` would leave the live specialist panel without the required review check.
- Pinning only the canonical template or generated agent could allow the runtime specialist render path to regress unnoticed.
- Passing a `$TMP`-rooted `--feature-file` would cause `render plan-review` to reject the smoke invocation before prompt rendering; the `[BUG]` feature fixture must be staged under `$design_tmpdir`.
- Omitting `--feature-file` or using an informal plan fixture would fail to exercise the `[BUG]` plus recovery-surface plan-review scenario.
- Overbroad wording could make every bug plan appear to require a recovery harness.
- Vague wording could let a plan claim “tests added” without naming the replaying case.
- A malformed G-Fix heading could prevent the coverage indexer from seeing the new guideline.

## Testing strategy

- Run `make test-prompt-template-invariants`; verify its plan-review smoke stages both the `[BUG]` feature fixture and firm recovery-surface plan under `DESIGN_TMPDIR`, then pins the rendered harness-or-one-line-no-repro checklist.
- Verify the same harness runs the specialist smoke against rendered `agents/reviewer-correctness.md` generic diff output and pins the class-or-instance instruction.
- Run `python3 python/cli.py generate code-reviewer-agent` and the repository generator check for `agents/code-reviewer.md`.
- Run focused rendering tests covering `render plan-review` and `render specialist` prompt assembly, including generic diff tagging.
- Run `python3 -m pytest python/tests/issue/test_learn_from_bugs.py -q -k architectural` to confirm the committed guideline remains visible to both the reader and coverage indexer.
- Run Markdown and changed-file lint checks for `ARCHITECTURAL_GUIDELINES.md`, `skills/shared/reviewer-templates.md`, and `agents/code-reviewer.md`.

difficulty: MODERATE
diff_added: 44
diff_deleted: 3
mechanical_churn: false
diff_lines: 47
