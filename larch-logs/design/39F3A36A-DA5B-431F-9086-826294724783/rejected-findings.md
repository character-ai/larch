### [Plan Review] FINDING_4

### FINDING_4: Committed verdict artifact referenced but never scheduled for creation
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan references recording human judgment in `docs/ground-truth-verdict.md` as the capstone acceptance artifact, but that file is absent and not listed under Files to modify/create. The code path can gate and print a verdict without landing the promised committed report, leaving the capstone artifact missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add docs/ground-truth-verdict.md to Files to modify/create, or name another concrete committed artifact path and include it.
  - From Codex-Innovation: Add `docs/ground-truth-verdict.md` to Files to modify/create and define the committed verdict entry to write.
  - From Codex-Requirements: Add `### NEW: docs/ground-truth-verdict.md` to Files to modify/create and seed it with the first verdict report or summary.


### [Plan Review] FINDING_5

### FINDING_5: GroundTruthStats new fields lack constructor defaults
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: `GroundTruthStats` adds set, bool, int, and optional fields without constructor defaults. `ground_truth_voter_calibration()` still calls `GroundTruthStats()` with no arguments, so the dataclass cannot be instantiated and verdict scanning fails immediately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Give every new stats field a default and use field(default_factory=set) for qualifying_run_dirs.


### [Plan Review] FINDING_6

### FINDING_6: GroundTruthEvidence.run_dir_key not wired through all constructors
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: The plan only mentions populating `run_dir_key` for accepted finding evidence, but `_ground_truth_issue_evidence()` and other constructors still build issue-backed evidence without it. Verdict runs will hit a missing-argument path or carry incomplete evidence metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Either default run_dir_key to "" or update _ground_truth_issue_evidence() and every other GroundTruthEvidence constructor to pass it.


### [Plan Review] FINDING_8

### FINDING_8: Diagnostic row-cache key includes verdict-only tuple members when verdict_mode unset
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan keys `_GROUND_TRUTH_ROW_CACHE` with `(log_root, since_date, min_larch_version, verdict_mode, min_runs)` even when `--ground-truth-verdict` is unset. If coordinators forward argv into the key when `verdict_mode=False`, one process can cache the same unfiltered scan under multiple keys and reuse a verdict-filtered entry whose `stats.min_runs` / gate fields do not match a later diagnostic call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Build cache keys from normalized stats only: diagnostic mode uses a fixed `(log_root, False)` (or equivalent sentinels); include `since_date`, `min_larch_version`, and `min_runs` only when `verdict_mode` is true.


### [Plan Review] FINDING_9

### FINDING_9: Verdict-mode offline entry path lacks regression coverage for empty-issue bypass and stderr gate error
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: `main()` / `analyze_main()` can still short-circuit on empty issues or fail to surface `ERROR=` when verdict mode is on, leaving the new branch unverifiable without dedicated regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a verdict-mode test that uses an empty JSON dump plus populated log-root evidence, asserts the verdict report renders, exit is non-zero on gate failure, and stderr carries `ERROR=`.
```

**Merge notes**

| Source IDs subsumed | Merged into |
|---|---|
| FINDING_1, 9, 15, 18 (+ embedded Requirements narrative #1) | FINDING_1 |
| FINDING_2, 8, 16, 19 (+ embedded Requirements narrative #2) | FINDING_2 |
| FINDING_4, 12, 20 | FINDING_4 |
| FINDING_7, 13, 14 | FINDING_7 |

FINDING_2 and FINDING_7 are related (#5461 incentive gate) but kept separate: one is missing bulk-issue lookup, the other is the wrong JSON field name. No `[OUT_OF_SCOPE]` tags in the input. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token (non-empty merge).


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: README.md:291-298
- **Concern**: [SCOPE-REDUCTION] Firm README.md and docs/skills.md updates are outside binding issue surfaces. Scenario: Binding scope lists only `python/analyze_issues.py`, `.claude/skills/analyze-issues/SKILL.md`, and `docs/point-competition.md`. Duplicate verdict-flag synopsis in README and docs/skills.md adds maintenance without changing verdict correctness or the committed artifact path (prior FINDING_14 rejection still applies).
- **Proposed resolution**: Drop `### UPDATED: README.md` and `### UPDATED: docs/skills.md` from the firm plan; keep operator-facing verdict docs in the skill and `docs/point-competition.md` only.


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:197-199
- **Concern**: [SCOPE-REDUCTION] Keep the severity slice verdict-only; adding it to normal diagnostic reports is extra surface area the capstone feature does not need.. Scenario: Normal /analyze-issues output changes even when --ground-truth-verdict is off, so the plan adds churn and new test burden without restoring a broken path.
- **Proposed resolution**: Gate the severity slice behind verdict mode, and leave the existing diagnostic report unchanged.


