# stall-recovery-report.sh

`stall-recovery-report.sh` is the deterministic helper for `/implement` Step 18a stall recovery. It classifies a persisted stall, tracks retry attempts, exposes the normative retry-cap table, detects larch dev clones, and composes sanitized public issue/report surfaces from fixed allowlists.

## Subcommands

- `classify --implement-tmpdir <path> [--in-memory-stall-tracking <true|false>] [--bail-reason <token>] [--failure-detail-log <path>] [--attempts-file <path>]`
  - Resolves `STALL_TRACKING` conservatively across the in-memory flag, `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, and `$IMPLEMENT_TMPDIR/session-env.sh`; missing ship-pr state does not suppress a session-env stall.
  - Emits `FAILURE_CLASS`, `FAILURE_SIGNATURE`, `RESUME_HINT`, `STALL_STEP`, `PHASE`, `STALL_TRACKING`, `BAIL_REASON`, and `EXIT_CODE`.
  - The emitted `STALL_STEP`, `PHASE`, and `BAIL_REASON` values are sanitized enums/tokens only; non-allowlisted bail reasons are redacted.
  - `FAILURE_CLASS` is one of `transient-infra`, `test-failure`, `lint-failure`, `dispatch-failure`, `contract-failure`, `same-cause-repeat`, or `unrecoverable`.
  - `RESUME_HINT` is one of `step2-impl`, `step5-review`, `step8-shippr`, or `none`. `step3-checks` and `step6-checks` are never resume hints; symbolic/terminal `STALL_STEP` values also fail closed to `none` unless they are explicitly mapped.
- `init-attempts --implement-tmpdir <path> --attempts-file <path>`
  - Atomically initializes the attempts file with `version=1`, `created_utc=<ISO8601>`, and `attempt_count=0`. Existing files are left unchanged.
- `record-attempt --implement-tmpdir <path> --attempts-file <path> --class <class> --signature <hash> --resume-hint <hint> --outcome <token>`
  - Atomically appends `attempt.<N>.{class,signature,resume_hint,outcome,utc}` and increments `attempt_count`.
  - `--attempts-file` must be an absolute path inside `--implement-tmpdir`; the helper rejects symlinks, non-regular files, and cross-tmpdir writes before any write occurs.
- `retry-policy --class <class>`
  - Emits `FAILURE_CLASS`, `MAX_ATTEMPTS`, and `RETRY_DELAY` for the requested classifier. This is the helper's mechanical projection of the retry-cap table below.
- `is-larch-dev-clone [--working-tree-root <path>] [--implement-tmpdir <path>]`
  - Emits `LARCH_DEV_CLONE=true|false` using the canonical `skills/implement/SKILL.md` marker.
  - When `--implement-tmpdir` shows `FORKED_TARGET=true`, emits `false` so forked runs keep the consumer-facing action-required path instead of auto-filing a larch-dev issue.
- `bug-body --implement-tmpdir <path> --classification-file <path> [--output-file <path>]`
  - Writes a sanitized bug body and emits `BODY_FILE` and `DRY_RUN_DECISION`.
- `bug-comment --implement-tmpdir <path> --classification-file <path> --attempts-file <path> [--output-file <path>]`
  - Writes the sanitized terminal-failure comment, including the allowlisted retry-attempt table.
- `issue-input-file --implement-tmpdir <path> --classification-file <path> --body-file <path> [--output-file <path>]`
  - Writes a batch-mode `/larch:issue` input file. The first line is `### [Bug] /implement stall: <class> at <step>`.
  - `--body-file` must be an absolute path that resolves to a regular, non-symlink, readable file under `$IMPLEMENT_TMPDIR`.
- `lint`
  - Asserts allowlist parity: TSV surface keys == helper code surface keys == this document's surface keys.

## Surface Allowlists

The committed TSV at `stall-recovery-report-allowlists.tsv`, the helper's `lint` subcommand, and this table must remain byte-equivalent at the `surface + field_key` level.

<!-- stall-recovery-allowlist:begin -->
| surface | field_key | source | transform |
|---|---|---|---|
| bug-body | failing_step | STALL_STEP | enum |
| bug-body | failing_phase | PHASE | enum |
| bug-body | failure_class | FAILURE_CLASS | enum |
| bug-body | exit_code | EXIT_CODE | integer |
| bug-body | signature_hash | FAILURE_SIGNATURE | hex |
| bug-body | inferred_root_cause | FAILURE_CLASS | fixed-prose-template |
| bug-body | suggested_mitigation | FAILURE_CLASS | fixed-prose-template |
| bug-comment | failing_step | STALL_STEP | enum |
| bug-comment | failing_phase | PHASE | enum |
| bug-comment | failure_class | FAILURE_CLASS | enum |
| bug-comment | exit_code | EXIT_CODE | integer |
| bug-comment | signature_hash | FAILURE_SIGNATURE | hex |
| bug-comment | inferred_root_cause | FAILURE_CLASS | fixed-prose-template |
| bug-comment | suggested_mitigation | FAILURE_CLASS | fixed-prose-template |
| bug-comment | attempt_count | attempts-file | integer |
| bug-comment | attempt_table | attempts-file | allowlisted-attempt-fields |
| bug-comment | final_class | FAILURE_CLASS | enum |
| bug-comment | final_signature | FAILURE_SIGNATURE | hex |
| issue-input-file | title | FAILURE_CLASS+STALL_STEP | synthesized-heading |
| issue-input-file | body | bug-body | body-file |
| chat-print | failing_step | STALL_STEP | enum |
| chat-print | failing_phase | PHASE | enum |
| chat-print | failure_class | FAILURE_CLASS | enum |
| chat-print | exit_code | EXIT_CODE | integer |
| chat-print | signature_hash | FAILURE_SIGNATURE | hex |
| chat-print | inferred_root_cause | FAILURE_CLASS | fixed-prose-template |
| chat-print | suggested_mitigation | FAILURE_CLASS | fixed-prose-template |
<!-- stall-recovery-allowlist:end -->

## Classifier Evidence

- `transient-infra`: rate-limit, `network/auth issue`, broader `network error` / `network failure` wording, timeout, connection reset/refused, DNS/name-resolution failures, TLS handshake, temporary GitHub/API outage, service unavailable, or HTTP 5xx evidence in the validated failure-detail log or, when no validated detail log is available, the persisted state/session evidence. Standalone auth-failure wording is not treated as transient.
- `test-failure`: pytest, jest, vitest, rspec, go test, or generic failing-test evidence.
- `lint-failure`: lint-fix, shellcheck, markdownlint, pre-commit, relevant-checks, or generic lint-failed evidence.
- `dispatch-failure`: Step 2 dispatch envelope, wrapper-validation, or orchestrator-envelope-invalid evidence.
- `contract-failure`: `STALL_STEP=3` or `STALL_STEP=6`; these are checks contracts where prompt-side recovery edits are intentionally forbidden.
- `same-cause-repeat`: the current sanitized signature matches the latest durable attempt signature; `RESUME_HINT` is forced to `none` so the orchestrator takes the alternate strategy instead of redispatching the same step.
- `unrecoverable`: no recoverable classifier matched, `STALL_TRACKING` is not true, or the bail reason is terminal (`adopted-issue-closed`, `tracking-init-failed`).

## Retry Caps

This table is the single normative retry-cap source. `skills/implement/references/stall-recovery.md` points here and does not duplicate values.

| failure_class | attempts | delay |
|---|---:|---|
| transient-infra | 4 | `sleep-seconds.sh 5` between attempts |
| test-failure | 8 | none |
| lint-failure | 8 | none |
| dispatch-failure | 3 | none |
| same-cause-repeat | 1 | alternate strategy: reread `larch:plan`, restart failed step from scratch |
| contract-failure | 0 | none |
| unrecoverable | 0 | none |

## Exit Codes

| exit | meaning |
|---:|---|
| 0 | success |
| 1 | argv error, validation rejection, or lint parity failure |
| 2 | missing required input |
| 3 | malformed/unparseable present `ship-pr-state.sh` only |

Missing `ship-pr-state.sh` is never exit 3. Without other recoverable evidence it is classified as a bounded `unrecoverable` outcome; `session-env.sh` plus a recoverable bail/detail signal can still produce a recoverable class.

## `--failure-detail-log` Validation

The optional failure-detail log must be absolute, canonical after physical directory resolution, regular, non-symlink, inside `--implement-tmpdir`, and no larger than 64 KiB. Invalid logs are ignored and classification continues from the remaining persisted evidence. The offline harness covers the oversize rejection path in addition to relative/outside/symlink/non-regular validation.

## Dry Run

`LARCH_STALL_RECOVERY_DRY_RUN=1` makes `bug-body`, `bug-comment`, and `issue-input-file` emit `DRY_RUN_DECISION=true`. `bug-body` also writes `$IMPLEMENT_TMPDIR/stall-recovery-bug-body.dry-run.md`. The caller must skip `/larch:issue` and `gh issue comment` when this value is true, and the harness covers all three helper surfaces.

## Security

All public surfaces are composed from the allowlists above using classifier enums, hashes, integers, and fixed prose templates. Raw stdout, stderr, failure-detail logs, local paths, branch names, issue bodies, and plan text are excluded. Every body/comment surface is still piped through `scripts/redact-secrets.sh` as a secrets-family backstop. See `SECURITY.md` "Stall recovery sanitization".
