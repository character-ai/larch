# Rejected Findings

# Review Round 1

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Makefile harness targets use narrow pytest -k filters
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retargeted harness Make targets use narrow `pytest -k` filters on a single file. Named harness targets pass while unrelated port tests in sibling files (e.g. `test_design_summary.py`) are never run by `make lint` shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Broaden -k filters or use markers; include test_design_summary.py in failure-report harness.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: No CLI-path behavioral or import-cycle tests for three new design verbs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No subprocess CLI tests for the three new verbs, `quiet_init` fd-3 contract, or `design_summary` ↔ `design_lifecycle` import cycle; core unit tests can pass while CLI wiring regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add subprocess CLI tests and explicit import-cycle smoke.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_14: Relevant-check rules omit python/clarify.py → clarify test mapping
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Relevant-check rules do not map modified `python/clarify.py` to clarify tests. A future `_stage_failed_clarify` regression may not run `test_clarify.py` during relevant-check selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add a direct python/clarify.py mapping to the clarify-focused target or py-test.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0


# Review Round 2

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: .bg-wait-active as directory breaks marker setup and poll-guard arming
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `.bg-wait-active` exists as a directory, marker setup fails but final-summary still completes. Poll-guard never arms because the hook only matches regular files. A corrupted or manual directory leaves every final-summary wait without mechanical anti-poll protection; the directory persists and blocks future marker installs until manual cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Detect non-regular marker paths before replace; repair or fail closed; consider skipping the completion sentinel when marker setup failed


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_12: test_checks does not pin new relevant-check targets
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_checks` does not pin new relevant-check targets `test-design-step-final-summary` and `design_summary` to `test-design-failure-report`. Accidental removal of `checks.py` mappings would not fail `test_checks`, dropping port coverage from relevant-checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add parametrized/assertion rows for those Makefile targets


Vote tally: YES=1 NO=2 JUDGE_ERROR=0


# Review Round 3



