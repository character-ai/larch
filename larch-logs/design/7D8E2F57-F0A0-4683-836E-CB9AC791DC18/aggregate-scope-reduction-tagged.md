### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/**/*.py
- **Concern**: [SCOPE-REDUCTION] The co-land scrub branch still has no firm file list for existing runtime U+2014 output.. Scenario: Approach step 5 allows enabling `lint em-dash-output` after prerequisite merges OR an in-PR scrub, but `### UPDATED`/`### NEW` only cover directive-separator edits plus the lint itself. Dozens of `python/larch/**` `print`/`_diag`/`logging_util.diagnostic` literals still contain U+2014 (e.g. design_step5b.py, preflight.py, bootstrap.py, design_postplan.py). If scrub PRs are not merged first, implementers can wire CI and hit immediate red with no enumerated repair surface.
- **Proposed resolution**: Make prerequisite scrub a hard gate (drop the in-PR OR), or add an explicit `### UPDATED` batch for every in-scope runtime output file that still contains U+2014 before CI enablement, and keep acceptance on `python3 python/cli.py lint em-dash-output` passing on the merged tree.
