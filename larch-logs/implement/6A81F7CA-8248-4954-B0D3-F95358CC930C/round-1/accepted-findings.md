### FINDING_12: Stamp decoy checks stamp existence but not decoy stamp content
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Stamp login decoy assertions verify stamp file existence (and env-key stamp stability) but not that login stamp content remains the expected decoy value; probe can write `login` stamp `false` while `CODEX_PRESENT=true` and checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror t6: assert login stamp content is true and env-key decoy unchanged
  - From cursor-specialist-testing-output.txt: Assert env-key stamp still reads true after run


### FINDING_16: Legacy strip test omits TMPDIR-wide sentinel leak scan
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Legacy strip integration test does not grep case `TMPDIR` recursively for `<REDACTED-TOKEN>`; sentinel can leak to non-captured probe artifacts undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep case TMPDIR recursively for <REDACTED-TOKEN> like t10-env-key-false
  - From cursor-specialist-security-output.txt: Add grep -Fr <REDACTED-TOKEN> on case TMPDIR fail-on-match
  - From cursor-specialist-plan-fidelity-output.txt: Add grep -Fr <REDACTED-TOKEN> on case TMPDIR fail-on-match


### FINDING_2: t8 auth-retry success path omits assert_no_probe_homes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The auth-retry case `t8` lacks `assert_no_probe_homes` unlike other probe paths; intermediate retry attempts may leak `larch-codex-probe-home.*` while the final attempt succeeds and CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add assert_no_probe_homes after t8
  - From cursor-specialist-correctness-output.txt: Add assert_no_probe_homes after t8 or log homes per retry in stub
  - From cursor-specialist-testing-output.txt: Add assert_no_probe_homes after t8 assertions
  - From cursor-specialist-security-output.txt: Add assert_no_probe_homes for SCRATCH/t8
  - From cursor-specialist-plan-fidelity-output.txt: Add assert_no_probe_homes for SCRATCH/t8


### FINDING_23: Env-key dispatch-failure omits events.jsonl sentinel leak check
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Env-key dispatch-failure test does not grep `coder-codex.events.jsonl` for sentinel leak; `<REDACTED-TOKEN>` in events would not fail the new test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Grep events.jsonl for <REDACTED-TOKEN> fail-on-match
  - From cursor-specialist-plan-fidelity-output.txt: Grep events.jsonl for <REDACTED-TOKEN> fail-on-match


