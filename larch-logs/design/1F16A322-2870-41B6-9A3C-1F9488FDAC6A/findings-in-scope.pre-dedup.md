### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_complexity_baseline.py:327-330
- **Concern**: Apply strip/nonblank validation to --write --reason and stored reason fields the same way as operator_override. Scenario: Plan requires stripped nonblank override reasons but only says Reject blank reasons for --write; sibling baseline lints use not reason.strip() and current _validate_reason uses not reason so whitespace-only values pass load and can be persisted on growth
- **Proposed resolution**: Strip and reject whitespace-only --reason before write; update _validate_reason to use not value.strip() and add matching tests alongside the accepted override whitespace cases ### 1. [correctness] `python/larch/lint/lint_complexity_baseline.py:327-330` — Strip/nonblank validation for `--reason` and stored `reason` **Concern:** The plan correctly requires stripped nonblank `operator_override` reasons (addressing accepted FINDING_13 / **I-Gate-1** audit integrity), but it only says `--write` should “reject blank reasons” and does not extend the same rule to the optional stored `reason` field. Current code and sibling baseline lints diverge: `lint_subprocess_via_runner.py` rejects `not reason.strip()`, while `_validate_reason` and `_validate_operator_override` today use `not reason`, so `" "` is treated as non-empty. **Scenario:** An operator runs `make regen-complexity-baseline REASON=' '` (or manually commits a whitespace `reason`). The writer accepts it, the row loads cleanly, and the issue acceptance criterion (“non-empty reason for any new entry or metric increase”) is satisfied only cosmetically. This does not disarm the repeat-bump gate (unlike override whitespace), but it weakens the audit trail the feature adds. **Suggested revision:** In the `lint_complexity_baseline.py` section, require `--write --reason` to strip and reject whitespace-only values before merge, and require `_validate_reason` to use the same stripped-nonblank check on load. Add parallel tests next to the planned override whitespace cases. This matches **G-Py-4** and existing baseline-lint conventions without expanding scope.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_complexity_baseline.py
- **Concern**: Metric-decrease merge leaves non-increasing history. Scenario: The writer allows decreases without a new reason but does not define history updates. After a shrink regen, history can still end with a higher metric than the stored row (for example 55 then 60 while metric becomes 45). The plan also rejects non-increasing history and derives repeat bumps from history alone, so the next reasoned increase either fails validation on write or keeps stale bump windows that can false-fail urgent regens.
- **Proposed resolution**: Specify shrink behavior in the writer merge: on metric decrease, rewrite history to a single UTC seed at the new metric (or truncate trailing entries above the new metric) without requiring --reason. Add a test that shrink-only regen stays load-valid and that a later first increase is not treated as a second bump inside 14 days of pre-shrink history.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_complexity_baseline.py
- **Concern**: Repeat-bump failures should name file plus symbol. Scenario: Plan failure text calls for the symbol and code-tagged history only. Grouping is by (file, qualified_symbol), but the same qualified_symbol can appear in multiple files, so stderr that omits file can send operators to the wrong function.
- **Proposed resolution**: Include normalized file path in each repeat-bump failure line (for example file:qualified_symbol) while keeping code-tagged history and the three remediation exits. ## Findings ### 1. **correctness** — `python/larch/lint/lint_complexity_baseline.py` The writer merge allows metric decreases without `--reason`, but it does not say what happens to `history`. That conflicts with the plan’s non-increasing history rule and with gate logic that reads bumps from committed history only. After a simplification regen, you can end up with `metric: 45` and `history: [{55}, {60}]`. The next growth append can fail validation, or stale dates can trigger a false repeat-bump failure. That blocks the “urgent fix always ships” goal. **Suggested fix:** On decrease, reset history to one UTC seed at the new metric (or truncate entries above it). Add a shrink-only test that proves load validation passes and pre-shrink bumps do not count. ### 2. **correctness** — `python/larch/lint/lint_complexity_baseline.py` Failure output is specified as symbol plus code-tagged history. Grouping uses `(file, qualified_symbol)`, but the message does not include `file`, so duplicate qualified symbols across files are ambiguous. **Suggested fix:** Print `file:qualified_symbol` in repeat-bump failures, with history and the three remediation paths unchanged. --- **Note:** Most round-1 accepted items (override preservation, `REASON=` wiring, check-mode history gate, cross-code grouping, history seeding, override whitespace, debt duplicate rejection, integration coverage) are now explicit in the plan. Re-raising them would be redundant. Rejected items (atomic writes, shared date helper, full identity in failures per round-1 vote) were skipped unless new evidence applied; finding 2 aligns with rejected FINDING_9 only insofar as the plan still omits `file` in failure text.



### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_complexity_baseline.py
- **Concern**: Define history ordering to support same-day and post-decrease metric increases. Scenario: The writer permits a decrease, then must append history on a later increase; that valid rebound can be lower than an earlier history metric. Also two increases can share one UTC date. The proposed rejection of non-increasing history and later-event override rule can reject writer-produced data or leave same-date cross-code overrides indeterminate.
- **Proposed resolution**: Validate chronological append order without requiring metrics or dates to be strictly increasing, treat post-seed records as bumps, and define deterministic same-date cross-code event and override handling; cover both cases in tests.



