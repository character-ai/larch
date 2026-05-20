### FINDING_1: [OUT_OF_SCOPE] **risk-integration** — [`scripts/lib-external-launcher-common.sh:42-47`](scripts/lib-external-launcher-common.sh) — Codex and Cursor use different lock directories (`larch-codex-serial-…` vs `larch-cursor-serial-…`), so sequential fallback (e.g. [`skills/review-and-fix/scripts/review-and-fix.sh:222-236`](skills/review-and-fix/scripts/review-and-fix.sh), [`scripts/lint-fix-loop.sh:145-157`](scripts/lint-fix-loop.sh)) does not globally serialize Keychain across tools; a still-running Codex child can overlap a newly started Cursor child. **Suggested fix:** optional future hardening with a single shared “external auth” lock or documented acceptance that macOS Keychain tolerates this overlap.
- **Reviewer**: dyn-lock-semantics-output.txt
- **Concern**: - **risk-integration** — [`scripts/lib-external-launcher-common.sh:42-47`](scripts/lib-external-launcher-common.sh) — Codex and Cursor use different lock directories (`larch-codex-serial-…` vs `larch-cursor-serial-…`), so sequential fallback (e.g. [`skills/review-and-fix/scripts/review-and-fix.sh:222-236`](skills/review-and-fix/scripts/review-and-fix.sh), [`scripts/lint-fix-loop.sh:145-157`](scripts/lint-fix-loop.sh)) does not globally serialize Keychain across tools; a still-running Codex child can overlap a newly started Cursor child. **Suggested fix:** optional future hardening with a single shared “external auth” lock or documented acceptance that macOS Keychain tolerates this overlap.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_2: [OUT_OF_SCOPE] **risk-integration** — [`scripts/lib-external-launcher-common.sh:77-80`](scripts/lib-external-launcher-common.sh) — After `LARCH_EXTERNAL_SERIAL_LOCK_TRIES` attempts, `external_serial_lock_acquire` returns success with an empty lock path (fail-open), so scripts do not block indefinitely but mutual exclusion may be skipped under sustained contention. **Suggested fix:** surface a warning or non-zero exit if strict locking is required (library-level change; unchanged by this branch).
- **Reviewer**: dyn-lock-semantics-output.txt
- **Concern**: - **risk-integration** — [`scripts/lib-external-launcher-common.sh:77-80`](scripts/lib-external-launcher-common.sh) — After `LARCH_EXTERNAL_SERIAL_LOCK_TRIES` attempts, `external_serial_lock_acquire` returns success with an empty lock path (fail-open), so scripts do not block indefinitely but mutual exclusion may be skipped under sustained contention. **Suggested fix:** surface a warning or non-zero exit if strict locking is required (library-level change; unchanged by this branch).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: [OUT_OF_SCOPE] **risk-integration** — [`scripts/lib-external-launcher-common.sh:87-95`](scripts/lib-external-launcher-common.sh) — `external_serial_lock_release_after` always schedules `sleep` + `rmdir` on a timer, independent of how long the child keeps touching Keychain or completing an auth handshake; the mutex only staggers launch starts, not whole-process Keychain usage. **Suggested fix:** treat as accepted Path B tradeoff unless product requirements change; a stricter design would hold the lock until post-auth or process exit (larger change than this issue).
- **Reviewer**: dyn-lock-semantics-output.txt
- **Concern**: - **risk-integration** — [`scripts/lib-external-launcher-common.sh:87-95`](scripts/lib-external-launcher-common.sh) — `external_serial_lock_release_after` always schedules `sleep` + `rmdir` on a timer, independent of how long the child keeps touching Keychain or completing an auth handshake; the mutex only staggers launch starts, not whole-process Keychain usage. **Suggested fix:** treat as accepted Path B tradeoff unless product requirements change; a stricter design would hold the lock until post-auth or process exit (larger change than this issue).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] **risk-integration** — [`scripts/lint-fix-loop.sh:152-157`](scripts/lint-fix-loop.sh), [`skills/review-and-fix/scripts/review-and-fix.sh:231-236`](skills/review-and-fix/scripts/review-and-fix.sh) — `cursor_launcher_setup_auth_argv` (and thus Keychain-touching preflight) still runs **before** the new Cursor lock acquire, matching patterns such as [`scripts/launch-cursor-implement.sh:280-305`](scripts/launch-cursor-implement.sh) rather than wrapping all KeyChain I/O. **Suggested fix:** move acquire earlier only if preflight must be serialized too (would diverge from current reference launchers).
- **Reviewer**: dyn-lock-semantics-output.txt
- **Concern**: - **risk-integration** — [`scripts/lint-fix-loop.sh:152-157`](scripts/lint-fix-loop.sh), [`skills/review-and-fix/scripts/review-and-fix.sh:231-236`](skills/review-and-fix/scripts/review-and-fix.sh) — `cursor_launcher_setup_auth_argv` (and thus Keychain-touching preflight) still runs **before** the new Cursor lock acquire, matching patterns such as [`scripts/launch-cursor-implement.sh:280-305`](scripts/launch-cursor-implement.sh) rather than wrapping all KeyChain I/O. **Suggested fix:** move acquire earlier only if preflight must be serialized too (would diverge from current reference launchers).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

