### OOS_1: [OUT_OF_SCOPE] BoundaryResult.source mislabeled on repo_unresolved
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On `repo_unresolved`, `BoundaryResult.source` is set to `gh-issue-closedAt` even though `gh issue view` never runs. The unavailable report’s “Boundary source attempted” contradicts `Reason: repo_unresolved` and can mislead operators into debugging `gh` when repo resolution failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use plugin-root-remote source when repo resolution fails

### OOS_2: [OUT_OF_SCOPE] Discovered vs era-scanned file counts can diverge unexplained
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Era bucketing drops TSVs from runs with missing/invalid `started_at`, but the header still reports all globbed files as discovered while per-era slices report only bucketed `files_seen`. Excluded runs make discovered exceed pre+post scanned counts with no reconciling line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add excluded classification file count or reconcile discovered vs bucketed

### OOS_3: [OUT_OF_SCOPE] missing-closedAt gh stub lacks argv contract guards
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The shipped-but-missing-`closedAt` fake-`gh` stub accepts any argv, unlike the success stub that enforces scoped `--repo` and `--json` fields. A regression dropping those guards would not fail this test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Apply same argv guards as fake-gh success stub

### OOS_4: [OUT_OF_SCOPE] Era exit `2` cases missing from consolidated exit-code docs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The consolidated “Output and exit codes” section lists only log-root-missing as exit `2`, while era-specific exit `2` cases (`--era-since-date` without `--era`, malformed date) appear only in the era section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add era exit `2` cases to the exit-codes bullet list for one-stop operator reference.

### OOS_5: [OUT_OF_SCOPE] `_run_gh_json` has no subprocess timeout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A wedged `gh` (auth prompt, network hang) can block `--era all` indefinitely. This mirrors `analyze_issues.py` gh helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional bounded timeout with degradation to boundary-unavailable would align with other soft-fail paths.

### OOS_6: [OUT_OF_SCOPE] Harness omits auto-boundary test for unshipped incentive issue
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-era-boundary-output.txt, dyn-dyn-era-harness-output.txt
- **Severity**: important
- **Concern**: The harness does not stub `gh issue view` returning a non-shipped incentive issue (open, closed without PR refs, `NOT_PLANNED`, etc.). The `calibration_incentive_not_shipped` degradation path at `voter-calibration.py:201-202` is implemented but not regression-locked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a stub `gh issue view` returning `OPEN` or closed-without-PR-refs and assert `Reason: \`calibration_incentive_not_shipped\`` plus exit `0`.
  - From dyn-dyn-era-boundary-output.txt: The harness covers missing `gh`, missing `git`, repo-unresolved, shipped-without-`closedAt`, and fake-`gh` success, but not a stub where `gh issue view` succeeds yet `_ground_truth_calibration_incentive_shipped` returns `calibration_incentive_not_shipped` (closed without PR refs, `NOT_PLANNED`, etc.). That path is implemented via `unavailable_reason=reason` at `voter-calibration.py:201-202` but is not regression-locked.
  - From dyn-dyn-era-harness-output.txt: There is no fake-`gh` case where the incentive issue is present but **not shipped** (open state or closed without PR refs). Auto-boundary degradation for that path is therefore unverified by the harness, though it is specified in the plan edge cases.

### OOS_7: [OUT_OF_SCOPE] `plugin_root` bound at import time
- **Reviewer(s)**: dyn-dyn-era-boundary-output.txt
- **Severity**: important
- **Concern**: `plugin_root` is bound at import time from `CLAUDE_PLUGIN_ROOT` / `__file__`. A long-lived embedded caller cannot retarget plugin root without a fresh process. Not introduced by era mode specifically.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] `CLAUDE_PLUGIN_ROOT` whitespace-only treated as authoritative
- **Reviewer(s)**: dyn-dyn-era-boundary-output.txt
- **Severity**: important
- **Concern**: Docs say `CLAUDE_PLUGIN_ROOT` is used when “set and non-empty,” but code treats any truthy env value (including whitespace-only) as authoritative, which can break auto-boundary repo resolution without falling back to `parents[3]`. Pre-existing bootstrap quirk, now more visible because era auto-boundary depends on `plugin_root` for `git -C`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Era bucketing couples to private `analyze_issues` helpers
- **Reviewer(s)**: dyn-dyn-era-bucketing-output.txt
- **Severity**: important
- **Concern**: Era bucketing imports private `analyze_issues._ground_truth_*` helpers. That matches the approved plan, but couples the skill script to underscore-prefixed internals; a small public facade in `python/` would reduce future rename risk.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] Zero-file era slice renders placeholder metrics
- **Reviewer(s)**: dyn-dyn-era-bucketing-output.txt
- **Severity**: important
- **Concern**: An era slice with zero scanned files still renders placeholder agreement/severity rows (`| n/a | n/a | 0 | ...`), which can read like measured zero calibration rather than “no corpus.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-era-bucketing-output.txt: The slice metadata line helps, but a one-line “no qualifying panels in this era” banner would reduce misread risk when one side of `--era all` is empty.

