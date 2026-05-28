### FINDING_1: unresolved dot-dot tail escapes tmpdir allowlist
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Non-existent `--design-tmpdir` candidates can pass the allowlist by string-prefix matching an unresolved tail containing `..`, then `mkdir -p` resolves the path outside the allowed roots. The regression tests also miss this malicious post-ancestor `..` escape case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: relative design tmpdir paths depend on caller CWD
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The validator does not require absolute paths, so relative `--design-tmpdir` values are resolved against the process working directory and can pass or fail depending on launch location.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: lib-plan-voter-coverage quiet dependency is implicit
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-plan-voter-coverage.sh` sources `lib-quiet.sh`, making consumers dependent on quiet initialization order and risking contract KV output to stdout when `larch_quiet_init` has not run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] changelog references removed voter coverage filename
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Historical `CHANGELOG.md` entries still reference `scripts/lib-voter-coverage.sh`; this is outside the acceptance grep scope but may confuse readers looking for the removed filename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: regular-file leaf is accepted as valid tmpdir
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The validator can accept an existing regular-file leaf under an allowed prefix, causing a later `mkdir -p` failure instead of a clear validation rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: newline or carriage return in tmpdir path is not rejected
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Embedded newline or carriage return characters in `--design-tmpdir` are not rejected before ancestor/tail splitting, which can make validation operate on the wrong path shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] remaining design tmpdir consumers are unwired
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Multiple other `--design-tmpdir` consumers still do not call `larch_design_tmpdir_validate`, so misconfigured orchestrators or publish/preview paths can still write outside the allowlist pending the deferred broader sweep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: directory symlink escape is missing from tmpdir harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The tmpdir validator harness tests a symlink to a non-directory leaf but not a directory symlink under the sessions root pointing outside the allowlist, leaving a prefix-matching symlink escape without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: consumer tests do not prove validator wiring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Consumer harnesses do not exercise the new `--design-tmpdir` validator wiring, so removing validation from wired scripts could pass library-only tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: file-leaf symlink test depends on /etc/passwd
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The file-leaf symlink rejection test is conditional on `/etc/passwd`, so minimal environments without that file skip the only leaf-symlink coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] relevant-checks does not map tmpdir validator changes to its harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/relevant-checks.sh` has no direct mapping from `lib-design-tmpdir` changes to `make test-lib-design-tmpdir`, so developers relying on relevant checks may miss the focused harness until broader linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] tmpdir validate-to-mkdir TOCTOU remains
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Callers validate one path but later `mkdir` the original argv, leaving a symlink-swap window where a validated shared tmpdir can be replaced before artifact creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] emit_kv allows newline keys
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `emit_kv` does not reject newlines in keys, which could split FD 3 parsers if keys ever become dynamic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: emit_kv failure can abort mid status block
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-plan-voter-coverage.sh` can abort mid status block under `set -e` if `emit_kv` rejects a newline-bearing value, leaving partial interleaved KV output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: multiline waterfall warning can abort dispatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `dispatch-plan-voters.sh` forwards `WARN` values to `emit_kv` without newline sanitization, so a multiline warning can abort dispatch after voters have launched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] branch includes unrelated work
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch includes substantial unrelated `#3122` work alongside the OOS hardening, so reviewers evaluating this PR against the plan should isolate the relevant commits from the broader branch delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
