### FINDING_1: Shell harnesses still pin the old mandatory separator
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan still leaves several structural shell checks and related references pinned to `MANDATORY — READ ENTIRE FILE`, so the colon migration will fail CI even if the main markdown files change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/scripts/test-brainstorm-prompts.sh` and update the grep to the colon form (or match the full readability directive line)
  - From Codex-Arch: Add the missing harnesses, at least `scripts/test-review-structure.sh`, `scripts/test-research-structure.sh`, `scripts/test-implement-structure.sh`, `scripts/test-implement-step8-exit3-first-fixer.sh`, and `scripts/test-plan-adequacy-audit.sh`, to the mandatory update set.
  - From Cursor-Innovation: Add `### UPDATED: scripts/test-implement-structure.sh` with colon-form pinned literals, and run the harness in Testing strategy.
  - From Cursor-Pragmatic: List every harness that pins MANDATORY — READ ENTIRE FILE (or substring) and add ### UPDATED rows to switch pins to the colon form
  - From Codex-Pragmatic: Add the omitted harness files to the same sweep and retarget their literals to the colon form in the same change.
  - From Codex-Requirements: Extend the sweep to those harnesses and reference files, or move the separator update into their generators, and change the pinned literals to `MANDATORY: READ ENTIRE FILE`


### FINDING_2: Pre-rendered reviewer bodies need regeneration and manifest coverage
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The pre-rendered reviewer prompt bodies and their manifest/check path are still treated as editable outputs, so regenerated bodies can drift and `generate check` can fail in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: agents/pre-rendered/*.txt` and update the grep to the colon form (or match the full readability directive line)
  - From Codex-Innovation: Add `agents/pre-rendered/.manifest` to the plan and regenerate it with the body files
  - From Cursor-Requirements: Promote regeneration to firm steps: after agent/template edits run python3 python/cli.py generate pre-rendered-reviewer-prompts and python3 python/cli.py generate check; list agents/pre-rendered/.manifest as UPDATED via regeneration


### FINDING_4: Em-dash-output lint needs a scrubbed baseline
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Lint Scope Auditor
- **Severity**: blocking
- **Concern**: The new lint is being enabled before the current tree's existing U+2014 output sites are explicitly scrubbed or gated behind a prerequisite merge, so acceptance would fail on the baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State explicitly that this change merges after the scrub issues and that `lint em-dash-output` must pass on a scrubbed tree
  - From Cursor-Pragmatic: Add an explicit approach step plus firm file coverage to replace em dashes in scoped output literals (print, dict values later printed, f-string parts in those calls, _emit/_diag paths) across python/larch/** before enabling the hook in make lint
  - From Cursor-Requirements: Add an explicit prerequisite in Approach/Testing: prior em-dash scrub issues must land first, or this PR must scrub every in-scope print/out.append literal before enabling lint-em-dash-output; gate acceptance on python3 python/cli.py lint em-dash-output exit 0 on the merged baseline
  - From Cursor-dyn-Lint Scope Auditor: Add explicit scrub deliverables for every in-scope Python output call and markdown status-print literal still containing U+2014, or state in Testing strategy that prerequisite scrub issues must merge first and list the residual paths this lint excludes until then.


### FINDING_5: Closure-growth scanner still matches the old separator
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements, Codex-dyn-Lint Scope Auditor
- **Severity**: blocking
- **Concern**: The mandatory-directive scanner and its fixtures still accept the old em-dash/hyphen form, so colon-form directives will be undercounted or break the ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add `python/larch/lint/lint_skill_closure_growth.py` and `python/tests/lint/test_lint_skill_closure_growth.py` to the firm update set, switch the directive regex to the colon form, and refresh any baseline data if the counted set changes.
  - From Cursor-Innovation: Add `### UPDATED: python/larch/lint/lint_skill_closure_growth.py` to tighten `MANDATORY_DIRECTIVE_RE` to the colon form and update `python/tests/lint/test_lint_skill_closure_growth.py` fixtures.
  - From Codex-Innovation: Update the shared mandatory-directive regex and its tests to accept `MANDATORY:` before `READ ENTIRE FILE`, then regenerate the closure baseline if the count changes
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/lint/lint_skill_closure_growth.py and ### UPDATED: python/tests/lint/test_lint_skill_closure_growth.py to align the regex and fixtures with the colon directive
  - From Codex-Requirements: Add `python/larch/lint/lint_skill_closure_growth.py` and `python/tests/lint/test_lint_skill_closure_growth.py` to the change set, switch the regex to accept the colon form, and refresh any fixtures or baselines that pin the old separator.
  - From Codex-dyn-Lint Scope Auditor: Update the regex and its fixtures to accept the colon form, or explicitly exempt the new colon directive from closure-growth accounting if that metric should stay on the old shape.


### FINDING_6: Generated reviewer agents should not be hand-edited
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The four auto-generated reviewer agent files are still being treated as hand-edited `### UPDATED` targets instead of outputs regenerated from `skills/shared/reviewer-templates.md`, which invites changes that `generate check` will reject.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep only `### UPDATED: skills/shared/reviewer-templates.md` for generated bodies; add Testing strategy steps to run `python3 python/cli.py generate code-reviewer-agent`, the three sibling reviewer generators, `pre-rendered-reviewer-prompts`, and `generate check`.
  - From Cursor-Requirements: Remove those four paths from hand-edit UPDATED; add a firm step after reviewer-templates.md: run python3 python/cli.py generate code-reviewer-agent, reviewer-plan-fidelity-agent, reviewer-code-robustness-agent, reviewer-security-structure-tests-agent, then python3 python/cli.py generate check


### FINDING_8: Runtime sink coverage misses logging_util helpers
- **Reviewer(s)**: Cursor-dyn-Lint Scope Auditor, Codex-dyn-Lint Scope Auditor
- **Severity**: blocking
- **Concern**: The planned runtime sink list omits the main `logging_util` emit/diagnostic helpers, so visible output routed through them would never be scanned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Lint Scope Auditor: Extend AST call detection to `logging_util.emit`, `logging_util.emit_kv`, and `logging_util.diagnostic` (and/or any `logging_util.*` emission helper); add tests for diagnostic/emit paths with planted U+2014.
  - From Codex-dyn-Lint Scope Auditor: Add those wrapper names to the sink set, or resolve wrapper call chains before checking string literals.


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5b.py:168-268
- **Concern**: [SCOPE-REDUCTION] Output-lint acceptance conflicts with surviving python/larch print literals. Scenario: Plan acceptance requires `python3 python/cli.py lint em-dash-output` to pass on the current tree, and step 4 scopes `python/larch/**/*.py` output calls, but the firm file list only swaps MANDATORY directive separators. Dozens of runtime `print`/`_diag` strings still contain U+2014 (e.g. design_step5b.py, preflight.py, bootstrap.py, design_postplan.py). Wiring the lint as written fails CI immediately.
- **Proposed resolution**: Add an explicit scrub pass for all in-scope python/larch output literals (or narrow v1 lint scope and relax acceptance); do not wire CI until the tree is clean for the chosen scope.


### FINDING_1: Inline status-print templates bypass the em-dash lint
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The planned markdown em-dash scan covers `Print:` backtick literals and line-leading `⏩`, but inline orchestrator status-print templates like ``print `⏩ ... — ...` `` still fall through. That leaves the highest-traffic design/research skill prose able to emit U+2014 while the lint passes, and the step-5 gate text does not force markdown scrub coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Extend the markdown scanner to also flag em-dash inside inline \`print \`…\`\` backtick literals (and matching reference prose), or add an explicit firm scrub step for those literals in every listed skill/reference file`
  - From Cursor-Innovation: `Extend \`lint_em_dash_output.py\` to scan em-dash inside backtick status-print templates on lines matching \`print \`⏩\` (and equivalent \`Print:\` bodies), or add an explicit scrub requirement for those literals in the firm-listed skill/reference files before enabling CI.`
  - From Cursor-Innovation: `Reword step 5 to require scrubbing every in-scope emitted surface (Python sinks plus markdown status-print literals) or document that inline \`\`print \`⏩\` \`\` templates must be included in the scanner scope and scrub checklist.`
  - From Codex-Requirements: `Add scanner coverage for inline print or Print backticked status literals, at least for literals beginning with the existing status glyphs, and add a focused fixture`


### FINDING_2: Runtime sink coverage misses several output wrappers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The planned AST sink list still misses multiple operator-visible emission paths, including module-level breadcrumb dict values joined into `print()`, `_err()` stderr warnings, `_core_diagnostic`, and `BreadcrumbWriter.emit` call shapes. That lets U+2014 survive in runtime output even if the `print()`-site scrub passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Scrub those dict literals in the prerequisite pass and either treat known breadcrumb dict constants as in-scope output strings for the lint, or add a targeted regression that plants U+2014 in a dict value that is joined into a \`print()\` call and expect failure`
  - From Cursor-Arch: `Add \`_err(\` to the AST sink list (or treat it as an alias of \`print\` to stderr) alongside \`print\`, \`_diag\`, and \`logging_util.*\`; include a unit test for \`_err("… — …")\``
  - From Codex-Arch: `Add BreadcrumbWriter.emit call shapes used in the tree to lint-em-dash-output and cover them in test_lint_em_dash_output.py.`
  - From Cursor-Pragmatic: `Add \`_core_diagnostic\` (and any other thin stderr wrappers in \`python/larch/**\`) to the AST sink list, or require scrubbing every existing \`_core_diagnostic\` literal in the same prerequisite pass that clears \`print\`/\`logging_util.diagnostic\` sites.`
  - From Codex-Requirements: `Resolve logging_util sinks through imports from larch.core.logging_util and include BreadcrumbWriter.emit, with one focused regression fixture`


### FINDING_3: Closure scanner colon switch undercounts mandatory load directives
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Switching the closure scanner to colon-only matching without sweeping every loaded `MANDATORY READ ENTIRE FILE` trigger leaves the refreshed closure baseline undercounted. Existing SKILL.md files, nested references, and harness pins can still point at prompt sources that the scanner no longer sees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Make the firm sweep cover every MANDATORY READ ENTIRE FILE marker in closure-scanned sources, especially skills/design/SKILL.md, skills/implement/SKILL.md, skills/review/SKILL.md, skills/research/SKILL.md, and generated reviewer agent/template sources.`
  - From Codex-Innovation: `Make the firm sweep cover every scanner-relevant MANDATORY READ ENTIRE FILE load directive in the gated SKILL.md files and harness pins, then run lint skill-closure-growth before refreshing the baseline.`
  - From Codex-Pragmatic: `Add every closure-scanned MANDATORY READ ENTIRE FILE trigger file to the firm colon sweep, or defer the closure scanner exact-colon change until those trigger lines are migrated`
  - From Cursor-Requirements: `Add ### UPDATED rows for each reference above; replace MANDATORY — READ ENTIRE FILE with the colon form everywhere it appears, including nested load directives inside ship-pr-ci-exit-matrix.md and rebase-checkpoint-routing.md.`


### FINDING_4: Dev skill directive sweep still sits in optional scope
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The readability-preamble lint dynamically scans `.claude/skills/*/SKILL.md`, but the plan leaves those files under `MAY_UPDATE`. If they are skipped, existing dev skills keep the old separator and the colon-only regex reports missing directives, so the required lint fails or the tree stays partially unsanitized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Move the dev skill directive sweep from MAY_UPDATE to a firm UPDATED requirement or otherwise make the lint contract explicitly exclude those files.`
  - From Codex-Innovation: `Promote .claude/skills/*/SKILL.md to firm UPDATED, or add a firm sweep of every dynamic dev skill directive, including analyze-bugs.`
  - From Codex-Pragmatic: `Promote .claude/skills/*/SKILL.md to firm UPDATED scope or otherwise require every dynamic dev skill directive to use the colon form`
  - From Codex-Requirements: `Move .claude/skills/*/SKILL.md to firm UPDATED scope or list the concrete dev skill files, including analyze-bugs`


### FINDING_5: Python runtime scrub scope is too small for the em-dash output lock
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: The firm file list does not cover the `python/larch` runtime output sites that still contain U+2014, so enabling `lint em-dash-output` on merge can fail CI unless those prerequisite scrubs already landed. The current plan leaves too much runtime surface outside the explicit deliverable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: `Add a firm deliverable: either ### UPDATED rows for every in-scope python/larch output site, or an explicit mechanical scrub step with a grep-driven file list and a hard gate that prerequisite scrub PRs are merged before CI wiring lands.`


### FINDING_6: Markdown scope files are missing from the firm UPDATED list
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: Several `⏩`-prefixed markdown status-print literals still carry U+2014 but are not listed in the firm `### UPDATED` scope, so the markdown side of the em-dash lock can stay green while those emitted breadcrumbs remain unsanitized. The runtime mirror in `design_postplan.py` adds a second path that will also fail if the scrub is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: `Add ### UPDATED rows for all six markdown files; colon-replace every ⏩ status-print literal; keep python/larch mirrors in the runtime scrub deliverable above.`


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/**/*.py
- **Concern**: [SCOPE-REDUCTION] The co-land scrub branch still has no firm file list for existing runtime U+2014 output.. Scenario: Approach step 5 allows enabling `lint em-dash-output` after prerequisite merges OR an in-PR scrub, but `### UPDATED`/`### NEW` only cover directive-separator edits plus the lint itself. Dozens of `python/larch/**` `print`/`_diag`/`logging_util.diagnostic` literals still contain U+2014 (e.g. design_step5b.py, preflight.py, bootstrap.py, design_postplan.py). If scrub PRs are not merged first, implementers can wire CI and hit immediate red with no enumerated repair surface.
- **Proposed resolution**: Make prerequisite scrub a hard gate (drop the in-PR OR), or add an explicit `### UPDATED` batch for every in-scope runtime output file that still contains U+2014 before CI enablement, and keep acceptance on `python3 python/cli.py lint em-dash-output` passing on the merged tree.


