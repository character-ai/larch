### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step5b-prepare.md:35
- **Concern**: Two design wrapper docs still cite the retired harness but are absent from the firm file list. Scenario: After deletion, `design-step5b-prepare.md` and `design-step5c.md` keep `scripts/test-design-structure.sh` coverage prose; `make lint-retired-scripts` can fail despite the migration
- **Proposed resolution**: Add `### UPDATED: skills/design/scripts/design-step5b-prepare.md` and `### UPDATED: skills/design/scripts/design-step5c.md` retargeting coverage to `make test-design-structure` or the shared pytest selection



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:255-285
- **Concern**: Design anchored line-window checks are not named in the pytest migration contract. Scenario: Six `check_context_before` / `check_context_before_step3_launch` assertions require a literal within N physical lines before a skill anchor (including the Step 3 launch fence); generic `contains` or cross-file pins would pass when the text is far above the anchor
- **Proposed resolution**: In `test_skill_structure.py`, add named tests (or a `context-before` pin with line bounds and the Step 3 launch anchor rule) that preserve each legacy label and window size



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:31-39
- **Concern**: Implement byte-window `require_near` parity is underspecified in the NEW test file contract. Scenario: About twenty `require_near` calls pin bgjob, self-review, bootstrap-recovery, ship, and ci-fix contracts with per-site limits of 900–2200 bytes; Approach item 3 omits a `near` predicate and the `test_skill_structure.py` specialized-test list never names proximity migration
- **Proposed resolution**: In `skill_structure_pins.py` add a `near` pin (anchor, needle, byte_limit) or list every `require_near` legacy label under implement specialized named tests; require each in the legacy-label inventory and focused `make test-implement-structure` selection



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-research-structure.sh:110-117
- **Concern**: Research and review header checks need a first-20-lines bound, not whole-file contains. Scenario: Research uses `head -n 20` plus anchored `^\*\*Consumer\*\*:` (and siblings); review uses `head -n 20` plus `grep -Fq` for opening headers—whole-file `contains` pins would pass if headers drift below line 20
- **Proposed resolution**: Add research/review named tests (or a `prefix-lines` pin with line count and anchored vs substring mode) covering every legacy header assertion



### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:191
- **Concern**: Positive wrapper executable-bit checks are omitted from the specialized-test list. Scenario: The harness fails when listed `skills/implement/scripts/*.sh` wrappers exist but lose `+x`; the plan only names executable absence checks, so non-executable wrappers could pass after deletion
- **Proposed resolution**: Add an implement specialized named test mirroring the wrapper list and `os.access(..., os.X_OK)` assertions, and map legacy labels in the inventory



### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/skills/skill_structure_pins.py:1
- **Concern**: [SCOPE-REDUCTION] `bounded cross-file` predicate has no legacy consumer. Scenario: None of the seven Bash structure harnesses implement a bounded cross-file assertion; shipping an unused predicate adds evaluator and self-test surface without parity benefit
- **Proposed resolution**: Drop `bounded cross-file` from Approach item 3, pin kinds, and self-tests unless a concrete legacy label is identified first



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Implement byte-window proximity checks are not an explicit migration deliverable. Scenario: scripts/test-implement-structure.sh embeds ~20 require_near calls with per-site limits of 900–2200 bytes (bgjob pins, bootstrap/self-review mandatory reads, ship/ci-fix matrix reads). Approach item 3 and the NEW test_skill_structure.py specialized-test bullet list omit proximity/near while only edge-case prose mentions windows; generic contains/ordered/same-line pins accept distant co-occurrence and drop parity.
- **Proposed resolution**: Add an explicit implement proximity named-test family (or a near pin with anchor, token, max_bytes, and legacy labels) to skill_structure_pins.py/test_skill_structure.py, include every legacy label in the inventory, and keep it inside each focused Make selection.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Design anchored line-window context checks lack an explicit specialized-test contract. Scenario: scripts/test-design-structure.sh uses check_context, check_context_before, and check_context_before_step3_launch (e.g., Step 3 launch lines 255–266 and Step 5c lines 271–285) to require literals only within N lines before/after anchors. None of the listed pin predicates encode anchored windows; whole-file contains passes when the token appears elsewhere.
- **Proposed resolution**: Name a design context-window specialized named-test module in the NEW/UPDATED test_skill_structure.py contract, port every check_context* assertion with the same anchors and line bounds, and map each legacy fail label in the inventory.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Research and review line-bounded header and line-order checks are not spelled out. Scenario: scripts/test-research-structure.sh and scripts/test-review-structure.sh require Consumer/Contract/When-to-load headers in the first 20 lines (research lines 112–115; review lines 274–275) and research also enforces line_for ordering chains (validation sidecar lines 297–305; degraded-tools vs activation lines 347–349). Plan pins CLI-backed absence tests but not these line-bounded contracts; migrated contains pins would pass relocated headers and shuffled steps.
- **Proposed resolution**: Add explicit research/review specialized named tests for first-20 header triplets and line_for line-order chains; register their legacy labels and include them in focused Make selections.



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Positive wrapper executable-bit checks are omitted from the specialized-test list. Scenario: scripts/test-implement-structure.sh lines 184–191 require a dozen skills/implement/scripts/*.sh wrappers to be executable (os.access X_OK). The plan names only executable absence checks; deleting the harness without a positive X_OK named test lets non-executable wrappers ship while structure CI stays green.
- **Proposed resolution**: Add a named test_implement_wrapper_executable_bits (or equivalent) covering the same wrapper set and legacy labels; keep it in the implement focused selection.



### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/linting.md:404
- **Concern**: [SCOPE-REDUCTION] Plan over-requires seven focused-target documentation rows. Scenario: Only make test-alias-structure has a dedicated docs/linting.md table row today (line 404); the other six structure targets are Makefile-only. Requiring seven new rows expands doc churn without changing lint behavior once shard lists move to pytest.
- **Proposed resolution**: Revise the single existing alias row plus shard-coverage prose to describe the shared pytest suite and per-skill -k selections; do not invent six redundant table entries.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Implement byte-proximity checks lack a migration hook. Scenario: scripts/test-implement-structure.sh embeds ~20 require_near assertions with per-site 900–2200 byte limits for bgjob, self-review, bootstrap-recovery, ship, and ci-fix contracts. Approach item 3 and the pin predicate list omit a near/proximity evaluator; edge cases mention proximity windows but name no pin kind or named-test inventory. Migrating only contains/ordered/same-line pins would let distant tokens satisfy legacy contracts.
- **Proposed resolution**: Add a same-file near predicate (anchor, token, max_bytes) with observed-distance diagnostics, migrate every legacy require_near label into implement pins or an explicit named-test table, and keep the legacy-label inventory one-to-one.



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Design anchored line-window checks are not represented. Scenario: scripts/test-design-structure.sh uses check_context_before and check_context_before_step3_launch to require tokens within 18–35 lines before Step 3/5c anchors in skills/design/SKILL.md. Listed predicates (contains, ordered, same-line, cross-file) cannot express bounded pre-anchor windows; whole-file contains or global ordered pins would pass when required bgjob contract text sits far above the anchor.
- **Proposed resolution**: Port each context_before/context_before_step3_launch assertion as a named specialized test or a line-window-before-anchor pin, and map every legacy label in the inventory.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Research header triplet first-20-lines bound is unspecified. Scenario: scripts/test-research-structure.sh lines 110–117 require Consumer/Contract/When-to-load headers via head -n 20 plus anchored grep -E. A migrated whole-file contains pin would pass if headers drift below line 20.
- **Proposed resolution**: Add a research named test (or first-N-lines pin) that preserves the head -n 20 anchored-regex semantics and inventory mapping.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Positive wrapper executable-bit checks are omitted. Scenario: Only scripts/test-implement-structure.sh lines 184–191 assert os.access X_OK on implement wrapper .sh siblings. The specialized-test list mentions executable absence only, not required executable permissions. Deleting the harness without a pytest equivalent would let non-executable wrappers ship while structure tests pass.
- **Proposed resolution**: Add an implement named test that preserves the positive X_OK wrapper list and legacy labels.



### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-review.md:30
- **Concern**: Retired-path reference is outside the firm update list. Scenario: step-5-review.md maintenance prose still names scripts/test-implement-structure.sh. Plan failure modes warn that prose references break lint-retired-scripts, but this file is not listed under ### UPDATED. After deletion, make lint-retired-scripts can fail even when listed files are updated.
- **Proposed resolution**: Add ### UPDATED: skills/implement/scripts/step-5-review.md to retarget maintenance prose to make test-implement-structure or the shared pytest suite.



### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:78
- **Concern**: assert_wrapper_pause_before_work prose cites a nonexistent helper. Scenario: SKILL.md anti-pattern #3 points at scripts/test-design-structure.sh assert_wrapper_pause_before_work, but no such symbol exists in the current harness or repo. Plan retargets harness paths in SKILL.md but does not fix the helper name, so post-migration guidance still references fiction.
- **Proposed resolution**: When editing skills/design/SKILL.md, replace the bogus helper with the actual pytest selection or named specialized test that enforces wrapper pause-before-work ordering.



### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: scripts/test-quick-mode-docs-sync.md:101
- **Concern**: Shard removal leaves a directly affected documentation contract stale. Scenario: The plan removes `test-implement-structure` from `test-harnesses`, but this line still says the aggregate and `make lint` run it
- **Proposed resolution**: Add this file as `### UPDATED:` and state that the pytest-focused target runs separately and through `make py-test`



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:78
- **Concern**: Design SKILL.md cites nonexistent assert_wrapper_pause_before_work helper. Scenario: The harness string assert_wrapper_pause_before_work is not defined in scripts/test-design-structure.sh today. Retargeting only the path to the pytest suite leaves Anti-pattern #3 pointing at a helper that neither the deleted Bash harness nor the new suite exposes.
- **Proposed resolution**: When updating skills/design/SKILL.md, replace the harness citation with the focused Make target or pytest selection and drop the assert_wrapper_pause_before_work name; point pause ordering at the migrated wrapper pause-before-work named coverage instead.



### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/test-quick-mode-docs-sync.md:101
- **Concern**: Tracked prose still names retired implement structure harness. Scenario: scripts/test-quick-mode-docs-sync.md still lists test-implement-structure among harness prerequisites. After the shell harness is retired and registered in python/migrated-scripts.tsv, make lint-retired-scripts scans this reference and fails step 7 of the testing strategy.
- **Proposed resolution**: Add ### UPDATED: scripts/test-quick-mode-docs-sync.md to replace the retired path with make test-implement-structure or python/tests/skills/test_skill_structure.py in the harness prerequisite example.



### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/test-render-cost-line-callsites.sh:16
- **Concern**: Render-cost allowlist still whitelists retired design structure harness. Scenario: The allowed_re regex on line 16 still includes scripts/test-design-structure.sh. Once that path is in the retired manifest, lint-retired-scripts treats this allowlist entry as a tracked full-path reference and fails even though the render-cost lane itself still runs.
- **Proposed resolution**: Add ### UPDATED: scripts/test-render-cost-line-callsites.sh to drop scripts/test-design-structure.sh from allowed_re (do not broaden the allowlist).



### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Implement wrapper positive executable-bit checks are not named in the specialized-test port list. Scenario: The legacy implement harness asserts os.access(X_OK) for eleven skills/implement/scripts/*.sh wrappers (lines 184-191). The plan specialized-test bullet lists executable absence checks only, so deleting the Bash lane can let required wrappers lose +x while pytest still passes.
- **Proposed resolution**: Explicitly port test_implement_wrapper_siblings_executable (or equivalent) as a named implement specialized test covering the same wrapper list and X_OK semantics, and register it in the implement focused selection inventory.



### FINDING_23:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/skills/test_skill_structure.py
- **Concern**: Research first-20-lines header bound is not assigned to pins or named tests. Scenario: scripts/test-research-structure.sh lines 110-117 require Consumer/Contract/When-to-load headers within the first 20 lines of each research reference. Whole-file contains pins would accept headers moved below that boundary.
- **Proposed resolution**: Add a research named test (or bounded-line pin) that preserves the head -n 20 anchored-header semantics and map its legacy label in the inventory.



### FINDING_24:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: docs/linting.md:404
- **Concern**: [SCOPE-REDUCTION] Plan overstates seven linting.md target rows when only alias is documented. Scenario: docs/linting.md currently documents only make test-alias-structure; the other six focused structure targets have no table rows. Requiring seven row updates invites six redundant doc additions without improving migration verification.
- **Proposed resolution**: Revise the docs/linting.md task to update the existing alias row plus shard-coverage prose, and only add new rows if a target already has a dedicated entry today.



