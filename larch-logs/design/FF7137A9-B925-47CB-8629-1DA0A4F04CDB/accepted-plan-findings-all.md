### FINDING_3: CI/probe basename and kind exclusion list is incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Multiple gaps in the planned CI-only filter let non-reviewer rows survive and keep `chart_end` at a late timestamp, preserving the discontinuous Gantt with a large empty mid-chart span. (1) The CI basename allowlist omits `ci-fix-{tier}.out` paths used by CI monitor (`python/ci_monitor.py` writes outputs like `ci-fix-codex.out`); a malformed or legacy row with `vendor-misc` and only a `ci-fix-*.out` basename could pass the planned kind list. (2) The filter omits generic probe basenames such as `unknown/claude.out` shown in the bug sample alongside `cursor/ci.out`; filtering only `*-ci.out` basenames and CI task kinds leaves `claude.out` (and symmetric `codex.out`/`cursor.out` when not slot-mapped). Because `chart_end` is max(displayed task end), one surviving 1s tail row keeps the axis at the full round span.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend basename matching to `ci-fix-*.out` (basename prefix after `base()`), or use a suffix rule on task kind such as `-$` match for `-ci` and `-ci-fix`
  - From Cursor-Pragmatic: Extend the chart-row predicate to drop claude.out (and symmetric codex.out/cursor.out when not slot-mapped), or treat any task kind matching *-ci / *-ci-fix / *-ci-test as CI regardless of basename. Add harness rows for claude.out at the round tail and assert absence plus a title span that ends near the last reviewer bar.
  - From Cursor-Requirements: Add claude.out (and matching codex.out/cursor.out launcher basenames if present) to the same basename exclusion predicate as ci.out, and extend scripts/test-render-review-phase-detail.sh assertions to reject unknown/claude.out in the main Gantt fixture.




### FINDING_1: Implement final-report harness pins stale 65s chart title span
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: If `render-review-phase-detail.sh` derives the Gantt title window from filtered reviewer tasks instead of the full round window, the fixture in `test-write-final-report.sh` (65s round row, lone 50s vendor row at lines 1128–1131) will render `window 0:00-0:50 (50s)` while line 1146 still asserts `window 0:00-1:05 (65s)`. `make test-harnesses-6` (`test-write-final-report`) fails even when `scripts/relevant-checks.sh` passes. `render-review-phase-detail.md` edit-in-sync already lists this harness; the plan does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: skills/implement/scripts/test-write-final-report.sh to Files to modify/create; change the pinned title to the filtered-task span (50s). render-review-phase-detail.md edit-in-sync already lists this harness.


### FINDING_2: Design final-summary harness pins stale 65s chart title span
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Same chart-window regression in the design path. The post-publish fixture in `test-render-final-summary.sh` (lines 935–938: 65s round / 50s vendor pattern) and `grep -Fq 'window 0:00-1:05 (65s)'` on line 961 will fail after the shell renderer change. `render-review-phase-detail.md` edit-in-sync lists `render-final-summary.sh` but not `test-render-final-summary.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: skills/design/scripts/test-render-final-summary.sh; update the expected title span to match the filtered reviewer row (50s). Include both harnesses in Testing strategy alongside scripts/test-render-review-phase-detail.sh.

---

**Evidence check (read-only):** Both harnesses currently assert the 65s round span while also checking for bare `50s` duration text. Today `render-review-phase-detail.sh` still sets title span from `gw_end - gw_start` (round window, lines 443–445). The findings are **plan-forward**: they apply if the planned change moves title span to filtered-task bounds. The fixture pattern and assertion lines cited by the reviewer match the repo.



