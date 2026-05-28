### FINDING_1: Fallback-counter persistence test misses mixed phase-2/phase-3 coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Item B-2 fallback-counter-file scenario at `scripts/test-dispatch-with-waterfall.sh:625-653` can pass without proving that both phase-2 relaunches and phase-3 Claude fallbacks contribute to persisted fallback counts. Several reviewers note the fixture likely yields `PHASE2_RELAUNCH_COUNT=0`, so regressions that omit phase-2 from persistence, omit/non-emit `COMBINED_FALLBACK_COUNT`, or allow zero combined increments may evade the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add assert_line or numeric guards requiring non-zero FALLBACK_COUNT and PHASE2_RELAUNCH_COUNT (or COMBINED_FALLBACK_COUNT) before the file comparison.
  - From cursor-specialist-correctness-output.txt: Reshape the fixture (e.g., reuse the cp-fail grouped pattern so one slot contributes phase-2 relaunches and another contributes phase-3 fallbacks) and assert both counters are non-zero before checking the persisted file equals `prior + fb + p2`.
  - From cursor-specialist-testing-output.txt: Use cp-stub-driven reuse failure for phase-2 plus phase-3 Claude fallback; assert both counters >=1 and COMBINED_FALLBACK_COUNT before checking the file.
  - From cursor-specialist-testing-output.txt: Add assert_line on COMBINED_FALLBACK_COUNT matching fb+p2.
  - From cursor-specialist-edge-cases-output.txt: Add assert_line on COMBINED_FALLBACK_COUNT and require fb+p2>=1 for this scenario.
  - From cursor-specialist-plan-fidelity-output.txt: Extend the fixture using the cp-fail grouped pattern so one slot increments PHASE2_RELAUNCH_COUNT and another reaches phase-3 Claude; assert both counters are >=1 and the file equals prior+fb+p2.


### FINDING_2: Agent-slot test does not match literal argv acceptance surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Item C test at `scripts/test-dispatch-with-waterfall.sh:238-240` checks prompt sidecar/rendered body behavior rather than the literal `--agent-file` presence in `CODEX_STUB_LOG` requested by the plan acceptance text. Reviewers disagree on whether argv is the right runtime surface, but agree the acceptance/test contract should be aligned or documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add grep -Fq -- '--agent-file' "$codex_log" per plan; fix misleading fail message referencing codex argv.
  - From cursor-specialist-correctness-output.txt: Optional — keep the sidecar/body checks and add a comment noting why `CODEX_STUB_LOG` is not the right surface for `--agent-file`, or stub/wrap `launch-review.sh` if argv-shape coverage is required.
  - From cursor-specialist-plan-fidelity-output.txt: Align acceptance text with sidecar assertions or add launch-review argv capture if codex_log greps remain mandatory.
  - From cursor-specialist-edge-cases-output.txt: Document sidecar contract in test comment or add both assertions if argv ever carries --agent-file.


### FINDING_4: Missing COMBINED threshold coverage on findings-present main path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh:326-337` covers the no-findings short-circuit threshold path, but not the post-tally/main-loop path with findings present. A regression in `emit_loop_kvs` or equivalent main-path degradation handling could escape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a minimal findings-present scenario asserting DEGRADED_PANEL=1, or narrow acceptance to short-circuit-only coverage.
  - From cursor-specialist-testing-output.txt: Add a findings-producing scenario with COMBINED_FALLBACK_COUNT above floor_half and assert DEGRADED_PANEL=1 with TALLY ok.


