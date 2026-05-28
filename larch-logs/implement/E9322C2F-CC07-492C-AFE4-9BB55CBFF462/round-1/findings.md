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

### FINDING_3: Duplicated dispatch stub heredoc can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh:73-96` duplicates `write_dispatch` logic in `write_dispatch_combined_threshold` for one KV, increasing future maintenance drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Parameterize write_dispatch with COMBINED_FALLBACK_COUNT default 0 and reuse from threshold scenario.

### FINDING_4: Missing COMBINED threshold coverage on findings-present main path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh:326-337` covers the no-findings short-circuit threshold path, but not the post-tally/main-loop path with findings present. A regression in `emit_loop_kvs` or equivalent main-path degradation handling could escape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a minimal findings-present scenario asserting DEGRADED_PANEL=1, or narrow acceptance to short-circuit-only coverage.
  - From cursor-specialist-testing-output.txt: Add a findings-producing scenario with COMBINED_FALLBACK_COUNT above floor_half and assert DEGRADED_PANEL=1 with TALLY ok.

### FINDING_5: Consumers trust missing or inconsistent COMBINED_FALLBACK_COUNT
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Consumers in `skills/design/scripts/dispatch-plan-review-panel.sh`, `skills/design/scripts/plan-review-loop.sh`, and `skills/design/scripts/decompose-panel-dispatch.sh` trust `COMBINED_FALLBACK_COUNT` or default it to `FALLBACK_COUNT` when absent. If `PHASE2_RELAUNCH_COUNT` survives but `COMBINED_FALLBACK_COUNT` is missing or understated, degradation decisions may ignore phase-2-only overload.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Recompute or clamp COMBINED when PHASE2 is present; or fail closed on inconsistent/missing COMBINED.
  - From cursor-specialist-edge-cases-output.txt: Extend guard to recompute from PHASE2 when COMBINED missing; add harness omitting only COMBINED.

### FINDING_6: CP_STUB_FAIL_COUNT=0 silently disables intended failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: In `scripts/test-dispatch-with-waterfall.sh:82-94`, `CP_STUB_FAIL_COUNT=0` disables all stub failures silently. A misconfigured multi-fall-through scenario with `CP_STUB_FAIL_TARGET_CONTAINS` set could pass without exercising reuse-copy failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Treat 0 as unset/default 1 or error when fail target is configured.

### FINDING_7: [OUT_OF_SCOPE] Duplicate COMBINED parse blocks may diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Identical `COMBINED_FALLBACK_COUNT` parse blocks exist in three design scripts. The reviewer marks this as intentional plan parity but notes future edits may diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider a shared parse helper in a follow-up if duplication grows.

### FINDING_8: [OUT_OF_SCOPE] No-findings short-circuit omits dedup failure in DEGRADED_PANEL
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: In `skills/design/scripts/plan-review-loop.sh:532-536`, `_dedup_failed` does not contribute to `DEGRADED_PANEL` on the no-findings short-circuit, while the main path includes it. The reviewer marks this as pre-existing and not introduced by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Decompose threshold is hardcoded
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/decompose-panel-dispatch.sh:208` hardcodes `floor_half=4` for an 8-slot panel. Future panel slot-count changes could desynchronize the degradation threshold from actual dispatch size.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Derive floor_half from manifest slot count like dispatch-plan-review-panel.sh.
