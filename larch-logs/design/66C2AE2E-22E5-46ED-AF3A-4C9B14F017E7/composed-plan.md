## Plan

## Approach

1. Add a data-driven structure checker for alias, bug, design, implement, learn-from-bugs, research, and review only.
2. Represent simple contracts as immutable pin records in `skill_structure_pins.py`; retain executable, CLI-backed, parser-dependent, and otherwise non-equivalent assertions as explicitly named tests.
3. Support `contains`, `absent`, `exact-count`, `ordered`, `same-line`, bounded cross-file, and `adjacent-pair-count-at-least` predicates.
4. Encode legacy match semantics in every applicable pin: fixed-string versus regex matching, physical-line versus matching-line versus substring count units, exact versus at-least comparators, and exact full-line versus substring ordered matching.
5. Make ordered pins use an explicit `match_mode`; migrated design ordering assertions default to exact full-line matching. Diagnostics must identify a missing first anchor, missing second anchor, or reversed order with line numbers.
6. Implement adjacent-pair counting as exact consecutive full-line pairs with a minimum count, preserving `assert_followed_count_at_least` behavior and labels from the design harness.
7. Emit deterministic failures naming the skill, stable legacy label, target path, predicate, expected inputs, observed counts where relevant, and relevant anchors.
8. Give every migrated assertion a stable pytest parameter ID derived from its skill and legacy label; maintain an inventory mapping specialized named tests to their legacy labels.
9. Add the pytest lane before deleting the Bash lane. Run both lanes, compare label coverage and diagnostics, then delete the legacy files only after parity passes.
10. Keep all seven focused Make target names, but remove their converted pytest recipes from `test-harnesses-2`, `test-harnesses-4`, and `test-harnesses-5`. Preserve the shard checker’s Bash-only contract; focused coverage continues through the seven targets and `make py-test`.
11. Register all seven deleted shell harnesses and six companion Markdown files in the retired-script manifest. Remove their residual-Bash entries and all tracked full-path references.
12. Do not migrate other structure harnesses or alter skill runtime behavior.

## Files to modify/create

### NEW: python/tests/skills/skill_structure_pins.py

- Define frozen, typed pin records, predicate kinds, match modes, count units, and comparators.
- Store per-skill pin tables for the seven scoped skills.
- Preserve legacy assertion labels in stable IDs, including lettered and numbered labels.
- Store repo-relative target paths and explicit predicate inputs.
- Add adjacent-pair pins for the design harness assertions that require consecutive exact full-line pairs and minimum counts.
- Require ordered pins to declare exact-line or contains matching; use exact-line for migrated design ordering checks.
- Record count units and comparators for each count-based pin, including exact and at-least behavior.
- Keep composite or executable behavior out of the tables when data-only representation would reduce coverage.
- Validate pin-table integrity: unique IDs after normalization, supported predicates, nonempty needles, valid bounds, required predicate fields, valid match modes, count units, and comparators.

### NEW: python/tests/skills/test_skill_structure.py

- Implement the shared predicate evaluator and parameterized pytest tests.
- Resolve targets from the repository root rather than the ambient working directory.
- Cache file reads without hiding missing-file failures.
- Preserve fixed-string and regex semantics from each legacy assertion.
- Implement exact full-line ordered matching, including missing-first, missing-second, and reversed-order diagnostics with line numbers.
- Implement physical-line, matching-line, substring, exact-count, at-least, and adjacent-pair count behavior with observed-count diagnostics.
- Implement exact consecutive full-line adjacent-pair counting with a minimum threshold.
- Port specialized checks as named tests, including design classifier execution, CLI-backed lint checks, structured block extraction, branch slicing, Markdown fence inspection, executable absence checks, and assertions not faithfully represented as pins.
- Maintain a checked legacy-label inventory covering both parameter IDs and specialized named tests.
- Add checker self-tests for positive and negative behavior of every predicate, count mode, comparator, and ordered match mode.
- Test malformed and duplicate pin definitions so configuration errors fail loudly.
- Define a central per-skill focused-selection registry and test that every pin and named specialized case belongs to its focused Make selection.
- Ensure pytest collection exposes stable IDs suitable for focused `-k` selection.

### UPDATED: Makefile

- Keep all seven focused target names.
- Replace each Bash recipe with a timed `python3 -m pytest python/tests/skills/test_skill_structure.py` invocation using the corresponding focused selection.
- Ensure each focused selection includes its parameterized pins and named specialized tests.
- Remove the seven converted targets from `test-harnesses-2`, `test-harnesses-4`, and `test-harnesses-5`, preserving the shard checker’s Bash-recipe inventory contract.
- Preserve `harness-mark` labels and aggregate behavior outside the required shard-membership change.

### UPDATED: docs/linting.md

- Update all seven focused-target entries to describe the shared pytest structure suite.
- Name the relevant skill selection and specialized tests instead of deleted Bash scripts.
- Update shard documentation to state that converted pytest structure targets are intentionally outside the Bash shard lists and are covered by focused targets plus `make py-test`.
- Preserve the remaining shard and `make lint` behavior descriptions.

### UPDATED: scripts/residual-bash-paths.txt

- Remove the seven deleted shell harness paths.
- Preserve ordering for all remaining residual Bash paths.

### UPDATED: python/migrated-scripts.tsv

- Add the seven retired `.sh` paths and six retired companion `.md` paths with the current issue attribution.
- Keep paths literal only in this manifest, as required by the retired-script lint contract.

### UPDATED: agent-lint.toml

- Remove allowlist entries and comments that exist only for the seven shell harnesses and six companion files.
- Update nearby ownership comments to name the pytest suite where the ownership distinction remains useful.
- Do not broaden exclusions for the new tests unless lint proves a narrow entry is required.

### UPDATED: .gitleaks.toml

- Remove the deleted `scripts/test-implement-structure.sh` path exemption.
- Do not replace it with a broader exemption.

### UPDATED: scripts/test-references-headers.sh

- Replace comments that assign structure ownership to deleted harnesses with the new pytest suite and relevant skill IDs.
- Preserve the actual header checks.

### UPDATED: scripts/test-references-headers.md

- Update the ownership split to reference `python/tests/skills/test_skill_structure.py`.
- Preserve the distinction between global reference-header checks and stricter research-local checks.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Remove reads and assertions against the deleted implement harness source.
- Retain direct assertions against production files.
- Leave structure-pin coverage to the new suite rather than testing another test’s internal source shape.

### REWRITTEN: scripts/test-alias-structure.sh

- Delete after the alias pytest lane passes alongside it.

### REWRITTEN: scripts/test-bug-structure.sh

- Delete after the bug pytest lane passes alongside it.

### REWRITTEN: scripts/test-design-structure.sh

- Delete after all data pins, exact-line ordering checks, adjacent-pair checks, and specialized design tests pass alongside it.

### REWRITTEN: scripts/test-implement-structure.sh

- Delete after all embedded Python assertions, fence checks, proximity checks, and branch checks have stable pytest equivalents.

### REWRITTEN: scripts/test-learn-from-bugs-structure.sh

- Delete after all learn-from-bugs pins pass alongside it.

### REWRITTEN: scripts/test-research-structure.sh

- Delete after all research pins and CLI-backed absence tests pass alongside it.

### REWRITTEN: scripts/test-review-structure.sh

- Delete after all review pins and CLI-backed absence tests pass alongside it.

### REWRITTEN: scripts/test-alias-structure.md

- Delete with its retired harness.

### REWRITTEN: scripts/test-bug-structure.md


### REWRITTEN: scripts/test-design-structure.md


### REWRITTEN: scripts/test-implement-structure.md


### REWRITTEN: scripts/test-research-structure.md


### REWRITTEN: scripts/test-review-structure.md


### UPDATED: agents/cursor-implementer.md

- Replace the retired harness path with the focused Make target or shared pytest path.

### UPDATED: python/larch/rendering/_rendering_generators.py

- Replace generated guidance that names a retired structure harness with the focused Make target or shared pytest suite.

### UPDATED: scripts/test-implement-cleanup-roundtrip.md

- Replace the retired implement-harness reference with the focused Make target or pytest path.

### UPDATED: skills/alias/SKILL.md

- Replace self-maintenance prose that names the retired alias harness with the focused Make target or pytest suite.

### UPDATED: skills/design/SKILL.md

- Replace retired structure-harness references with focused Make targets or stable pytest paths.
- Do not change Bash fences or `/design` runtime behavior.

### UPDATED: skills/design/scripts/design-clarify.md

- Update the structure-test coverage reference.

### UPDATED: skills/design/scripts/design-step-prelude.md


### UPDATED: skills/design/scripts/design-step3-continuation-entry.md


### UPDATED: skills/design/scripts/design-step3-entry-preview.md


### UPDATED: skills/design/scripts/design-step3-entry-state.md


### UPDATED: skills/design/scripts/design-step3-entry.md


### UPDATED: skills/design/scripts/design-step3-gate-b-bypass.md


### UPDATED: skills/design/scripts/design-step3-review.md


### UPDATED: skills/design/scripts/design-step35-settle.md


### UPDATED: skills/design/scripts/design-step35.md


### UPDATED: skills/design/scripts/design-step3b-entry.md


### UPDATED: skills/design/scripts/design-step3b-entry.sh

- Update the comment that names the retired design harness.

### UPDATED: skills/design/scripts/design-step3b-sanitize.md


### UPDATED: skills/design/scripts/design-step3b-tail.md


### UPDATED: skills/design/scripts/design-step5b-annotate.md


### UPDATED: skills/design/scripts/design-step5b-prepare.md


### UPDATED: skills/design/scripts/design-step5c.md


### UPDATED: skills/implement/scripts/step-18.md

- Replace the retired implement-harness reference with `make test-implement-structure` or the shared pytest path.

### UPDATED: skills/implement/scripts/step-5-resume.md

- Replace the retired implement-harness reference.

### UPDATED: skills/implement/scripts/step-5-review.md


### UPDATED: skills/implement/scripts/test-step-18.md


### UPDATED: skills/shared/orchestrator-never.md

- Replace the retired implement-harness reference without changing the orchestration rule.

### UPDATED: python/test_fixtures/plan-fidelity-calibration/diffs/33A6D738-B665-43BE-B89E-EDA96E7C887E_FINDING_3.diff

- Replace retired full-path literals while preserving the fixture’s intended plan-fidelity scenario.

### UPDATED: python/test_fixtures/plan-fidelity-calibration/diffs/66A96EAD-3088-4750-AE3A-64A0E11EABBD_FINDING_10.diff


### UPDATED: python/test_fixtures/plan-fidelity-calibration/diffs/E79F3F0B-4459-48FB-8241-5DDB90ABF050_FINDING_1.diff


### UPDATED: python/test_fixtures/plan-fidelity-calibration/plans/33A6D738-B665-43BE-B89E-EDA96E7C887E_FINDING_3.plan.txt

- Replace retired full-path literals with the focused target or pytest path.
- Preserve the fixture’s finding and plan semantics.

### UPDATED: python/test_fixtures/plan-fidelity-calibration/plans/E79F3F0B-4459-48FB-8241-5DDB90ABF050_FINDING_1.plan.txt


## Edge cases

- Treat missing target files as assertion failures, not collection errors with incomplete context.
- Preserve literal and regex semantics from every Bash `grep`, `awk`, and embedded-Python assertion.
- Reject empty needles as invalid configuration.
- Count non-overlapping substring occurrences consistently.
- Preserve the legacy unit and comparator for every count assertion.
- Require all same-line tokens on one physical line.
- Require adjacent-pair anchors to occupy exactly consecutive physical lines and report observed versus required pair counts.
- For ordered checks, use the encoded match mode and report missing first anchor, missing second anchor, or reversed order with line numbers.
- For bounded cross-file checks, report both target files, the anchor, the required token, and the bound.
- Preserve checks for files that must not exist.
- Preserve exact proximity windows used by the implement harness.
- Keep named tests included in their skill’s focused Make selection.
- Avoid parameter IDs that collide after punctuation normalization.
- Do not let retired full-path literals survive in fixtures, comments, generated guidance, or docs.

## Failure modes

- A broad parameterization may weaken a specialized assertion; keep those assertions as named tests.
- Substring ordering or generic count logic can silently weaken exact-line legacy checks; require explicit match modes, count units, and comparators.
- Focused Make selection may omit named tests; validate the selection registry against collected cases.
- Leaving pytest-focused targets in Bash shard prerequisites produces shard-coverage orphan failures; remove them atomically with the recipe conversion.
- Updating only executable references will leave prose references that fail `lint-retired-scripts`.
- Adding pytest tests without matching IDs makes legacy assertion parity unauditable.
- Removing agent-lint exclusions before stale comments are updated can produce confusing dead-reference findings.
- Fixture wording edits can alter plan-fidelity expectations; run the owning calibration tests after each fixture update.
- The design classifier test executes Bash against temporary state; keep it isolated and fail with captured output.

## Testing strategy

1. Before deletion, run each legacy Bash harness and its matching pytest selection:
   - `bash scripts/test-alias-structure.sh`
   - `bash scripts/test-bug-structure.sh`
   - `bash scripts/test-design-structure.sh`
   - `bash scripts/test-implement-structure.sh`
   - `bash scripts/test-learn-from-bugs-structure.sh`
   - `bash scripts/test-research-structure.sh`
   - `bash scripts/test-review-structure.sh`
   - The corresponding seven focused pytest selections after temporarily wiring or directly invoking pytest.
2. Audit the legacy-label inventory against collected pytest IDs and specialized named-test mappings. Require every legacy label to map to exactly one parameter ID or named test.
3. Run checker self-tests covering exact-line order, substring order where intentionally used, all count units and comparators, and adjacent-pair minimum counts.
4. Run the complete focused suite:
   - `python3 -m pytest python/tests/skills/test_skill_structure.py -q`
5. After deletion, run all seven focused Make targets.
6. Run `make test-harness-shards-coverage` and confirm it passes with the seven pytest targets removed from the Bash shard prerequisite lists.
7. Run `make lint-retired-scripts`.
8. Run residual-Bash checks, including `python3 python/cli.py residual-bash paths --root . --check-exists` and focused residual-Bash pytest coverage.
9. Run directly affected tests:
   - `python3 -m pytest python/tests/implement/test_implement_dispatch.py -q`
   - The plan-fidelity calibration tests that consume the edited fixtures.
10. Lint only changed Python files with the repository’s Python lint and type-check commands.
11. Run focused agent-lint, gitleaks, and documentation lint checks for the changed configuration and Markdown files.

## Acceptance

1. Before deletion, run each legacy Bash harness and its matching pytest selection:
   - `bash scripts/test-alias-structure.sh`
   - `bash scripts/test-bug-structure.sh`
   - `bash scripts/test-design-structure.sh`
   - `bash scripts/test-implement-structure.sh`
   - `bash scripts/test-learn-from-bugs-structure.sh`
   - `bash scripts/test-research-structure.sh`
   - `bash scripts/test-review-structure.sh`
   - The corresponding seven focused pytest selections after temporarily wiring or directly invoking pytest.
2. Audit the legacy-label inventory against collected pytest IDs and specialized named-test mappings. Require every legacy label to map to exactly one parameter ID or named test.
3. Run checker self-tests covering exact-line order, substring order where intentionally used, all count units and comparators, and adjacent-pair minimum counts.
4. Run the complete focused suite:
   - `python3 -m pytest python/tests/skills/test_skill_structure.py -q`
5. After deletion, run all seven focused Make targets.
6. Run `make test-harness-shards-coverage` and confirm it passes with the seven pytest targets removed from the Bash shard prerequisite lists.
7. Run `make lint-retired-scripts`.
8. Run residual-Bash checks, including `python3 python/cli.py residual-bash paths --root . --check-exists` and focused residual-Bash pytest coverage.
9. Run directly affected tests:
   - `python3 -m pytest python/tests/implement/test_implement_dispatch.py -q`
   - The plan-fidelity calibration tests that consume the edited fixtures.
10. Lint only changed Python files with the repository’s Python lint and type-check commands.
11. Run focused agent-lint, gitleaks, and documentation lint checks for the changed configuration and Markdown files.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 1800
diff_deleted: 3300
mechanical_churn: true
oversize_override: operator
diff_lines: 5100
