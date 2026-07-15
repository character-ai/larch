### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: [SCOPE-REDUCTION] Production exclusion filter is unspecified for git discovery. Scenario: Pathspecs python/larch/**/*.py still match tracked test_*.py, conftest.py, and support filenames under python/larch. Legacy iter_source_files drops them via is_exempt_path; engine discovery uses git ls-files plus optional source_filter. The plan says to preserve exclusions but does not wire a LintRule source_filter (markdown uses is_production_source_path). A tracked exempt file would be scanned and could change live identities and baseline results.
- **Proposed resolution**: Reuse the existing is_exempt_path logic as a repo-relative source_filter on LintRule, mirroring lint_markdown_heading_fence_state.py. Extend the engine-backed CLI test to git-track an exempt filename and assert it is skipped while eligible python/larch files are scanned.
