# test-stall-recovery-report.sh

Hermetic offline harness for `stall-recovery-report.sh`.

The harness builds a temporary plugin-like sandbox, copies the helper and required shared scripts, stubs GitHub-facing commands, and exercises the planned classifier, redaction, and retry cases without network access. Fixtures use synthetic `ship-pr-state.sh`, `session-env.sh`, failure-detail logs, and attempts files only.

Invariants:

- Public output surfaces must not contain injected raw classifier-input sentinels.
- `lint` must prove allowlist parity across TSV, code, and `stall-recovery-report.md`.
- Dry-run mode must not call `gh` or invoke `/larch:issue`.
- Missing `ship-pr-state.sh` must still honor `session-env.sh` stall tracking when present, and must not exit 3.
- Malformed present `ship-pr-state.sh` is the only exit-3 path.

Case map:

- Cases 1-7 cover classifier branches and retry behavior: transient infra, test failure, lint failure, dispatch failure, contract failure, unrecoverable terminal bail reasons, and same-cause-repeat with `RESUME_HINT=none`.
- Case 8 covers the session-env-only stall path: `ship-pr-state.sh` absent, `STALL_TRACKING=true` in `session-env.sh`, recoverable classification still succeeds.
- Case 9 covers invalid `--failure-detail-log` validation branches and asserts distinct stderr diagnostics for relative, outside-tmpdir, symlink, and non-regular paths.
- Cases 10-12 cover attempts-file idempotency and larch-dev-clone detection, including fork suppression.
- Cases 13-18 cover sanitization and public-surface generation: public-surface sentinel/token redaction, classifier-env metadata sanitization, redactor invocation, allowlist parity lint, byte-stable bug bodies, attempt-table output, and dry-run behavior.
- Cases 19-20 cover success-path read-back ordering, in-memory stall precedence, non-redispatch step handling, invalid-log fallback, in-memory-only recovery classification, stale-evidence precedence, and broader network-error matching.
- Case 21 covers exit-code boundaries, malformed state rejection, and `issue-input-file` rejection of body files outside `$IMPLEMENT_TMPDIR`.
