# Review Round 1

- Mode: `diff`
- 13 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: CI invokes deleted dialectic smoke test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.github/workflows/ci.yaml` still runs deleted `scripts/dialectic-smoke-test.sh`, so the `agent-sync` CI job fails on every PR with a missing script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Step 2b prompt still calls removed classification reader
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still tells the inline Step 2b drafter to call removed classification-reading commands, so live `/design` can fail before drafting the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Design report plot child rejects one-series schema
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/report-tokens/scripts/plot-cost-over-time.py` still expects two design series while the parent now emits one `All runs` series, so design plot generation fails validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Parse-design-argv harness has stale hard-flag cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-parse-design-argv.sh` has assertions without `run_case` and stale hard-flag or `HARD_REQUESTED` expectations, so the harness can fail or produce false positives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Structure harness still pins 2a.5 dialectic breadcrumb
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still expects a `2a.5` dialectic breadcrumb in `SKILL.md`, causing the structure harness to fail against the one-flow design surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Legacy no-sketch sentinel is rejected in Step 2a
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step2a.sh` treats legacy no-sketch artifacts as conflicting data instead of normalizing them to `NO_SKETCHES`, so resumed legacy designs can abort at Step 2a.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_3: Retired STEP=2a.5 route remains active
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pause save/load and the step registry still allow `STEP=2a.5`, and legacy markers are not remapped before validation, so resumed designs can route into deleted dialectic orchestration instead of Step 2b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Pause markers still emit retired TIER metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-save.sh` still derives and writes `TIER` metadata, preserving retired tier state in pause markers despite the tier-free design contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Pause-resume test still expects invalid TIER failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-pause-resume.sh` still expects invalid `TIER` data to fail, while pause load no longer validates `TIER`; the test should assert legacy `TIER` is ignored and not re-emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: Design summaries still print Mode or Path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/render-run-summary.sh` still emits `Mode: N/A` and may emit `Path` for design summaries, leaking retired flow metadata into tier-free final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Plan-size tests and docs still use hard-trigger tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Step 3, postplan, and summary docs still use retired `hard-trigger` or `cancelled-plan-size-hard` naming after runtime renamed the contract to `plan-size-trigger` and `cancelled-plan-size`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Postplan emit test still expects removed classification warning
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-postplan-emit.sh` still expects a removed `read-design-classification` warning case, so the harness retains stale contract coverage and can fail after the runtime removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Retired dialectic and tier references remain in docs and prompt surfaces
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Docs, rules, and design prompt references still describe retired dialectic, tier, or `hard_requested` flows, so operators or orchestrator prompts may follow deleted behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


