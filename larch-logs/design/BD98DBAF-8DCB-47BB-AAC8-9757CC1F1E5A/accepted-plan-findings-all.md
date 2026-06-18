### FINDING_1: Check 15 pins absent `FINDING_N` / `OOS_N` literals in `validation-phase.md`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Arch, Codex-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan adds Check 15 `contains()` assertions for `FINDING_N` and `OOS_N` in `skills/research/references/validation-phase.md`, but those literals are absent from that file (and from the research tree). Item 1 scope calls for synthesis / `NOT_SUBSTANTIVE` pins, not plan-voter ballot grammar. Implementing Check 15 as written makes `scripts/test-research-structure.sh` fail on every run under `make lint`, so Item 1 cannot land.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic: Drop Check 15 or retarget pins to strings that actually exist in the chosen research reference (issue Item 1 asked for synthesis/NOT_SUBSTANTIVE pins, not plan-voter ballot grammar)
  - From Codex-Arch, Codex-Pragmatic: Retarget Check 15 to existing contract text or add the missing research contract text to Files to modify/create before asserting it
  - From Codex-Innovation: Either add the validation-phase contract text that contains the exact required marker, or change Check 15 to pin an existing required literal. If the intended source item is FINDING_3, assert FINDING_3, not FINDING_N.
  - From Cursor-Requirements: Drop Check 15 or retarget pins to a file that actually carries the ballot protocol (if any); do not assert FINDING_N/OOS_N in validation-phase.md


### FINDING_2: `parse-rate-check` uses invalid `--id-grammar FINDING`
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The planned `tally-code-votes.sh` swap calls `python/cli.py voting parse-rate-check` with `--id-grammar "FINDING"`, but `python/voting.py` only accepts `finding-only` or `finding-oos`. Under `set -e`, each live voter eligibility check exits argparse code 2 instead of emitting `PARSE_RATE_STATUS`, so tally either aborts or excludes voters incorrectly and Item 4 consolidation breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Pass --id-grammar finding-oos for code-review ballots and keep parsing PARSE_RATE_STATUS from stdout
  - From Codex-Innovation, Codex-Pragmatic: Use --id-grammar finding-oos.
  - From Cursor-Requirements: Use --id-grammar finding-oos to match agent_voters.py dispatch for code-review ballots that include OOS rows
  - From Codex-Requirements: Use `--id-grammar finding-oos`;


### FINDING_3: Planned `NOT_SUBSTANTIVE` regression test does not pin the count path
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: The planned `python/test_plan_review.py` assertion only checks body-wide `COLLECT_FAILURE_COUNT` presence (and similar surface strings). `_write_round_summary` could stop emitting the count, or `_count_collector_evidence` could stop incrementing on `NOT_SUBSTANTIVE`, while the new test still passes. Item 2's round-summary.env regression remains unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Slice the _write_round_summary function body and assert the exact COLLECT_FAILURE_COUNT printf appears in that region
  - From Codex-Innovation: In the new test, isolate _count_collector_evidence from the embedded loop and assert the non-OK case increments collect_failure_count. Then separately assert write_round_summary emits COLLECT_FAILURE_COUNT.


### FINDING_5: `docs/linting.md` `test-classify-bump` shard attribution drifts from `Makefile`
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The planned `docs/linting.md` row keeps `test-harnesses-20` attribution for `test-classify-bump`, but `Makefile` still places that target in `test-harnesses-19`. The lint-table contract stays drifted after the PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Change the row to test-harnesses-19, or move the target to test-harnesses-20 if that is intended


### FINDING_6: Non-three-slot tally loop passes unsafe `--slot` / missing voter-tool args
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Beyond the invalid id-grammar, the planned `parse-rate-check` replacement adds `--slot "$slot"` and `--voter-tool` in branches where `slot` is not initialized (legacy non-three-slot loop under `set -u`). Tally can abort on unset variables or call parse-rate-check with wrong tool labels even after grammar is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation, Codex-Pragmatic: In the three-slot loop pass VOTER_TOOLS[$slot] and --slot "$slot". In the legacy loop pass a fixed voter-tool label and omit --slot, or derive a local index.
  - From Codex-Requirements: in the legacy else branch either omit `--slot` or enumerate voter files with an initialized slot/tool label before calling `parse-rate-check`


### FINDING_7: Item 4 testing strategy maps to wrong harness
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan's testing strategy maps Item 4 (tally-code-votes voter-exclusion consolidation) to `scripts/test-prompt-template-invariants.sh`. An implementer may skip `python/test_review_tally.py` (or `make test-tally-code-votes`) coverage for the parse-rate-check swap, letting tally regressions slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: List python/test_review_tally.py (or make test-tally-code-votes) under Item 4 validation instead of the prompt-template harness



### FINDING_1: Plan-review-loop harness `-k` filter omits new NOT_SUBSTANTIVE count test
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Item 2 adds `test_embedded_plan_review_loop_not_substantive_count_emitted`, but `make test-plan-review-loop` still runs pytest with `-k 'loop_dedup or migrated_collector'` only. Lint shard 10 may never execute the new NOT_SUBSTANTIVE count pins, so a regression in the embedded plan-review-loop body can pass CI while Item 2 appears done.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the Makefile test-plan-review-loop -k expression (or add a dedicated harness target) so the new test runs in the lint shard that owns plan-review-loop coverage


### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/test_plan_review.py:31-47
- **Concern**: [SCOPE-REDUCTION] Proposed NOT_SUBSTANTIVE regional assertion is over-specific. Scenario: The embedded _count_collector_evidence helper counts wildcard non-OK statuses and does not contain NOT_SUBSTANTIVE, so the proposed test either fails or forces unrelated embedded-asset churn
- **Proposed resolution**: Keep the existing NOT_SUBSTANTIVE body pin. In the regional test, assert the non-OK increment path and the _write_round_summary COLLECT_FAILURE_COUNT emit only




### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:114-120
- **Concern**: Item 4 testing strategy claims `make test-tally-code-votes` covers voter-exclusion consolidation, but `python/test_review_tally.py` has no case that exercises narrative-only voter exclusion through the proposed `voting parse-rate-check` tally path. Scenario: Switching `python/legacy_review_shell/tally-code-votes.sh` from `parse-rate-diag-matches` (sidecar presence) to live `parse-rate-check` changes quorum math on the tally hot path; existing tally tests only use well-formed vote lines (e.g. `test_tally_three_voter_mixed_outcomes`), so a miswired KV branch or inverted OK/non-OK handling would still pass `make test-tally-code-votes` and `make lint`
- **Proposed resolution**: Revise the Testing strategy bullet for Item 4 to stop claiming tally harness coverage for the consolidation, or add one targeted `python/test_review_tally.py` case with a narrative-only voter file and assert it is excluded when `PARSE_RATE_STATUS=NOT_SUBSTANTIVE`



