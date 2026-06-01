# stall-recovery-report.sh

`stall-recovery-report.sh` is the deterministic helper for `/implement` Step 18a stall recovery. It classifies a persisted stall, tracks retry attempts, exposes the normative retry-cap table, detects larch dev clones, and composes sanitized public issue/report surfaces from fixed allowlists.

## Subcommands

- `classify --implement-tmpdir <path> [--in-memory-stall-tracking <true|false>] [--bail-reason <token>] [--failure-detail-log <path>] [--attempts-file <path>]`
  - Resolves `STALL_TRACKING` conservatively across the in-memory flag, `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, and `$IMPLEMENT_TMPDIR/session-env.sh`; missing ship-pr state does not suppress a session-env stall.
  - Precondition: callers that resolved "no stall detected" must skip `classify` entirely and continue to teardown; this helper is only for persisted or confirmed stalls.
  - Truthy values are exactly `1`, `true`, `TRUE`, `True`, `yes`, `YES`, `Yes`, `on`, `ON`, and `On`; every other value is false.
  - Emits `FAILURE_CLASS`, `FAILURE_SIGNATURE`, `RESUME_HINT`, `STALL_STEP`, `PHASE`, `STALL_TRACKING`, `BAIL_REASON`, and `EXIT_CODE`.
  - The emitted `STALL_STEP`, `PHASE`, and `BAIL_REASON` values are sanitized enums/tokens only. `BAIL_REASON` is a closed enum (`adopted-issue-closed`, `tracking-init-failed`) plus empty; every other value is emitted as `redacted`.
  - `FAILURE_CLASS` is one of `transient-infra`, `test-failure`, `lint-failure`, `dispatch-failure`, `contract-failure`, `same-cause-repeat`, or `unrecoverable`.
  - `RESUME_HINT` is one of `step2-impl`, `step5-review`, `step8-shippr`, or `none`. `step3-checks` and `step6-checks` are never resume hints; mapped ship-pr restart tokens are the `8`-through-`15` family except the explicit no-resume terminals `12d` and `bump-branch-guard`.
  - `--attempts-file`, when provided, must be an absolute path that resolves to a regular, non-symlink, readable file under `$IMPLEMENT_TMPDIR`.
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
  - `--classification-file`, `--attempts-file`, and `--output-file` must stay under `--implement-tmpdir`.
- `issue-input-file --implement-tmpdir <path> --classification-file <path> --body-file <path> [--output-file <path>]`
  - Writes a batch-mode `/larch:issue` input file. The first line is `### [Bug] /implement stall: <class> at <step>`.
  - `--classification-file` and `--body-file` must be absolute paths that resolve to regular, non-symlink, readable files under `$IMPLEMENT_TMPDIR`.
  - `--output-file` must stay under `$IMPLEMENT_TMPDIR`.
- `clear-stall --implement-tmpdir <path>`
  - Owns the Step 18a success-path atomic clear of `$IMPLEMENT_TMPDIR/ship-pr-state.sh` (disk before memory). Emits `CLEARED=true|false` on every path.
  - Present-file guards are three-tier: (1) symlink or non-regular file → `CLEARED=false`, exit 3; (2) syntax-invalid lines (`check_ship_pr_state_syntax`) → `CLEARED=false`, exit 3; (3) syntax-valid but keyless (empty or comment-only) → `CLEARED=false`, exit 0 without rewriting disk. Absent file → `CLEARED=false`, exit 0. Never call `validate_ship_pr_state` (it exits 3 without emitting `CLEARED`).
  - On success (syntax-valid file with at least one key): key-rewrite sets `STALL_TRACKING=false` and `STALL_STEP=` (appending both when absent), preserves every other key and line order, temp-write → re-read-assert `false` via `read-session-env-key.sh` → `mv -f` → destination re-read-assert `false`. Operational failures on temp-write, re-read, `mv`, or destination re-read emit `CLEARED=false` before exit (explicit handlers; no bare `set -e` abort without the KV).
  - Never clears in-memory orchestrator state.
- `seed-terminal-state --implement-tmpdir <path> [--stall-step <N>] [--phase <token>]`
  - Owns the Step 18a terminal-failure durable write (steps 8.1–8.3). Emits `SEEDED=true|false` and, on success, `SEED_MODE=rewrite|seed`.
  - When `ship-pr-state.sh` exists: same three-tier present-file guards as `clear-stall` for symlink/non-regular (exit 3) and syntax-invalid (exit 3). Unlike `clear-stall`, a syntax-valid keyless present file is not a no-op: the helper seeds the canonical minimal Step-8 shape (`SEED_MODE=seed`) instead of exiting 3. When the file has keys, rewrite keeps `STALL_TRACKING=true`, refreshes `STALL_STEP` / `PHASE` from sanitized args when provided else keeps existing sanitized disk values, and preserves `BAIL_FAILURE_DETAIL_LOG` and all other keys by construction (key-rewrite updates only the named keys).
  - When absent: seeds the canonical minimal Step-8 shape (`PHASE=ci-initial`, `STALL_TRACKING=true`, `STALL_STEP=8`, `BAIL_REASON=`, `BAIL_FAILURE_DETAIL_LOG=`, `EXIT_CODE=4`) with `--stall-step` / `--phase` overriding defaults when supplied.
  - Re-read-assert `STALL_TRACKING=true` after `mv -f`. Operational failures emit `SEEDED=false` before exit.
- `lint`
  - Asserts allowlist parity: TSV surface keys == helper code surface keys == this document's surface keys.

## Surface Allowlists

`clear-stall` and `seed-terminal-state` compose no public report text. The `## Surface Allowlists` table, TSV, and `lint` parity checks are unchanged — only classification/report subcommands participate in allowlisted surfaces.

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
- `same-cause-repeat`: the current sanitized signature matches the latest durable attempt signature; `RESUME_HINT` is forced to `none` so the orchestrator takes the alternate strategy instead of redispatching the same step. Terminal classes (`contract-failure`, `unrecoverable`) never reclassify to `same-cause-repeat`, including repeated Step 3 / Step 6 checks failures.
- `unrecoverable`: no recoverable classifier matched, `STALL_TRACKING` is not true, or the bail reason is terminal (`adopted-issue-closed`, `tracking-init-failed`).

## Retry Caps

This table is the single normative retry-cap source. `skills/implement/references/stall-recovery.md` points here and does not duplicate values. `stall-recovery-report.sh lint` fails closed if the table drifts from helper output, and the offline harness checks every class against `retry-policy`.

| failure_class | attempts | delay |
|---|---:|---|
| transient-infra | 4 | `sleep-seconds.sh 5` |
| test-failure | 8 | none |
| lint-failure | 8 | none |
| dispatch-failure | 3 | none |
| same-cause-repeat | 2 | none |
| contract-failure | 0 | none |
| unrecoverable | 0 | none |

For `same-cause-repeat`, the absence of a delay is intentional: the orchestrator uses the one-time alternate strategy immediately instead of sleeping before redispatch.
For `transient-infra`, the emitted retry delay means "sleep this command between attempts."

## Exit Codes

| exit | meaning |
|---:|---|
| 0 | success |
| 1 | argv error, validation rejection, or lint parity failure |
| 2 | missing required input |
| 3 | present `ship-pr-state.sh` is symlinked, non-regular, or syntax-invalid only |

Missing `ship-pr-state.sh` is never exit 3. Without other recoverable evidence it is classified as a bounded `unrecoverable` outcome; `session-env.sh` plus a recoverable bail/detail signal can still produce a recoverable class.

## `--failure-detail-log` Validation

The optional failure-detail log must be absolute, canonical after physical directory resolution, regular, non-symlink, inside `--implement-tmpdir`, and no larger than 64 KiB. Step 18a should source the canonical path from `BAIL_FAILURE_DETAIL_LOG` in `ship-pr-state.sh` when that key is populated, then pass it through `--failure-detail-log` after validation; classification validates and reads the file through one helper so the public classifier does not re-open the path after validation. Invalid logs are ignored and classification continues from the remaining persisted evidence. The offline harness covers the oversize rejection path in addition to relative/outside/symlink/non-regular validation.

## Signatures

Failure signatures are always SHA-256 digests. The helper uses `shasum -a 256`, then `sha256sum`, then a Python `hashlib.sha256` fallback so deduplication stays environment-independent.

## Dry Run

`LARCH_STALL_RECOVERY_DRY_RUN=1` makes `bug-body`, `bug-comment`, and `issue-input-file` emit `DRY_RUN_DECISION=true`. `bug-body` also writes `$IMPLEMENT_TMPDIR/stall-recovery-bug-body.dry-run.md`. The caller must skip `/larch:issue` and `gh issue comment` when this value is true, and the harness covers all three helper surfaces.

## Security

All public surfaces are composed from the allowlists above using classifier enums, hashes, integers, and fixed prose templates. Raw stdout, stderr, failure-detail logs, local paths, branch names, issue bodies, and plan text are excluded. Every body/comment surface is still piped through `scripts/redact-secrets.sh` as a secrets-family backstop. See `SECURITY.md` "Stall recovery sanitization".
