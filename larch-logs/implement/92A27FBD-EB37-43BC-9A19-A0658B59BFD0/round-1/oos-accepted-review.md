### OOS_1: [OUT_OF_SCOPE] WARN/ERROR replay bypasses CR/LF/control-byte validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `replay_warn_error` prints raw WARN/ERROR records before applying the delegated parser’s CR/LF rejection, allowing carriage-return/control-byte telemetry forgery on stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Delegated parser failures are masked by process substitution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-delegation-errors-output.txt
- **Severity**: latent
- **Concern**: `phase_driver_read_result_env` is invoked in process substitution, so a nonzero delegate result can be hidden; a deleted, unreadable, or symlink-swapped source may yield an empty output file and overall exit 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-delegation-errors-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] relevant-checks does not route lib-phase-driver edits to read-result-env tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `read-result-env.sh` now depends on `lib-phase-driver.sh`, but `scripts/relevant-checks.sh` may not run `test-read-result-env` for lib-phase-driver-only changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Silent-skip parsing can let partial or corrupted handoff state proceed
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, dyn-behavioral-regression-output.txt, dyn-delegation-errors-output.txt
- **Severity**: latent
- **Concern**: Delegating to silent-skip parsing changes malformed or CR-tainted regular primary input from fail-closed to exit-0 partial output; Step 0b may continue if `INIT_STATUS=ok` survives while other required handoff keys are omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, dyn-behavioral-regression-output.txt, dyn-delegation-errors-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] design-init-runparams.md still documents fail-closed malformed-line behavior
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-delegation-errors-output.txt, dyn-behavioral-regression-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/design-init-runparams.md` still says malformed no-equals lines are rejected, while the implementation now silently skips them and exits successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-delegation-errors-output.txt, dyn-behavioral-regression-output.txt: Address the concern above.


