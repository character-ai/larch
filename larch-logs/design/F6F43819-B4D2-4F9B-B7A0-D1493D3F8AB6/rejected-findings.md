### [Plan Review] FINDING_1

### FINDING_1: Report labels conditional closure as reported-only after ratchet change
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan extends baseline keys and `_growth_violations()` to ratchet `conditional_*` metrics for skill targets (`design`, `implement`, `review`), but `_print_report()` (around `python/larch/lint/lint_skill_closure_growth.py:592-602`) still prints `Conditional closure (reported only)`. Operators and CI can read a non-ratcheted report label while `lint skill-closure-growth` fails on conditional growth, or misread review conditional metrics as informational only. The mismatch also affects `test_report_mode_prints_design_and_implement` expectations if they still assert the old header.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update _print_report to label conditional closure as ratcheted for skill targets (panel-tier may stay zero), and update the report-mode test expectations accordingly.
  - From Cursor-Pragmatic: Rename the conditional section header to reflect ratcheted skill targets (for example `Conditional closure (ratcheted for skill targets)`), keep panel-tier zeros explicit, and mirror the wording in `docs/linting.md`.


### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_skill_closure_growth.py:251-266
- **Concern**: [SCOPE-REDUCTION] Classifier bullets add generic use/follow/procedure matchers while Approach limits changes to verified hidden-eager patterns. Scenario: Issue scope names only final-summary-emit, step-name-registry, external-reviewers, session-setup-output, and the preflight default-path fix. Generic follow harvesting also matches always-on prose such as design Follow shared/subskill-invocation.md and Follow shared/progress-reporting.md rules, plus many route-qualified follow lines. That inflates design/implement baselines beyond the four verified gaps even with conditional gates.
- **Proposed resolution**: Replace generic phrase matchers with narrow harvesters tied to the verified patterns (session-start Read of skills/*/scripts/step-name-registry.tsv, review Step 0 use ... session-setup-output.md / external-reviewers.md, implement green-path follow final-summary-emit.md, force_requested=false preflight read). Keep the shared path extractor and conditional gate, but do not add blanket follow <path>.md harvesting.


### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_skill_closure_growth.py:541-551
- **Concern**: [SCOPE-REDUCTION] Plan ratchets conditional metrics for design and implement, not only review. Scenario: Issue acceptance requires review eager plus conditional ratchet and panel-tier closure ratchet. Design and implement conditional closure is report-only today. Requiring _growth_violations to compare conditional_* for every skill row freezes existing conditional corpora (for example design validator-failure.md) and expands enforcement beyond the issue.
- **Proposed resolution**: Limit conditional growth checks to the review row (or compare conditional_* only when baseline conditional_lines > 0). Keep conditional fields on design/implement rows for reporting if desired, but do not fail lint on their conditional growth unless the issue explicitly expands scope.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: docs/linting.md:60-64
- **Concern**: [SCOPE-REDUCTION] Required doc edits omit the lint failure-criteria paragraph. The plan rewrites scope bullets and `--skill` examples but does not require updating the paragraph that still says growth lint fails only on eager `skill_md_*` and `closure_*` fields. After conditional metrics enter the baseline ratchet, operators reading unchanged prose will think conditional growth is still report-only.. Scenario: Add an explicit Required doc change: state that `lint skill-closure-growth` also fails when `conditional_lines`, `conditional_estimated_tokens`, or `conditional_content_estimated_tokens` grow for `design`, `implement`, and `review`; keep `panel-tier` conditional metrics at zero.
- **Proposed resolution**:


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_skill_closure_growth.py:541-551
- **Concern**: [SCOPE-REDUCTION] Conditional ratchet is extended to every skill target, not just `/review`. Issue scope adds review eager plus conditional ratchet and panel-tier closure; design and implement conditional closure is report-only today (`Conditional closure (reported only)`). Applying `_growth_violations()` conditional compares to `design` and `implement` changes lint behavior beyond the issue and will force baseline churn for existing conditional files such as `decompose-panel.md` without a stated requirement.. Scenario: Limit conditional baseline compare and growth failures to the `review` row (uniform schema keys are fine); keep design and implement conditional metrics report-only in `lint skill-closure-growth`, matching current behavior.
- **Proposed resolution**:


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_skill_closure_growth.py
- **Concern**: [SCOPE-REDUCTION] Generic `use` / `follow` / `procedure in` matchers exceed the issue and the plan Approach line that limits extension to verified hidden-eager patterns. Scenario: The plan Approach says to extend directive matching only for verified hidden-eager patterns, but the classifier section adds repo-wide `use <path>.md`, `follow <path>.md`, and `procedure in <path>.md` harvesters. That is broader than the named gaps (review `session-setup-output.md` / `external-reviewers.md`, implement `final-summary-emit.md` / `step-name-registry.tsv` / default-path `preflight-plan-audit.md`) and will pull in many branch-only citations, inflating design/implement/review baselines beyond the minimum-change contract.
- **Proposed resolution**: Replace generic matchers with narrow patterns tied to the verified shapes already in production skills (`use …session-setup-output.md for`, `procedure in …external-reviewers.md`, session-start `Read …step-name-registry.tsv`, green-path `follow …final-summary-emit.md`, plus the `force_requested=false` eager override). Keep `_line_is_conditional` on any new harvester.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:378
- **Concern**: [SCOPE-REDUCTION] `follow agents/_implementer-base.md` is manifest-conditional but will classify eager under the planned `follow <path>.md` matcher. Scenario: Line 378 (`For non-empty manifests, follow agents/_implementer-base.md`) does not hit current conditional-prefix rules (`for \`` / `when \``). A generic follow harvester adds `agents/_implementer-base.md` to implement eager closure even though it is already counted under panel-tier via `agents/*.md`, forcing implement baseline churn the issue did not request.
- **Proposed resolution**: Exclude `agents/*.md` from skill-target harvesting (panel-tier owns them) or require an explicit manifest predicate before eager classification; add a real-scan negative assert that `agents/_implementer-base.md` is absent from implement `files` and `conditional_files`.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_skill_closure_growth.py:541-551
- **Concern**: [SCOPE-REDUCTION] Baseline conditional ratchet is generalized to design/implement, beyond issue acceptance. Scenario: Issue acceptance requires growth failure for review and panel-tier only. The plan compares `conditional_*` for every skill ratchet row, so growth in existing design/implement conditional-only references (already tracked in live scans/tests) becomes a new lint failure surface the issue did not ask to tighten.
- **Proposed resolution**: Limit conditional `_growth_violations()` enforcement to the `review` row (store conditional fields on all rows if needed for schema uniformity), or document this expanded ratchet as an explicit in-scope requirement before implementation.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_skill_closure_growth.py:17-25; python/tests/lint/test_lint_skill_closure_growth.py:633-648
- **Concern**: [SCOPE-REDUCTION] Planned conditional-metric ratcheting applies to every gated skill, not just the new /review row. Scenario: The issue needs /review eager plus conditional coverage and panel-tier growth. Adding conditional fields to global METRIC_FIELDS and the byte-exact baseline freshness gate makes existing /design and /implement conditional-only sources fail CI on future growth, expanding a previously report-only contract beyond this feature.
- **Proposed resolution**: Add target-specific conditional ratcheting. Compare and freshness-gate conditional_* metrics only for review. Leave design and implement conditional closure reported-only unless a separate issue changes that contract.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_skill_closure_growth.py:541-551
- **Concern**: [SCOPE-REDUCTION] Plan ratchets conditional metrics for design and implement, not only review. Scenario: The issue asks for a review row with eager plus conditional ratchet and names no change to design/implement conditional policy. Today conditional metrics are reported only (`_print_report` labels them "reported only"; `_growth_violations` checks eager `METRIC_FIELDS` only). The plan requires `_growth_violations()` to compare conditional metrics for every skill target row, so growth in existing design conditional files such as `skills/design/references/decompose-panel.md` would start failing lint without any issue-scoped need.
- **Proposed resolution**: Limit conditional `_growth_violations` comparisons to the new `review` row only (keep design/implement conditional report-only), or narrow the plan and docs to state an explicit repo-wide policy change and add the matching operator/docs text.


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_skill_closure_growth.py:251-266
- **Concern**: [SCOPE-REDUCTION] Generic `use` / `follow` / `procedure in` matchers exceed the issue's named hidden-eager scope. Scenario: The Approach says to extend directive matching only for verified hidden-eager patterns, but the implementation section adds broad phrase matchers. Live skills contain many capitalized `Follow ... .md` lines unrelated to the named gaps (for example design line 25 `subskill-invocation.md`, design line 622 `finalize-step5.md`, implement line 113 `verbosity-control.md`). Even with `_line_is_conditional` and sentence-bounded clauses, a generic harvester risks inflating design/implement/review baselines beyond the four verified fixes and forcing churn the issue did not request.
- **Proposed resolution**: Replace generic matchers with the minimum patterns needed for the named sources (`use ... session-setup-output.md for`, registry `Read ... step-name-registry.tsv`, `procedure in ... external-reviewers.md`, default-path `preflight-plan-audit.md`, and green-path `final-summary-emit.md`), or keep generic matching but add required real-scan negative assertions for high-risk always-on prose citations the issue did not ask to ratchet.


