### FINDING_1: [OUT_OF_SCOPE] **risk-integration** — [`scripts/lib-external-launcher-common.sh:42-47`](scripts/lib-external-launcher-common.sh) — Codex and Cursor use different lock directories (`larch-codex-serial-…` vs `larch-cursor-serial-…`), so sequential fallback (e.g. [`skills/review-and-fix/scripts/review-and-fix.sh:222-236`](skills/review-and-fix/scripts/review-and-fix.sh), [`scripts/lint-fix-loop.sh:145-157`](scripts/lint-fix-loop.sh)) does not globally serialize Keychain across tools; a still-running Codex child can overlap a newly started Cursor child. **Suggested fix:** optional future hardening with a single shared “external auth” lock or documented acceptance that macOS Keychain tolerates this overlap.
- **Reviewer**: dyn-lock-semantics-output.txt
- **Concern**: - **risk-integration** — [`scripts/lib-external-launcher-common.sh:42-47`](scripts/lib-external-launcher-common.sh) — Codex and Cursor use different lock directories (`larch-codex-serial-…` vs `larch-cursor-serial-…`), so sequential fallback (e.g. [`skills/review-and-fix/scripts/review-and-fix.sh:222-236`](skills/review-and-fix/scripts/review-and-fix.sh), [`scripts/lint-fix-loop.sh:145-157`](scripts/lint-fix-loop.sh)) does not globally serialize Keychain across tools; a still-running Codex child can overlap a newly started Cursor child. **Suggested fix:** optional future hardening with a single shared “external auth” lock or documented acceptance that macOS Keychain tolerates this overlap.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] **risk-integration** — [`scripts/lib-external-launcher-common.sh:77-80`](scripts/lib-external-launcher-common.sh) — After `LARCH_EXTERNAL_SERIAL_LOCK_TRIES` attempts, `external_serial_lock_acquire` returns success with an empty lock path (fail-open), so scripts do not block indefinitely but mutual exclusion may be skipped under sustained contention. **Suggested fix:** surface a warning or non-zero exit if strict locking is required (library-level change; unchanged by this branch).
- **Reviewer**: dyn-lock-semantics-output.txt
- **Concern**: - **risk-integration** — [`scripts/lib-external-launcher-common.sh:77-80`](scripts/lib-external-launcher-common.sh) — After `LARCH_EXTERNAL_SERIAL_LOCK_TRIES` attempts, `external_serial_lock_acquire` returns success with an empty lock path (fail-open), so scripts do not block indefinitely but mutual exclusion may be skipped under sustained contention. **Suggested fix:** surface a warning or non-zero exit if strict locking is required (library-level change; unchanged by this branch).
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] **risk-integration** — [`scripts/lib-external-launcher-common.sh:87-95`](scripts/lib-external-launcher-common.sh) — `external_serial_lock_release_after` always schedules `sleep` + `rmdir` on a timer, independent of how long the child keeps touching Keychain or completing an auth handshake; the mutex only staggers launch starts, not whole-process Keychain usage. **Suggested fix:** treat as accepted Path B tradeoff unless product requirements change; a stricter design would hold the lock until post-auth or process exit (larger change than this issue).
- **Reviewer**: dyn-lock-semantics-output.txt
- **Concern**: - **risk-integration** — [`scripts/lib-external-launcher-common.sh:87-95`](scripts/lib-external-launcher-common.sh) — `external_serial_lock_release_after` always schedules `sleep` + `rmdir` on a timer, independent of how long the child keeps touching Keychain or completing an auth handshake; the mutex only staggers launch starts, not whole-process Keychain usage. **Suggested fix:** treat as accepted Path B tradeoff unless product requirements change; a stricter design would hold the lock until post-auth or process exit (larger change than this issue).
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] **risk-integration** — [`scripts/lint-fix-loop.sh:152-157`](scripts/lint-fix-loop.sh), [`skills/review-and-fix/scripts/review-and-fix.sh:231-236`](skills/review-and-fix/scripts/review-and-fix.sh) — `cursor_launcher_setup_auth_argv` (and thus Keychain-touching preflight) still runs **before** the new Cursor lock acquire, matching patterns such as [`scripts/launch-cursor-implement.sh:280-305`](scripts/launch-cursor-implement.sh) rather than wrapping all KeyChain I/O. **Suggested fix:** move acquire earlier only if preflight must be serialized too (would diverge from current reference launchers).
- **Reviewer**: dyn-lock-semantics-output.txt
- **Concern**: - **risk-integration** — [`scripts/lint-fix-loop.sh:152-157`](scripts/lint-fix-loop.sh), [`skills/review-and-fix/scripts/review-and-fix.sh:231-236`](skills/review-and-fix/scripts/review-and-fix.sh) — `cursor_launcher_setup_auth_argv` (and thus Keychain-touching preflight) still runs **before** the new Cursor lock acquire, matching patterns such as [`scripts/launch-cursor-implement.sh:280-305`](scripts/launch-cursor-implement.sh) rather than wrapping all KeyChain I/O. **Suggested fix:** move acquire earlier only if preflight must be serialized too (would diverge from current reference launchers).
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: .claude/rules/external-tool-launcher-parity.md:1-12
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Implementation plan overstates this rule as the regression guard for new serial-lock sites; rule paths omit the four touched scripts and the rule text does not cover serial locks. Future regression could drop lock calls without this rule firing on those paths. Align plan text with actual checks, extend rule paths if desired, or rely on explicit tests/relevant-checks.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: .claude/rules/external-tool-launcher-parity.md:2-3
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Rule paths omit the four edited spawn scripts while the plan calls this rule the regression guard. Future contributor removes serial-lock calls in e.g. scripts/run-negotiation-round.sh without the path-triggered parity rule or CI failing. Add those scripts (or a dedicated lint) to the parity rule paths: or add a harness/grep check that enforces acquire+release_after before codex/cursor spawns.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: branch diff only
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan requires /relevant-checks; not evidenced in code diff. Reviewer cannot confirm local lint ran without CI logs or PR notes. Ensure PR CI includes full harness path; paste relevant-checks output in PR if required by team process.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/run-negotiation-round.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New KeyChain serial lock prose implies all Cursor-side KeyChain I/O is serialized at spawn. Darwin `cursor_auth_preflight` still runs `security find-generic-password` before `external_serial_lock_acquire`, so overlapping negotiation or other KeyChain traffic is still possible during preflight even though `cursor agent` startup is locked. Clarify that the lock wraps the `cursor agent` invocation (and note preflight remains outside the lock), matching actual ordering in scripts/run-negotiation-round.sh:110-121.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/run-negotiation-round.sh:82-118
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No automated test targets the new serial-lock lines; repo has no test-run-negotiation-round harness. Linux CI always passes the acquire/release lines as no-ops; a macOS-only regression (missing lock, wrong order) ships unnoticed. Mirror scripts/test-launch-review.sh serial-lock assertions with LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin or add a focused negotiation-round harness.
- **Suggested revision**: Address the concern above.

