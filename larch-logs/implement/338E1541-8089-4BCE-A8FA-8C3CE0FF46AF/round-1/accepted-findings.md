### FINDING_1: docs/linting.md harness table dropped `test-get-issue-context` row
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The harness markdown table no longer documents `make test-get-issue-context` while the Makefile still exposes the target (and shard routing), so operators lose discoverability and docs drift from CI/Makefile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore the removed row next to the new bootstrap row
  - From cursor-specialist-edge-cases-output.txt: Restore the `test-get-issue-context` table row from `main` alongside the new row.

---


### FINDING_14: Unquoted here-doc re-expands ingest/bootstrap stdout blobs as shell syntax (command substitution risk)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Parsing KV blocks via unquoted here-doc can re-expand lines containing `$(...)`, executing unintended command substitution from crafted or accidental helper output during ingest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Replace heredoc with a read path that does not expand payload (e.g. process substitution + printf into while loop in current shell)
  - From cursor-specialist-security-output.txt: Use read loop fed from printf/process substitution without unquoted here-doc expansion of the full blob

---


### FINDING_15: Protocol “Execution Directive” still lists discrete infra scripts vs collapsed `implement-bootstrap`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The protocol line still enumerates discrete create-branch / session-entry-gate / session-setup as Step 0 first external actions, conflicting with the collapsed `implement-bootstrap.sh` narrative and risking wrong tool/script ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Rewrite clause (3) to mandate implement-bootstrap.sh --up-to-phase infra as the Step 0 infra entrypoint.

---


### FINDING_16: Anti-halt “critical boundary” still routes through standalone `session-setup.sh`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Recovery prose still implies running `session-setup.sh` after preflight audit as a standalone Step 0 hop, which misaligns with bootstrap-first Step 0 ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Rephrase to implement-bootstrap.sh then tracking or plan materialization blocks per the numbered Step 0 section.

---


### FINDING_17: Misspelled `SANBOX_TMP` identifier in bootstrap harness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Consistent misspelling increases maintainer confusion and typo risk when fixing or extending the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Rename consistently to `SANDBOX_TMP` (or similar).

---


### FINDING_2: Bootstrap breadcrumbs can interleave non-KV prose on stdout (quiet-disable / missing breadcrumb FD)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: With `LARCH_QUIET_BREADCRUMBS=1` and/or `LARCH_QUIET_DISABLE=1`, breadcrumb emission can land on stdout when `LARCH_QUIET_BREADCRUMB_FD` is unset, violating strict stdout-as-KV expectations and breaking consumers that parse stdout as `KEY=value` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Require numeric BREADCRUMB_FD before emitting, document the pairing, or otherwise guarantee breadcrumbs never use stdout in this entrypoint.
  - From cursor-specialist-testing-output.txt: Wire a default breadcrumb FD like review-core ensure_breadcrumb_fd or document+require FD; update implement-bootstrap.md breadcrumbs section accordingly
  - From cursor-specialist-edge-cases-output.txt: Send breadcrumbs to stderr under quiet-disable, require a numeric breadcrumb FD when breadcrumbs are enabled, or filter non-KV lines in `SKILL.md`; update the contract doc accordingly.

---


### FINDING_6: `write-session-env.sh` non-zero exit ignored after successful `session-setup`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: If `write-session-env.sh` returns non-zero, bootstrap can still exit 0 and later steps may use an incomplete `session-env`, masking failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Capture rc; on failure emit STEP_FAILED=write-session-env and exit 2 before ledgers

---


### FINDING_7: `session-setup` success path drops non-KV stderr/emit lines (stale-plugin advisory visibility)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Only stdout is KV-ingested and stderr is discarded on success, so known non-KV advisory lines (e.g. stale-plugin working-tree-ahead) may no longer reach the operator transcript compared to direct `session-setup` invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Forward known non-KV emit lines to larch_err or tee setup_out while parsing

---


### FINDING_9: Optional `--skip-codex-probe` / `--skip-cursor-probe` no longer forwarded to `session-setup`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Callers that relied on forwarding these argv flags through the old fenced Step 0 path cannot express the same skip-probe behavior via bootstrap without an alternative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-add argv forwarding or document caller-env-only replacement

---


