### OOS_1: [OUT_OF_SCOPE] Launcher harness misses content, dispatch, and rejection coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-awk-template-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not fully enforce the emitted `larch-run.sh` contract. Regressions in Python dispatch, argv passthrough, invalid-target rejection, plugin-root sourcing, or awk fallback parity could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-awk-template-fidelity-output.txt: Add a single shared constant (or extract the awk line from `implement-bootstrap.sh`) and assert it in both `test-implement-fence-shape.sh` (full old-shape awk line) and `test-implement-bootstrap.sh` (`assert_contains` on emitted `larch-run.sh`), plus sandbox executions that verify `/abs` and `../` paths exit 2 while valid stub `.sh`/`.py` targets succeed.


### OOS_2: [OUT_OF_SCOPE] linting docs describe the obsolete fence-shape contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `docs/linting.md` still describes the old all-fences plugin-root guard invariant instead of the new boundary between pre-bootstrap old-shape fences and post-Step-0 `larch-run.sh` one-liners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Partial-upgrade tmpdir coverage is missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-session-transition-safety-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the shape where `plugin-root.env` is present but `larch-run.sh` is absent during `--resume-plan-tail`. A regression could skip launcher backfill for migrated tmpdirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


