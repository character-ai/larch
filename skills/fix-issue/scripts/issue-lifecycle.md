# skills/fix-issue/scripts/issue-lifecycle.md — contract

`skills/fix-issue/scripts/issue-lifecycle.sh` is the subcommand-based GitHub-issue lifecycle script. Three subcommands: `comment`, `close`, `update-body`. Callers:

- **`comment --lock`** — invoked by `skills/fix-issue/scripts/find-lock-issue.sh` at `/fix-issue` Step 0 (combined Lock + Rename) for both ordinary issue locks and umbrella child-dispatch locks.
- **`close`** — invoked by `/fix-issue` Step 3 (close for not-material issues) and Step 6b (NON_PR close for DONE).
- **`update-body`** — called internally by `cmd_close` when `--pr-url` is provided.

## Subcommands

- **`comment --issue N --body TEXT [--lock]`** — post a comment.
  - With `--lock`: lock without requiring any specific prior comment. Refuses if the tail is exactly `IN PROGRESS` (already locked). **Snapshots the duplicate-detection anchor BEFORE posting**: prefers the last comment's `created_at`; falls back to the issue's own `createdAt` when the issue has zero comments (FINDING_4 — a no-comment-safe anchor for fresh `/umbrella` batch-created children that have never been commented on). Posts `IN PROGRESS`, then re-fetches the comment list to capture the runner's own just-posted comment id, then post-checks for OTHER `IN PROGRESS` comments at `created_at >= snapshot_ts AND id != just_posted_id` (the inclusive `>=` is correct because the snapshot anchor itself remains in the comment stream; the runner's own post is excluded by id so `>= snapshot_ts` can never count it). `>0` means another runner won the race.

  Stdout: `LOCK_ACQUIRED=true` (on success with `--lock`) + `COMMENTED=true`, or `LOCK_ACQUIRED=false` + `ERROR=` on failure.
- **`close --issue N [--comment TEXT] [--pr-url URL] [--close-class false-positive|duplicate|superseded|done] [--mark-false-positive-if-keyword]`** — close an issue with optional DONE comment, optional PR-link body backfill, and optional false-positive title marking. The script resolves the repo internally via `scripts/resolve-repo.sh`, passes `--repo` to all `gh issue` calls, and forwards that resolved value to `tracking-issue-write.sh mark-false-positive`; no caller-supplied `--repo` flag is accepted. **Idempotent**: if the issue is already CLOSED (e.g., GitHub auto-closed it via `Closes #<N>` on PR merge), the `gh issue close` call is skipped but the DONE comment and `--pr-url` body backfill still run; a stderr note (`INFO: issue #N already closed; backfilling DONE metadata only`) is emitted and `CLOSED=true` is printed — **the stdout contract is identical across the open and already-closed paths**, so parsers reading only stdout cannot distinguish them (stderr is a side channel used for diagnostic signals). The false-positive marker hook runs whenever the command reaches the `CLOSED=true` print and the enum/keyword conditions match, including the already-closed branch.

  **`--close-class` enum (structured close-reason — preferred path)**: deterministically drives the `[FALSE-POSITIVE]` marker decision at the call site, set by the orchestrator at triage decision time. Accepts exactly one of `false-positive`, `duplicate`, `superseded`, `done`; any other value exits 2 with a usage error before the close runs. After `CLOSED=true` is emitted, values `false-positive`, `duplicate`, and `superseded` invoke `tracking-issue-write.sh mark-false-positive`; `done` skips the marker entirely. The closing comment is **never** scanned under this path — the enum is the sole signal, so an empty `--comment` is permitted with `--close-class`.

  **`--mark-false-positive-if-keyword` (legacy fallback)**: retained for unstructured-prose closes. After `CLOSED=true`, sources `scripts/false-positive-keywords.sh` and scans the closing comment for configured keywords; on match, invokes `tracking-issue-write.sh mark-false-positive`. Requires `--comment` to be non-empty; otherwise it is a no-op.

  **Precedence**: when both `--close-class` and `--mark-false-positive-if-keyword` are passed on the same call, `--close-class` wins silently — the keyword scan is not executed and no warning is emitted. This is the documented hand-off path for callers migrating from the legacy flag to the enum.

  **Marker trigger order**: `close` posts the optional comment, runs optional body update, probes/closes (or skips close if already closed), emits `CLOSED=true`, then runs the marker decision in this order:
  1. If `--close-class` is set: deterministic dispatch on the value (no comment scan).
  2. Else if `--mark-false-positive-if-keyword` is set AND `--comment` is non-empty: keyword scan (legacy fallback).
  3. Else: no marker.

  Both modes use the same shared `_run_false_positive_marker` helper. Marker failure never changes stdout or exit status after a successful close; it emits `WARNING: mark-false-positive failed for issue #N: <redacted-error>` on stderr. Raw marker stderr is buffered through `scripts/redact-secrets.sh`. Three buffer outcomes:
  1. **Redactor exit 0 + non-empty buffer** → the redacted bytes are emitted to stderr verbatim.
  2. **Redactor exit 0 + empty buffer** (input was entirely sensitive content the scrubber consumed) → the helper emits `INFO: mark-false-positive stderr fully redacted (<bytes> bytes consumed, no surviving output)` so operators see a clean-redaction signal rather than a misleading failure shape.
  3. **Redactor unavailable, non-executable, or exits non-zero** → captured stderr is discarded entirely and the helper emits `WARNING: mark-false-positive stderr suppressed: redactor exit=<code> (<bytes> bytes discarded)`.

  This buffer-then-cat invariant prevents partial redactor output from leaking. Tests may set `LARCH_TEST_REDACTOR_PATH` to exercise redactor failure and missing-redactor branches, and `LARCH_TEST_TRACKING_WRITE_PATH` to replace the marker helper; production callers leave both unset. Umbrella finalization and existing callers that omit both flags keep the byte-stable `CLOSED=true` behavior with no marker invocation.

  **Wiring**: `/fix-issue` Step 3 (not-material close) passes `--close-class <inferred>` derived from the triage decision (already-fixed → `done`, duplicate-of → `duplicate`, superseded-by → `superseded`, invalid/false-positive → `false-positive`). `/fix-issue` Step 6b NON_PR closes pass `--close-class done` so the marker is never applied to legitimate completion summaries. The PR path (Step 6a) does not call `close` — the issue is auto-closed by GitHub via `Closes #N` on PR merge. Legacy `--mark-false-positive-if-keyword` callers are not removed; the flag continues to work for any external caller that has not migrated to the enum.

  **Probe-failure fallback**: if the state probe (`gh issue view --json state`) fails transiently, `close` logs a `WARNING: failed to probe state for issue #N; attempting close anyway` to stderr and falls through to `gh issue close`. This preserves the pre-idempotency OPEN-path reliability — a read-side blip must not abort a close that the write-side would otherwise succeed on. A fatal error is reported only if the subsequent `gh issue close` ALSO fails (`CLOSED=false` + `ERROR=Failed to close issue #N`, exit 1).

  **Partial-success semantics**: the `--comment` (DONE) post and the `--pr-url` body backfill run BEFORE the state probe. On probe-AND-close failure (Fixture 6 in the harness), the comment and body edits may have already been applied to the issue — the caller sees `CLOSED=false` but GitHub state shows a backfilled issue body and a DONE comment on a still-open issue. This is the same partial-success class that existed pre-idempotency (comment + body could already succeed before a fatal `gh issue close`); the idempotency change does not introduce a new partial-success mode.
- **`update-body --issue N --pr-url URL`** — append a PR link to the issue body. Idempotent via substring check. Stdout: `UPDATED=true` (+ optional `SKIPPED=already_present`) on success, `UPDATED=false` + `ERROR=` on failure. Note: `cmd_close` suppresses this subcommand's stdout when it calls it internally so only `CLOSED=true` (or `CLOSED=false` + `ERROR=`) ever appears on `close`'s stdout.

## Lock-settle pause (`ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS`)

After posting the lock comment, `cmd_comment` pauses for `ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS` (default `1`) before re-fetching the comment list to detect a duplicate-runner race. The pause gives GitHub time to make the new comment visible via the API. Test harnesses that PATH-stub `gh` (e.g. `skills/fix-issue/scripts/test-find-lock-issue.sh`) export `ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS=0` because the stub returns synthetic state instantly. The validator accepts non-negative integer or decimal seconds; non-numeric or empty values exit 2 with `ERROR=ISSUE_LIFECYCLE_LOCK_SETTLE_SECONDS must be a non-negative number`.

## Stdout contract

- `close` success: `CLOSED=true` (single line on stdout; any INFO or false-positive marker WARNING note goes to stderr).
- `close` failure: `CLOSED=false` + `ERROR=<reason>` (two lines on stdout; exit code 1).
- `comment` success: `COMMENTED=true` (plus `LOCK_ACQUIRED=true` with `--lock`).

- `update-body` success: `UPDATED=true` (plus `SKIPPED=already_present` when the PR URL is already in the body).

`/fix-issue` Step 6b (and Step 3 on the not-material path) reads stdout loosely (substring match), so additional `INFO:` lines on stderr do not affect callers. The stdout contract is byte-stable across the OPEN and CLOSED idempotency branches.

## Exit codes

- `0` — success.
- `1` — lock verification failed, state read failed, gh call failed, or API error.
- `2` — usage error.

## Test harness

`skills/fix-issue/scripts/test-issue-lifecycle.sh` is the offline regression harness for the `close` idempotency behavior, the structured `--close-class` enum, and the optional legacy false-positive marker flag. It uses a PATH-prepended stub `gh` under `$TMPDIR` to cover: OPEN (no --pr-url), CLOSED (no --pr-url), CLOSED with --pr-url, OPEN with --pr-url (parity), probe-failure with close succeeding (fallback exercised), probe-failure with close also failing (fatal), unsupported `close --repo` rejected with exit 2 before any `gh` side effects, legacy keyword-flag match/no-match/default-off, close-failure no-marker, idempotent marker re-run, already-closed marker invocation, marker-failure WARNING redaction, marker-stderr suppression on redactor failure and missing redactor, non-repo cwd path resolution, and the `--close-class` enum (each value's marker behavior including `done` skip, precedence over the keyword flag, and invalid-value rejection). The harness is self-contained (no network, no repo state changes) and is wired into `make lint` via the `test-issue-lifecycle` target under `test-harnesses`. CI runs `make test-harnesses` directly. `agent-lint.toml` excludes the harness path because agent-lint's dead-script rule does not follow Makefile-only references; the skill-local `.md` exclusion block covers this file.

## Edit-in-sync rules

Changes to `cmd_close`'s stdout contract (including the `CLOSED=true` key, the `CLOSED=false` + `ERROR=` pattern, the `INFO:` stderr note, or the false-positive marker `WARNING:` stderr note) MUST update this file in the same PR and MUST add / update a corresponding fixture in `test-issue-lifecycle.sh`. Changes to the `--close-class` enum (accepted values, marker-action mapping, precedence over `--mark-false-positive-if-keyword`) MUST update both this file and the harness in the same PR. Changes to `cmd_update_body`'s stdout keys (`UPDATED=`, `SKIPPED=`) are caller-visible only when the subcommand is invoked directly (not via `cmd_close`, which suppresses this output). Changes to false-positive keyword semantics (legacy keyword path) must update `scripts/false-positive-keywords.md` and `scripts/test-false-positive-keywords.sh`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
