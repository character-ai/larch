### FINDING_1: Final-report consumer must adapt to typed PR line-count results
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Typed Contract Compatibility, Codex-dyn-Typed Contract Compatibility
- **Severity**: major
- **Concern**: `compute_pr_line_counts()` will return `PrLineCountResult`, but `final_report.py` remains optional and uses mapping-style access, causing uncached final-report generation to fail at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change ### MAY_UPDATE: python/larch/report/final_report.py to ### UPDATED. Replace dict .get / mapping access with PrLineCountResult fields (and adjust _merge_line_count_state call accordingly). Add a bounded test in python/tests/report/test_final_report.py for ok/skipped/unavailable field mapping, and list that file in Testing strategy.
  - From Codex-Arch: Promote `python/larch/report/final_report.py` to UPDATED and require adapting both `_derive_pr_line_counts()` and `_merge_line_count_state()` to named result fields while preserving the existing KV output
  - From Codex-Innovation: Promote `python/larch/report/final_report.py` to UPDATED and replace mapping access and `_merge_line_count_state` input with named result fields while preserving ship-file KV output
  - From Cursor-Pragmatic: List ### UPDATED: python/larch/report/final_report.py and switch _derive_pr_line_counts/_merge_line_count_state to PrLineCountResult fields (or a small typed-to-KV helper) while preserving cached ship-pr-state keys and empty fallbacks
  - From Codex-Pragmatic: Promote final_report.py to UPDATED and replace mapping access with PrLineCountResult fields
  - From Cursor-Requirements: Promote python/larch/report/final_report.py to ### UPDATED: with explicit PrLineCountResult field access, or add a hard requirement that this MAY_UPDATE is mandatory whenever compute_pr_line_counts() changes return type
  - From Codex-Requirements: Move final_report.py to UPDATED and update _derive_pr_line_counts() to use named result fields; add its direct regression coverage to the plan
  - From Cursor-dyn-Typed Contract Compatibility: Promote python/larch/report/final_report.py to ### UPDATED: and require field access plus a Mapping adapter (or explicit KV dict build) for _merge_line_count_state, preserving cached ship-pr-state keys and empty fallback behavior.
  - From Codex-dyn-Typed Contract Compatibility: Mark final_report.py UPDATED and convert _derive_pr_line_counts() and _merge_line_count_state() to named PrLineCountResult fields while preserving cached KV output.


### FINDING_2: Add CLI wrapper contract regression tests
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Typed Contract Compatibility
- **Severity**: major
- **Concern**: Library tests do not pin the four token `*_main` wrappers’ byte-stable stdout, stderr, key ordering, and exit-code behavior after conversion to dataclass results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add explicit test_tokens.py cases that call each *_main, assert full stdout and stderr, and assert exit codes for ok, skipped-ledger, unavailable, and invalid-input paths; mirror the timing wrapper coverage already planned in test_timing.py.
  - From Cursor-Requirements: Add wrapper-level stdout, stderr, and exit-code regression tests for those four token *_main entry points, mirroring existing timing_mark_main and timing_report_main coverage in test_timing.py
  - From Cursor-dyn-Typed Contract Compatibility: Add capsys/exit-code tests for token_mark_main, token_check_budget_main, token_claude_source_main, and compute_pr_line_counts_main (mirror python/tests/report/test_timing.py timing_*_main coverage), including skipped-ledger, cap_hit/under_cap, unavailable claude-source, and each LINES_STATUS branch.


### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:454-463
- **Concern**: [SCOPE-REDUCTION] Promote final_report.py from MAY_UPDATE to firm UPDATED. Scenario: compute_pr_line_counts() is being converted from dict to PrLineCountResult; _derive_pr_line_counts still calls result.get() and passes result into _merge_line_count_state(lines: Mapping). Skipping the optional file leaves AttributeError or broken ship KV line-count derivation on /implement final report.
- **Proposed resolution**: Make ### UPDATED: python/larch/report/final_report.py firm. Replace dict access with PrLineCountResult fields and build the ship-file mapping from those fields only.


