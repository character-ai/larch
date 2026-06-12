# Review Round 3

- Mode: `diff`
- 6 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Contiguous legacy sentinel literals fail acceptance grep
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-load.sh` still contains contiguous legacy `SIMPLE` and `HARD` sentinel literals, so the required acceptance grep fails even if runtime behavior works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: Trailing --hard after numeric issue is silently ignored
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `parse-design-argv.sh` ignores `--hard` when it appears after a numeric issue positional, so `/design 3249 --hard` exits successfully instead of rejecting the obsolete flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Legacy no-sketch normalization only runs for STEP=2a.5
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pause-load repairs legacy no-sketch sentinels only for original `STEP=2a.5`, so legacy pauses restored at `STEP=2b` can keep stale sentinel artifacts that Step 2b no longer recognizes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Missing split-fragment legacy sentinel normalization coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pause-resume tests do not seed legacy no-sketch sentinel content via split fragments and assert normalization to `NO_SKETCHES`, so regressions in legacy normalization or grep-clean source handling can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Step 2b prelude marks Step 2a complete without sentinel artifacts
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step2b-prelude.sh` can create the Step 2a completion marker even when required sentinel artifacts are missing, allowing an incomplete tmpdir into plan drafting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Design-route tier-mode summary remnants remain
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `SUMMARY_MODE_STRING` and tier-mode cancel-summary documentation remain after the tier-free final-summary refactor, leaving stale contract text and grep hits that may reintroduce Mode/Path output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


