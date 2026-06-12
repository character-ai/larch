# Review Round 2

- Mode: `diff`
- 9 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Legacy 2a.5 resume skips no-sketch sentinel repair
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Legacy `STEP=2a.5` pause loads remap to `STEP=2b` without repairing or normalizing required `NO_SKETCHES` sentinel artifacts or rejecting conflicts. Step 2b prelude only creates the completion marker, so stale or missing sketch/dialectic artifacts can reach direct plan drafting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: Shared operational prose still advertises sketch and dialectic steps
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Shared progress examples and subskill topology prose still name sketch and dialectic phases. Users, contributors, or nested orchestrators may see removed breadcrumbs and assume the old topology still runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Step 3 review harness has orphaned launcher wiring
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-run-step3-review.sh` still has bare `run-step3-review` invocations and stale snapshot-helper wiring. Under `set -e`, the launcher aborts because it is invoked without `--design-tmpdir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Deleted-flow references remain in audits, docs, and prose tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Active tests and docs still reference deleted sketch, dialectic, snapshot, and debate-retry surfaces. Missing files can break lint/CI or make grep errors false-pass, while stale docs point operators at dead paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Research evals still target deleted dialectic flow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/research/references/eval-set.md` still scores answers against deleted dialectic protocol, Step 2a.5, and sketch-timeout behavior. Eval runs may expect files and flows that no longer exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Legacy 2a.5 pause-load regression coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pause/resume tests lack an explicit `STEP=2a.5` marker-load fixture that asserts remap to `STEP=2b` and sentinel normalization. Legacy resume behavior can regress without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Sentinel validation accepts stale extra content
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step2a.sh` accepts files that contain a sentinel line plus extra non-sentinel content. Stale sketch recommendations can pass validation and reach the drafter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Final-summary cost-line harness still expects SUMMARY_MODE_STRING
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-render-cost-line-callsites.sh` still asserts `SUMMARY_MODE_STRING=N/A` after the final-summary wrapper removed design mode/path output. The retained lint target fails, and residual route/docs references may remain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Active design references still route work to removed sketch phases
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Active design references still defer architecture or integration to sketch agents and Step 2a sketch prompts. `/design` can guide users toward nonexistent sketch phases instead of direct drafting and review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


