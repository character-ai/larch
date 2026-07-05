### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:219-230
- **Concern**: Planned markdown lint scans only `Print:` backtick literals and line-leading `⏩`, not inline orchestrator `print \`⏩ … — …\`` instructions. Scenario: At least 19 such literals across design/research skills and references (e.g. `print \`⏩ 1d.5: brainstorm — skipped\``) are copied verbatim into operator chat; `lint em-dash-output` passes while live skip breadcrumbs still emit U+2014
- **Proposed resolution**: Extend the markdown scanner to also flag em-dash inside inline `print \`…\`` backtick literals (and matching reference prose), or add an explicit firm scrub step for those literals in every listed skill/reference file



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5b.py:68-121
- **Concern**: Module-level breadcrumb dict values are emitted but excluded from the planned AST sink rules. Scenario: `_STEP5B_SKIP_BREADCRUMBS` strings flow into `OOS_SKIP_BREADCRUMB=` KV output via `print("\n".join(wrapper_rows))`; the planned test case “non-output Python string containing U+2014 does not fail” exempts them, so prerequisite scrub can miss them and the lint cannot catch regressions
- **Proposed resolution**: Scrub those dict literals in the prerequisite pass and either treat known breadcrumb dict constants as in-scope output strings for the lint, or add a targeted regression that plants U+2014 in a dict value that is joined into a `print()` call and expect failure



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/state/bootstrap.py:82-83
- **Concern**: Planned Python sink list omits the repo-wide `_err()` stderr helper used for operator-visible warnings. Scenario: `_err()` is `print(message, file=sys.stderr)`; call sites such as `agent_voters.py:353`, `_auth.py:703-705`, and `issue_block.py:72` already emit U+2014 via `_err(...)` and will survive the new lint unchanged
- **Proposed resolution**: Add `_err(` to the AST sink list (or treat it as an alias of `print` to stderr) alongside `print`, `_diag`, and `logging_util.*`; include a unit test for `_err("… — …")`



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_skill_closure_growth.py:50
- **Concern**: Prior accepted closure-growth fix is incomplete because the plan narrows the sweep to readability directive lines while changing the scanner to a colon-only mandatory directive.. Scenario: If implementer updates only readability lines, closure scanning stops seeing required non-readability load directives such as skills/implement/SKILL.md:135 and skills/research/SKILL.md:191, so the ratchet drops real prompt sources or rebaselines against an undercount.
- **Proposed resolution**: Make the firm sweep cover every MANDATORY READ ENTIRE FILE marker in closure-scanned sources, especially skills/design/SKILL.md, skills/implement/SKILL.md, skills/review/SKILL.md, skills/research/SKILL.md, and generated reviewer agent/template sources.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_readability_preamble.py:196-223
- **Concern**: Dev skill updates cannot remain optional because readability-preamble dynamically scans .claude/skills/*/SKILL.md outside the TSV manifest.. Scenario: If .claude/skills/*/SKILL.md stays under MAY_UPDATE and is skipped, the colon-only regex reports missing per-skill readability directives for existing dev skills such as .claude/skills/analyze-bugs/SKILL.md, blocking the required lint.
- **Proposed resolution**: Move the dev skill directive sweep from MAY_UPDATE to a firm UPDATED requirement or otherwise make the lint contract explicitly exclude those files.



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/logging_util.py:157-180
- **Concern**: The runtime sink list still omits BreadcrumbWriter.emit, so the accepted logging_util coverage fix remains incomplete.. Scenario: A planted U+2014 in logging_util.BreadcrumbWriter().emit(...) or a one-hop writer.emit(...) call is still visible operator output but would not be caught by the planned sink list.
- **Proposed resolution**: Add BreadcrumbWriter.emit call shapes used in the tree to lint-em-dash-output and cover them in test_lint_em_dash_output.py.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:219-547,skills/research/SKILL.md:207-336,skills/design/references/approval-gates.md:67-149
- **Concern**: Markdown em-dash-output lint scopes only line-start `⏩` and `Print:` lines, but the dominant status-print contract is inline ``print `⏩ … — …` `` templates (~19 hits across design/research skills and references).. Scenario: The colon-only MANDATORY sweep and the new lint can both pass while orchestrators keep emitting em-dash skip/bypass breadcrumbs from those backtick templates; the issue’s output-lint lock then misses the highest-traffic user-visible prose.
- **Proposed resolution**: Extend `lint_em_dash_output.py` to scan em-dash inside backtick status-print templates on lines matching `print `⏩` (and equivalent `Print:` bodies), or add an explicit scrub requirement for those literals in the firm-listed skill/reference files before enabling CI.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan:Approach step 5
- **Concern**: Prerequisite/acceptance gate text only names an explicit scrub pass for Python output calls, not markdown status-print literals.. Scenario: An implementer can treat step 5 as Python-only, enable `lint em-dash-output` after the Python prerequisite merges, and still ship em-dash breadcrumbs from inline ``print `⏩ … — …` `` templates because that gate never requires markdown scrub or scanner coverage.
- **Proposed resolution**: Reword step 5 to require scrubbing every in-scope emitted surface (Python sinks plus markdown status-print literals) or document that inline ``print `⏩` `` templates must be included in the scanner scope and scrub checklist.



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_readability_preamble.py:177-188
- **Concern**: Dev-only readability directive sweep is optional even though the lint scans it. Scenario: The plan changes the readability regex to exact colon form and runs lint, but leaves .claude/skills/*/SKILL.md under MAY_UPDATE. If skipped, existing dev skill lines such as .claude/skills/analyze-bugs/SKILL.md:10 keep the old U+2014 form, so dynamic skill scanning reports a missing per-skill directive and CI fails.
- **Proposed resolution**: Promote .claude/skills/*/SKILL.md to firm UPDATED, or add a firm sweep of every dynamic dev skill directive, including analyze-bugs.



### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_skill_closure_growth.py:50
- **Concern**: Accepted prior scanner fix is incomplete because the plan pairs colon-only closure matching with a readability-only directive sweep. Scenario: If non-readability prompt-load lines in gated SKILL.md files keep the old U+2014 form, parse_direct_markdown_references no longer sees those loaded references. A refreshed closure baseline can then drop real prompt files and weaken the ratchet.
- **Proposed resolution**: Make the firm sweep cover every scanner-relevant MANDATORY READ ENTIRE FILE load directive in the gated SKILL.md files and harness pins, then run lint skill-closure-growth before refreshing the baseline.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5c.py:554
- **Concern**: The planned em-dash output sinks omit `_core_diagnostic`, which writes operator-visible stderr.. Scenario: Approach step 4 lists `print`, `_diag`, `sys.stderr.write`, and `logging_util.diagnostic`, but not `_core_diagnostic`. `design_core._core_diagnostic` already emits `**⚠ Step 5c: missing .completed/step-5b — OOS filing incomplete...` at design_step5c.py:554. After prerequisite scrub of `print()` sites, enabling `lint em-dash-output` can still pass while stderr keeps U+2014, weakening the output lock.
- **Proposed resolution**: Add `_core_diagnostic` (and any other thin stderr wrappers in `python/larch/**`) to the AST sink list, or require scrubbing every existing `_core_diagnostic` literal in the same prerequisite pass that clears `print`/`logging_util.diagnostic` sites.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/**/*.py
- **Concern**: [SCOPE-REDUCTION] The co-land scrub branch still has no firm file list for existing runtime U+2014 output.. Scenario: Approach step 5 allows enabling `lint em-dash-output` after prerequisite merges OR an in-PR scrub, but `### UPDATED`/`### NEW` only cover directive-separator edits plus the lint itself. Dozens of `python/larch/**` `print`/`_diag`/`logging_util.diagnostic` literals still contain U+2014 (e.g. design_step5b.py, preflight.py, bootstrap.py, design_postplan.py). If scrub PRs are not merged first, implementers can wire CI and hit immediate red with no enumerated repair surface.
- **Proposed resolution**: Make prerequisite scrub a hard gate (drop the in-PR OR), or add an explicit `### UPDATED` batch for every in-scope runtime output file that still contains U+2014 before CI enablement, and keep acceptance on `python3 python/cli.py lint em-dash-output` passing on the merged tree.



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/agnix-fix/SKILL.md:10
- **Concern**: Dev-only readability directive sweep is listed as MAY_UPDATE even though lint scans it. Scenario: With the exact colon regex, skipping the optional .claude skill edits leaves old em-dash directives in dynamic skill coverage, including analyze-bugs, and python3 python/cli.py lint readability-preamble fails
- **Proposed resolution**: Promote .claude/skills/*/SKILL.md to firm UPDATED scope or otherwise require every dynamic dev skill directive to use the colon form



### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_skill_closure_growth.py:344-351
- **Concern**: Closure scanner colon switch leaves existing mandatory reference triggers outside the sweep. Scenario: The plan makes MANDATORY_DIRECTIVE_RE colon-only, but files such as skills/implement/references/checks-repair-loop.md:3 still contain MANDATORY — READ ENTIRE FILE and are not firm updates; refreshing the baseline would accept an undercounted prompt closure
- **Proposed resolution**: Add every closure-scanned MANDATORY READ ENTIRE FILE trigger file to the firm colon sweep, or defer the closure scanner exact-colon change until those trigger lines are migrated



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5b.py:168-268
- **Concern**: Firm file list omits python/larch runtime output scrub despite lint acceptance gate. Scenario: Approach step 5 allows prerequisite scrub issues or an in-PR scrub pass, but no ### UPDATED rows cover the ~35 python/larch modules whose print/_diag/emit strings still contain U+2014 (e.g. design_step5b.py, preflight.py, design_postplan.py, dispatch_commit_route.py). Enabling lint em-dash-output on merge fails CI immediately if prerequisite scrubs are not already on main.
- **Proposed resolution**: Add a firm deliverable: either ### UPDATED rows for every in-scope python/larch output site, or an explicit mechanical scrub step with a grep-driven file list and a hard gate that prerequisite scrub PRs are merged before CI wiring lands.



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:23
- **Concern**: em-dash-output ⏩ scope files missing from firm ### UPDATED list. Scenario: Plan step 4 lints ⏩-prefixed skill markdown lines, but six files still carry ⏩ breadcrumbs with U+2014 and are not listed: step2b5-rc-handling.md, skills/shared/progress-reporting.md, skills/implement/references/step18-cleanup.md, skills/design/references/decompose-panel.md, skills/research/references/critique-loop-phase.md, skills/research/references/citation-validation-phase.md. design_postplan.py mirrors the step2b5 strings and will also fail the Python side.
- **Proposed resolution**: Add ### UPDATED rows for all six markdown files; colon-replace every ⏩ status-print literal; keep python/larch mirrors in the runtime scrub deliverable above.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/implement/references/self-review.md:5
- **Concern**: Reference-file MANDATORY directive sweep is incomplete versus issue scope. Scenario: Issue Fix requires sweeping every SKILL.md and reference file that embeds the MANDATORY directive. Eight loaded references still use the em-dash separator and are absent from the firm list: self-review.md, bootstrap-recovery.md, checks-repair-loop.md, ship-pr-ci-fix.md, ship-pr-exit-matrix.md, rebase-checkpoint-routing.md, ship-pr-oos-checkpoint-router.md, skills/review/references/heavy-worker.md, plus skills/design/references/settle-rc-dispatch.md. Preamble lint may stay green, but loaded reference bodies still model the banned separator.
- **Proposed resolution**: Add ### UPDATED rows for each reference above; replace MANDATORY — READ ENTIRE FILE with the colon form everywhere it appears, including nested load directives inside ship-pr-exit-matrix.md and rebase-checkpoint-routing.md.



### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.tsv.md:36
- **Concern**: Dev skill directive edits are marked optional even though the lint requires them. Scenario: After the regex becomes colon-only, an implementer can skip the MAY_UPDATE .claude skill files; existing dev skill lines such as .claude/skills/analyze-bugs/SKILL.md:10 still use the old separator, so lint readability-preamble fails
- **Proposed resolution**: Move .claude/skills/*/SKILL.md to firm UPDATED scope or list the concrete dev skill files, including analyze-bugs



### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/plan_quality.py:30
- **Concern**: Logging output sink coverage still misses existing helper call forms. Scenario: The plan lists logging_util.emit style calls, but current code imports emit, emit_kv, and diagnostic directly, and other files use BreadcrumbWriter().emit; a planted U+2014 in those emitted strings can pass the new lint
- **Proposed resolution**: Resolve logging_util sinks through imports from larch.core.logging_util and include BreadcrumbWriter.emit, with one focused regression fixture



### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/SKILL.md:207
- **Concern**: Markdown output scanner misses inline print literals. Scenario: The plan scans Print: and lines that start with the status prefix, but current skills also emit status strings as lowercase print with a backticked status literal; a planted U+2014 there is emitted output but can pass
- **Proposed resolution**: Add scanner coverage for inline print or Print backticked status literals, at least for literals beginning with the existing status glyphs, and add a focused fixture



