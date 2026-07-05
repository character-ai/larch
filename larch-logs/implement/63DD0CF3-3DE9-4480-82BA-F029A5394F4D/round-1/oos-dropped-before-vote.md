### OOS_1: [OUT_OF_SCOPE] remaining runtime emitters and heuristic boundaries still bypass coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-lint-scope
- **Severity**: important
- **Concern**: Other runtime emitters and heuristic boundaries outside the current lint surface still allow em dashes or misclassification, including timing labels, stderr wrappers, breadcrumb sinks, prompt constants, and composed output strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend lint to subprocess argv literals or scrub remaining timing labels in a follow-up.
  - From cursor-specialist-edge-cases: Add _plain_diagnostic or stderr wrapper sinks in a follow-up scrub.
  - From cursor-specialist-edge-cases: Narrow detection to assignments from logging_util.BreadcrumbWriter().
  - From cursor-specialist-edge-cases: Narrow BreadcrumbWriter detection to construction patterns or explicit variable names
  - From cursor-specialist-edge-cases: Follow-up scrub only if timing surfaces emit em dashes to operators
  - From cursor-specialist-edge-cases: Scrub constants and add prompt-constant coverage in a follow-up pass
  - From dyn-dyn-lint-scope: Only string literals and f-string constant parts in sink calls are checked; variables built elsewhere and passed to `print`/`logging_util.emit`/`sys.stdout.write` are ignored. The plan accepts this first-pass limit, but it leaves a permanent hole for refactored or composed output strings.
  - From dyn-dyn-lint-scope: Tests cover `logging_util.emit` and `logging_util.diagnostic` but not `logging_util.emit_kv`, `sys.stdout.write`/`sys.stderr.write`, imported `emit`/`diagnostic`, or `_plain_diagnostic`, even though those sinks are documented in `docs/linting.md` and partially implemented. Missing coverage makes the bypasses above easier to reintroduce.

### OOS_2: [OUT_OF_SCOPE] shell/status examples and canonical docs still carry em dashes
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-lint-scope
- **Severity**: latent
- **Concern**: Shell breadcrumbs and canonical docs examples outside the current lint surface still carry em dashes, so copying them can reintroduce the old separator without a lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend lint to shell printf status lines or scrub separately; out of this PR's declared scope.
  - From cursor-specialist-testing: Add rendering out.append to sinks or scrub at template source; pre-existing outside plan scope.
  - From cursor-specialist-testing: Update examples to colon form or add non-fenced lint coverage if examples are treated as canonical output.
  - From dyn-dyn-lint-scope: The shared contract still documents prose payloads with a ` — ` separator and fenced examples using em dashes, while the compact `/implement` skip format explicitly omits that separator (`skills/shared/progress-reporting.md:75`). That predates this branch (the file is unchanged in the diff) and can keep models copying em-dash skip lines from the canonical reference.
