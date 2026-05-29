### FINDING_1: Document larch_err quiet-log mirroring
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: larch_err/larch_errf now mirror to both the quiet log and operator stderr, but docs still imply FD4-only diagnostics in places. This can mislead maintainers about what gets published into committed breadcrumbs and how to debug quiet output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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

### FINDING_4: Add quiet-active integration coverage for larch_err mirroring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Major Family-B harnesses run with `LARCH_QUIET_DISABLE=1`, so they do not exercise quiet-active `larch_err` mirroring into `larch-quiet-*.log` files that publication commits. A quiet-mode mirroring regression could pass those tests while real `/implement` run logs miss operator diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Add inherited invalid breadcrumb FD coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The planned `emit_breadcrumb` assertion update is comment-only, so there is no behavioral test pin for stale `LARCH_QUIET_BREADCRUMB_FD`. An invalid inherited FD could regress into early `larch_err` failure without harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

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

### FINDING_8: Quiet-log publication broadens committed stderr capture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Quiet-log-only publication can stage full session quiet logs plus `larch_err`-mirrored lines, not capped ndjson breadcrumb records. This may commit broader stderr captures than the old 1KiB breadcrumb stream and increases reliance on redaction discipline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Warn or error on invalid breadcrumb source hint
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: If `LARCH_BREADCRUMB_SOURCE_DIR` points outside allowed session tmpdirs, publication returns success without breadcrumbs. A misconfiguration can make commits appear successful while omitting expected breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Update run-log docs for quiet-log-only sourcing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `docs/run-logs.md` still describes live NDJSON stream files under session `breadcrumbs/`, but Stage 2 diagnostics now come from session-root quiet logs with operator-visible stderr via `larch_err`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Clarify interim breadcrumb monitor role
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Family-B background+monitor pairing remains mandatory by lint, but after callsite migration the monitor no longer receives `larch:bc` records and mostly waits for the sentinel. This creates an idle mandatory stack with little live-progress value until Piece 3 removes it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Fix breadcrumb-monitor wire-contract count
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/breadcrumb-monitor.md` says the wire contract has six env vars, but only five are documented after removing `LARCH_BREADCRUMB_STREAM`. Contributors reconciling Family-B wiring may miscount required paths or omit stream allocation while the monitor still requires `--stream`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] AGENTS.md still documents emit_breadcrumb
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `AGENTS.md` still lists `emit_breadcrumb` in the lib-quiet API contract. The reviewers identify this as deferred to Piece 3, but it remains stale contributor-facing documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Remove unused ci-wait test helper
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ci-wait.sh` keeps an unused `assert_stream_contains` helper after ndjson stream cases were removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Avoid EXIT trap eval risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `larch_quiet__exit_combo` evals a captured EXIT trap body. The reviewer marks this as a pre-existing same-UID trap-chaining risk unchanged by this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Redact implement-bootstrap stderr relay
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `implement-bootstrap.sh` relays gate/setup stderr through `larch_err` without redaction. The reviewer marks this as pre-existing rather than introduced by the migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Fail closed on ship-pr redaction failure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ship-pr.sh` may relay raw tool output through `larch_err` when `redact-secrets.sh` fails, creating a pre-existing token disclosure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Redact create-pr gh stderr
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `create-pr.sh` surfaces raw `gh` stderr through `larch_err`, which the reviewer identifies as a pre-existing operator transcript disclosure risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Separate unrelated branch hunks
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The PR diff includes Gate B presentation and design env-var docs outside the Stage 2 plan file list, forcing reviewers auditing Stage 2 scope to filter unrelated hunks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
