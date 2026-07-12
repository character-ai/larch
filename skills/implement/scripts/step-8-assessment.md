# step-8-assessment.sh

Thin Bash 3.2-compatible bgjob adapter around Piece 2’s
`python3 python/cli.py architectural-assessment run`.

Foreground mode is a **blocking** launcher: one invocation owns identity checks,
`bgjob start` or live rejoin, repeated `bgjob wait`, terminal-result validation,
and the single allowed retry. It does not return after `BGJOB_STATUS=STARTED` or
after a zero-duration live-rejoin probe. Piece 4 may invoke it as one Bash fence.

Child mode (`--bgjob-child`) alone invokes Piece 2’s CLI, validates its stdout,
and writes canonical `ASSESSMENT_*` merge-result KVs. `bgjob start` always
launches `step-8-assessment.sh --bgjob-child`, never `architectural-assessment run`
as the direct bgjob command.

## Caller-owned prerequisites

- `$IMPLEMENT_TMPDIR`
- Persisted repository root as `REPO_ROOT` in `$IMPLEMENT_TMPDIR/session-env.sh`
  (non-symlink directory with `.git`)
- `$IMPLEMENT_TMPDIR/.ship-route-exit-handoff.env` with `NEXT_ACTION=assessments`
  and `DETAIL` / optional `DETAIL_FILE` kind list
- Valid current materialization metadata for every requested kind
- Plugin Python import path: after plugin-root rehydration, the adapter exports
  `$CLAUDE_PLUGIN_ROOT/python` ahead of any existing `PYTHONPATH`

## Step slug and budget

- Fixed step slug: `implement-step8-assessment`
- `--budget-s 5700` on every `bgjob start`
- Rationale: Piece 2 can run three sequential 1800-second model lanes; the
  adapter budget adds 300 seconds for shared-launcher sidecars, daemon startup,
  merge-result publication, and `bgjob wait` finalization

## Normative identity and result contract

### `ASSESSMENT_REQUESTED_KINDS`

Comma-separated normalized kinds in Piece 2 order (example:
`invariants,guidelines`). No spaces. Empty, unknown, or duplicate raw handoff
tokens fail closed with exit 2 before `normalize_kinds`.

### `ASSESSMENT_COVERED_FINGERPRINT`

Lowercase 64-character SHA-256 hex digest of this UTF-8 preimage:

- One line per normalized kind, in order
- Line format: `kind|HEAD_SHA|BASE_REF|DIFF_FINGERPRINT`
- Field separator: ASCII `|`
- Line separator: ASCII `\n`
- No trailing newline after the final kind line

Each per-kind field comes from Piece 2 `validate_materialization` at launch
time. Missing, malformed, symlinked, out-of-root, or non-regular materialization
inputs are rejected before hashing.

A single bounded inline Python helper (plugin `PYTHONPATH` established first)
imports Piece 2 `normalize_kinds` and `validate_materialization`, builds the
preimage, and emits the kinds plus fingerprint KVs. Harness stubs mirror that
contract; they do not reimplement Piece 2.

### `ASSESSMENT_STATUS`

- `complete`: child validation succeeded
- `fail-closed`: terminal failure after retry exhaustion or non-retryable
  validation failure on attempt 2

### `ASSESSMENT_ATTEMPT`

`1` or `2`. Attempt 3 is forbidden.

### `ASSESSMENT_RESULTS`

Exact copy of successful Piece 2 `ARCHITECTURAL_ASSESSMENT_RESULTS`:
comma-separated `kind:state` tokens in normalized kind order. Allowed states
include `deterministic-clean`, `handled`, `clean`, `deviation`, `violation`,
`log-pending`, and `unavailable`.

### `ASSESSMENT_CHILD_DETAIL`

Optional diagnostic captured from the terminal assessment child. The adapter
passes child stderr on stdin to
`python3 python/cli.py architectural-assessment sanitize-detail --implement-tmpdir "$IMPLEMENT_TMPDIR"`.
That command emits exactly one redacted, newline-free value, bounded to 500
characters, and no other stdout rows. A sanitizer failure fails closed.

Raw child stderr is never written to a merge-result value or committed
artifact. The adapter removes its mode-0600 raw file on normal completion,
malformed child output, sanitizer or merge-write failure, shell error, and
signal exits.

### Required adapter/bgjob KVs

- `STEP=implement-step8-assessment`
- `BGJOB_RC`
- `ASSESSMENT_REQUESTED_KINDS`
- `ASSESSMENT_COVERED_FINGERPRINT`
- `ASSESSMENT_STATUS`
- `ASSESSMENT_ATTEMPT`
- `ASSESSMENT_RESULTS` when `ASSESSMENT_STATUS=complete`
- Optional `ASSESSMENT_CHILD_DETAIL` when the terminal child emitted stderr

Daemon-reserved keys (`BGJOB_PID`, `BGJOB_OWNER_PID`, `BGJOB_STATUS`,
`BGJOB_RC`, `BGJOB_ELAPSED_S`, `STEP`, and other keys owned by
`python/cli.py bgjob`) must not be written through the merge-result envelope.

## Live and completed rejoin

- Identity-matching **live** work: call `bgjob wait --max-wait-s 0` as the
  immediate probe; on `WAIT`, enter the adapter’s blocking wait loop
  (`--max-wait-s 270` repeated) until a terminal envelope; validate; apply the
  shared retry-or-terminal logic.
- Identity-matching completed `ASSESSMENT_STATUS=complete` requires `BGJOB_RC=0`.
- Identity-matching terminal `ASSESSMENT_STATUS=fail-closed` may retain non-zero
  `BGJOB_RC` (including `timeout`) and must not receive attempt 3.
- `ASSESSMENT_ERROR=active-stale-identity-mismatch` (exit 2) only when a live
  registry row’s launch identity differs from current inputs. Do not unlink,
  overwrite, or start replacement work while that child or daemon remains live.
- Dead or identity-mismatched completed work: clear stale result and merge state
  safely, then continue.

## Attempt loop and input drift

- Attempt 1: seed launch identity into merge-result, start the wrapper child,
  print `BGJOB_STATUS=STARTED` exactly once for this foreground invocation,
  wait until terminal, validate.
- Retryable attempt-1 failure with unchanged identity: clear only dead/stale
  attempt-1 state and run attempt 2 in the same invocation (no second
  `STARTED`).
- Input drift between attempts: abandon the old retry budget, clear only dead
  old-identity state, recompute identity, and treat the new identity as a fresh
  attempt 1.
- Attempt 2: preseed `ASSESSMENT_STATUS=fail-closed` before `bgjob start`;
  replace with `complete` only after successful child validation.
- Terminal `fail-closed` attempt 2 is rejoinable and never retried.

## Child exit contract

Child mode exits 0 only after:

- `ARCHITECTURAL_ASSESSMENT_STATUS=ok`
- `ARCHITECTURAL_ASSESSMENT_RESULTS` contains each requested kind exactly once
  and no extra kinds
- merge-result KVs are atomically written

Child mode exits non-zero on usage error, failed Piece 2 status, malformed or
missing stdout KVs, duplicate/extra/missing kinds, newline-bearing KV values,
unsafe paths, or merge-write failure. Do not treat merge-result persistence as
success when the child exits non-zero.

## Ownership boundaries

- Piece 2 owns session-recorded tool availability, the per-kind
  Cursor→Codex→Claude waterfall, deterministic skip, authored assessment,
  persistence, and HEAD-drift handling. Each model lane receives one attempt.
- Adapter attempt 2 repairs a failed child or daemon envelope; it does not retry
  a model lane or select tools.
- The adapter never performs foreground or main-agent authoring.
- The launch-time fingerprint is published as identity and is **not**
  revalidated against post-run materialization files (Piece 2 may refresh
  materialization during a valid run).
- `skills/implement/SKILL.md` and Step 8 route activation are out of scope for
  this piece (Piece 4).

## Safety and portability

- Symlink, containment, and regular-file checks on `$IMPLEMENT_TMPDIR/bgjob`,
  result env, merge-result env, `DETAIL_FILE`, and materialization inputs
- Atomic merge-result writes with mode `0600`
- Reject newline or carriage-return values before writing any `KEY=value` field
- macOS Bash 3.2 portable (no associative arrays, namerefs, `mapfile`, or
  Bash 4-only parameter expansion)

## Edit-in-sync

Keep this document aligned with:

- `skills/implement/scripts/step-8-assessment.sh`
- `skills/implement/scripts/test-step-8-assessment.sh`
- `skills/implement/scripts/test-step-8-assessment.md`

## Re-author-required terminal

`re-author-required` is an allowed per-kind `ASSESSMENT_RESULTS` state. If any requested kind has that state, the adapter writes `ASSESSMENT_STATUS=re-author-required` with `BGJOB_RC=0` and preserves the request identity and full results. This envelope is terminal and rejoinable, but it is not successful coverage and is not retryable. The parent routes it to `NEXT_ACTION=assessments` and must not invoke `step-8-ship.sh`.
