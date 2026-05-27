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

- Cases 1-7 cover classifier branches and retry behavior: transient infra, test failure, lint failure, dispatch failure, contract failure, unrecoverable terminal bail reasons, same-cause-repeat with `RESUME_HINT=none`, and retry-policy projection of the documented caps.
- Case 8 covers missing-`ship-pr-state.sh` behavior in both forms: absent-state-without-recoverable-evidence stays unrecoverable, while the session-env-only stall path (`STALL_TRACKING=true` plus recoverable bail/detail signal) still classifies recoverably.
- Case 9 covers invalid `--failure-detail-log` validation branches and asserts distinct stderr diagnostics for relative, outside-tmpdir, symlink, non-regular, and oversize paths.
- Cases 10-12 cover attempts-file idempotency and larch-dev-clone detection, including fork suppression.
- Case 13 additionally covers attempts-file write containment: init/record reject outside-tmpdir and symlinked attempts paths before writing.
- Cases 13-18 cover sanitization and public-surface generation: public-surface sentinel/token redaction across bug body, terminal comment, issue-input wrapper, and consumer chat-print payload, classifier-env metadata sanitization, redactor invocation, allowlist parity lint, byte-stable bug bodies, attempt-table output, and dry-run behavior.
- Cases 19-20 cover success-path read-back ordering, in-memory stall precedence, non-redispatch step handling, invalid-log fallback, in-memory-only recovery classification, stale-evidence precedence, and broader network-error matching.
- Case 18 covers dry-run propagation across `bug-body`, `bug-comment`, and `issue-input-file`.
- Case 19 covers the disk-clear ordering guard: in-memory stall remains authoritative until the false-on-disk rewrite is moved into place and re-read.
- Case 20 includes same-cause-repeat-at-step6, missing-log fallback, in-memory-only classification, lint-over-transient precedence, broader network wording, and standalone-auth unrecoverable classification.
- Case 21 covers exit-code boundaries, malformed state rejection, and `issue-input-file` rejection of body files outside `$IMPLEMENT_TMPDIR`.
