### FINDING_1: Document larch_err quiet-log mirroring
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: larch_err/larch_errf now mirror to both the quiet log and operator stderr, but docs still imply FD4-only diagnostics in places. This can mislead maintainers about what gets published into committed breadcrumbs and how to debug quiet output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: Fix breadcrumb-monitor wire-contract count
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/breadcrumb-monitor.md` says the wire contract has six env vars, but only five are documented after removing `LARCH_BREADCRUMB_STREAM`. Contributors reconciling Family-B wiring may miscount required paths or omit stream allocation while the monitor still requires `--stream`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Remove redundant quiet-source guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-larch-log.sh` keeps a redundant inner `quiet_source_ok` guard after ndjson publishing was removed, adding maintenance noise and suggesting dual-source behavior still exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: Remove obsolete LARCH_QUIET_BREADCRUMBS exports
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Several harnesses and `/implement` launch fences still export `LARCH_QUIET_BREADCRUMBS=1` even though lib-quiet ignores it after emit_breadcrumb removal. This can mislead maintainers about routing behavior and let stdout-only assertions miss the new stderr/quiet-log contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Align SECURITY breadcrumb-source semantics
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` still documents removed directory-level breadcrumb source rejection/fail-closed behavior. The current code treats an out-of-tmpdir source hint as a silent no-op or only rejects at per-file staging, so auditors and maintainers get the wrong security contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Redaction gap in direct larch_err operator output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Migrated callsites send progress and bail strings through `larch_err`/`larch_errf` on FD4, bypassing breadcrumb-monitor streaming redaction. Dynamic background output may reach the operator transcript without per-line `lib-redact-streaming` filtering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


