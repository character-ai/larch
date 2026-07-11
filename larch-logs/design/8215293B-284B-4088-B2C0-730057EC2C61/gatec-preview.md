## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Add a thin Bash 3.2-compatible bgjob envelope around Piece 2’s `python3 python/cli.py architectural-assessment run`.

The adapter is a **blocking foreground launcher**: one invocation owns identity checks, `bgjob start`, live rejoin, repeated `bgjob wait`, terminal-result validation, and the single allowed retry. Unlike `step-8-ship.sh`, it does not return after `BGJOB_STATUS=STARTED` or after a zero-duration live-rejoin probe and leave completion, validation, or retry observation to the caller. Piece 4 may invoke it as one Bash fence.

The adapter will:

1. Read requested assessment kinds from `$IMPLEMENT_TMPDIR/.ship-route-exit-handoff.env`, following the existing `DETAIL` and `DETAIL_FILE` handoff grammar.
2. Normalize, deduplicate, and order the kind set with Piece 2’s `normalize_kinds` contract. Reject empty, duplicate, or unsupported tokens.
3. Rehydrate `${CLAUDE_PLUGIN_ROOT}` using the established `$IMPLEMENT_TMPDIR/plugin-root.env` fallback, then export:
   ```bash
   PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"
   export PYTHONPATH
   ```
   before any inline Python helper or `python/cli.py` invocation that imports larch Python modules.
4. Validate each requested kind’s current materialization through Piece 2’s `validate_materialization`.
5. Build a launch-time **covered fingerprint** with one shared bounded Python helper used for prelaunch identity, merge-result seeding, live/completed rejoin checks, and post-child result coverage validation.
6. Rejoin a live or completed `implement-step8-assessment` job only when both the normalized kind set and covered fingerprint match.
7. For an identity-matching live registry row, use `bgjob wait --max-wait-s 0` only as the immediate rejoin probe. If it reports `WAIT`, continue the adapter-owned documented wait loop, repeating the identical wait command until `DONE` or terminal dead-state evidence. Validate the terminal envelope and route retryable terminal failure through the same attempt-2 path used after a fresh attempt-1 launch.
8. Refuse a fresh launch only when a registry row for `implement-step8-assessment` is live and its recorded launch identity **differs** from current inputs. Emit a distinct `ASSESSMENT_ERROR=active-stale-identity-mismatch` result and exit 2. Do not delete, overwrite, or start replacement work while that child or daemon remains live.
9. Clear stale merge-result, result, and launch-identity state only for dead or identity-mismatched completed work before starting fresh work.
10. Pin `--budget-s 2100` on every `bgjob start`. Piece 2’s assessment child timeout is 1800 seconds; 2100 seconds leaves 300 seconds for daemon startup, merge-result publication, and `bgjob wait` finalization.
11. Start the adapter itself as the bgjob child, not Piece 2’s CLI directly. The start command follows the Step 8 bgjob shape and runs:
    ```bash
    -- bash "$SCRIPT_DIR/step-8-assessment.sh" \
      --bgjob-child \
      --merge-result-env "$MERGE_RESULT_ENV"
    ```
    Child mode alone invokes `architectural-assessment run`, validates its stdout, and translates it into canonical `ASSESSMENT_*` merge-result KVs.
12. Delegate all assessment work to `architectural-assessment run`. Do not reproduce materialization, pre-filter, authoring, persistence, or HEAD-drift logic.
13. Run an adapter-owned attempt loop in foreground mode:
    - Attempt 1: seed launch identity into merge-result, start the wrapper child, print `BGJOB_STATUS=STARTED` exactly once for this foreground invocation, then run the blocking wait loop until a terminal envelope is available.
    - A rejoined identity-matching live attempt 1 enters that same wait-and-validate path. It is not treated as complete merely because the zero-duration probe returned `WAIT`.
    - On retryable terminal failure with unchanged launch identity, clear only dead/stale attempt-1 state and run attempt 2 in the same invocation.
    - If inputs change between attempts, abandon the old retry budget, clear only dead old-identity state, recompute identity, and treat the new identity as a fresh attempt 1.
    - Attempt 2: preseed `ASSESSMENT_STATUS=fail-closed` before `bgjob start`; replace it with `complete` only after successful child validation.
    - A completed terminal `fail-closed` attempt 2 is rejoinable but is never retried. Never start attempt 3.
14. Publish canonical result KVs through the bgjob result-env contract.

**Do not** recompute or compare post-child materialization fingerprints against launch-time fingerprints. Piece 2 may refresh materialization during a valid run. Child success is validated only from stdout and per-kind result coverage; the published `ASSESSMENT_COVERED_FINGERPRINT` remains the launch-time digest.

### Normative identity and result contract

Implement one shared bounded Python helper, invoked from the Bash adapter and mirrored exactly in harness stubs. The adapter establishes the plugin Python import path before invoking this helper.

**`ASSESSMENT_REQUESTED_KINDS`**
- Comma-separated normalized kinds in Piece 2 order.
- Example: `invariants,guidelines`
- No spaces.

**`ASSESSMENT_COVERED_FINGERPRINT`**
- Lowercase 64-character SHA-256 hex digest of this UTF-8 preimage:
  - One line per normalized kind, in order.
  - Line format: `kind|HEAD_SHA|BASE_REF|DIFF_FINGERPRINT`
  - Field separator inside the line: ASCII `|`
  - Line separator: ASCII `\n`
  - No trailing newline after the final kind line.
- Each per-kind field comes from Piece 2 `validate_materialization` at launch time.
- Reject missing, malformed, symlinked, out-of-root, or non-regular materialization inputs before hashing.

**`ASSESSMENT_STATUS`**
- `complete`: child validation succeeded.
- `fail-closed`: terminal failure after retry exhaustion or non-retryable validation failure on attempt 2.

**`ASSESSMENT_ATTEMPT`**
- `1` or `2`.

**`ASSESSMENT_RESULTS`**
- Exact copy of successful Piece 2 `ARCHITECTURAL_ASSESSMENT_RESULTS`.
- Grammar: comma-separated `kind:state` tokens in normalized kind order.
- Allowed `state` values are exactly those Piece 2 may emit today, including `deterministic-clean`, `handled`, `clean`, `deviation`, `violation`, `log-pending`, and `unavailable`.

**Required adapter/bgjob KVs**
- `STEP=implement-step8-assessment`
- `BGJOB_RC`
- `ASSESSMENT_REQUESTED_KINDS`
- `ASSESSMENT_COVERED_FINGERPRINT`
- `ASSESSMENT_STATUS`
- `ASSESSMENT_ATTEMPT`
- `ASSESSMENT_RESULTS` on `ASSESSMENT_STATUS=complete`

Daemon-reserved keys (`BGJOB_PID`, `BGJOB_OWNER_PID`, and any other keys owned by `python/cli.py bgjob`) must not be written through the merge-result envelope.

**Completed rejoin**
- Identity-matched completed envelopes are rejoinable through `bgjob wait --max-wait-s 0` when:
  - `STEP=implement-step8-assessment`
  - requested kinds and covered fingerprint match current inputs
  - all required adapter KVs exist
  - `ASSESSMENT_STATUS` is `complete` or terminal `fail-closed`
- `BGJOB_RC=0` is required only for `ASSESSMENT_STATUS=complete`.
- Terminal `ASSESSMENT_STATUS=fail-closed` envelopes remain rejoinable when `BGJOB_RC` is non-zero, including `timeout`, so resumed runs do not launch attempt 3.
- A completed envelope that identity-matches but fails required-KV or result-coverage validation is not accepted as successful completion. If it represents attempt 1, route it through the one retry; if it represents attempt 2, publish or preserve terminal `fail-closed`.

**Child exit contract**
- Child mode exits 0 only after:
  - `ARCHITECTURAL_ASSESSMENT_STATUS=ok`
  - `ARCHITECTURAL_ASSESSMENT_RESULTS` contains each requested kind exactly once and no extra kinds
  - merge-result KVs are atomically written
- Child mode exits non-zero on usage error, failed Piece 2 status, malformed or missing stdout KVs, duplicate/extra/missing kinds, newline-bearing KV values, unsafe paths, or merge-write failure.
- Do not treat merge-result persistence as success when the child exits non-zero.

## Files to modify/create

### NEW: skills/implement/scripts/step-8-assessment.sh

Create the foreground adapter and bgjob child entry point.

- Start with `set -euo pipefail` and keep all syntax compatible with macOS Bash 3.2.
- Resolve `${CLAUDE_PLUGIN_ROOT}` from the installed plugin root, with the established `$IMPLEMENT_TMPDIR/plugin-root.env` rehydration fallback.
- Immediately export `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"` after plugin-root rehydration and before inline Python or any larch CLI invocation.
- Require `$IMPLEMENT_TMPDIR` and resolve the repository root from persisted run state rather than ambient cwd.
- Use the fixed step slug `implement-step8-assessment`.
- Parse only the documented child and foreground arguments. Reject unknown or incomplete arguments with exit 2.
- Read the `NEXT_ACTION=assessments` handoff safely. Resolve `DETAIL_FILE` only when it is a regular, non-symlink file contained under `$IMPLEMENT_TMPDIR`.
- Normalize requested kinds by importing Piece 2’s `normalize_kinds`, not a second Bash table.
- Compute `ASSESSMENT_COVERED_FINGERPRINT` through one shared bounded Python helper that:
  - imports Piece 2 `normalize_kinds` and `validate_materialization` through the established plugin Python path;
  - builds the normative preimage defined above;
  - returns lowercase SHA-256 hex;
  - rejects missing, malformed, stale, symlinked, or out-of-root materialization files.
- Protect `$IMPLEMENT_TMPDIR/bgjob`, the canonical result env, merge-result envelope, and launch-identity sidecar against symlinks and non-regular files.
- Store launch identity (`ASSESSMENT_REQUESTED_KINDS`, `ASSESSMENT_COVERED_FINGERPRINT`, `ASSESSMENT_ATTEMPT`) in the merge-result envelope before `bgjob start`.
- Inspect the bgjob registry with the established registry and process-liveness helpers.
- Rejoin an identity-matching live registry row by:
  1. calling `bgjob wait --max-wait-s 0` as the immediate rejoin probe;
  2. when the probe reports `WAIT`, entering the same documented repeated wait-until-terminal loop used by a fresh launch;
  3. validating the terminal envelope; and
  4. applying the shared retry-or-terminal logic based on the recorded attempt and current identity.
- Rejoin a completed result only when identity, required KVs, and completion grammar match; allow non-zero `BGJOB_RC` for terminal `ASSESSMENT_STATUS=fail-closed`.
- On an identity-**mismatched** live registry row with a live child or daemon, exit 2 with `ASSESSMENT_ERROR=active-stale-identity-mismatch`. Do not unlink the row, overwrite result state, or start fresh work.
- On an identity-mismatched dead row or stale completed envelope, clear stale result and merge state safely, then continue.
- Recreate the merge-result envelope atomically with mode `0600`.
- Launch the adapter child through `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start` with:
  - `--step implement-step8-assessment`
  - `--tmpdir "$IMPLEMENT_TMPDIR"`
  - `--budget-s 2100`
  - owner PID
  - merge-result path
  - `-- bash "$SCRIPT_DIR/step-8-assessment.sh" --bgjob-child --merge-result-env "$MERGE_RESULT_ENV"`
- Do not launch `architectural-assessment run` as the direct bgjob command; it must execute only inside `--bgjob-child` mode.
- Foreground mode owns this loop in one invocation:
  1. Compute current launch identity.
  2. Rejoin identity-matching completed work if present.
  3. For identity-matching live work, run the zero-duration rejoin probe, then continue the blocking wait loop if the job is still running.
  4. Otherwise run attempt 1: clear stale state, seed merge-result, start the wrapper child, print `BGJOB_STATUS=STARTED` once, wait until terminal state, and validate.
  5. On retryable terminal failure with unchanged identity, clear only dead/stale attempt-1 artifacts and run attempt 2 in the same invocation without printing a second `STARTED`.
  6. If identity changed before attempt 2, abandon the old attempt and restart at attempt 1 for the new identity.
  7. Emit the validated terminal `bgjob wait` envelope as foreground stdout. Never start attempt 3.
- In child mode:
  - Invoke `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" architectural-assessment run` once with one `--kind` per normalized kind, plus persisted repo root and implement tmpdir.
  - Capture and validate exact `KEY=value` stdout.
  - Require `ARCHITECTURAL_ASSESSMENT_STATUS=ok`.
  - Require `ARCHITECTURAL_ASSESSMENT_RESULTS` coverage for each requested kind exactly once.
  - Do not compare post-run materialization fingerprints to launch-time fingerprints.
  - Atomically write adapter KVs plus copied `ASSESSMENT_RESULTS` into merge-result without daemon-reserved keys.
  - Exit 0 only on full validation success; otherwise exit non-zero.
- Retryable failures for attempt 1:
  - `BGJOB_RC=timeout`
  - any other non-zero `BGJOB_RC`
  - missing or malformed merge/result KVs
  - `ASSESSMENT_STATUS` not `complete`
  - kind coverage mismatch in `ASSESSMENT_RESULTS`
- Attempt 2 preseeds `ASSESSMENT_STATUS=fail-closed`; preserve timeout or non-zero `BGJOB_RC` if validation still fails.
- Keep diagnostics on stderr.
- Reject newline or carriage-return values before writing any `KEY=value` field.

### NEW: skills/implement/scripts/step-8-assessment.md

Document the adapter contract.

- State that the script is a thin bgjob wrapper over Piece 2’s `architectural-assessment run`.
- State that foreground mode blocks through start or live rejoin, repeated wait, validation, and the single retry in one invocation.
- Define caller-owned prerequisites:
  - `$IMPLEMENT_TMPDIR`
  - persisted repository root
  - `.ship-route-exit-handoff.env` with `NEXT_ACTION=assessments`
  - valid current materialization metadata for every requested kind
  - an established plugin Python import path: after plugin-root rehydration, the adapter exports `$CLAUDE_PLUGIN_ROOT/python` ahead of any existing `PYTHONPATH`.
- Define the fixed step slug, `--budget-s 2100`, and explicit rationale: Piece 2 child timeout is 1800 seconds; adapter budget adds 300 seconds for daemon and merge/finalize overhead.
- Document that `bgjob start` launches `step-8-assessment.sh --bgjob-child`, while child mode alone invokes Piece 2’s CLI, validates its output, and writes canonical merge-result KVs.
- Document the normative fingerprint section:
  - exact KV names
  - ordered per-kind tuple fields
  - canonical serialization
  - SHA-256 digest format
- List required result KVs and allowed completion states.
- Document live and completed rejoin rules:
  - matching live work receives a zero-duration probe followed by the adapter’s blocking wait loop and shared validation/retry handling;
  - matching completed `complete` results require `BGJOB_RC=0`;
  - matching terminal `fail-closed` results may retain non-zero `BGJOB_RC` and do not receive attempt 3.
- Document `ASSESSMENT_ERROR=active-stale-identity-mismatch` only for an identity-mismatched live row that cannot be replaced safely.
- Distinguish input drift (new attempt 1 for new identity) from retryable execution failure (attempt 2 for the same identity).
- Document the one-retry limit, fail-closed terminal result, and the rule that attempt 3 is forbidden.
- Document child non-zero exit semantics and that exit 0 is reserved for fully validated success.
- State that Piece 2 owns deterministic skip, authored assessment, persistence, and HEAD-drift handling.
- State that the adapter never performs foreground or main-agent authoring.
- State that launch-time fingerprint is published as identity, not revalidated against post-run materialization files.
- Record symlink, containment, regular-file, atomic-write, Python-import-path, and Bash 3.2 requirements.
- Mark `skills/implement/SKILL.md` and Step 8 route activation as out of scope for this piece.
- Add an edit-in-sync note naming the script and its harness files.

### NEW: skills/implement/scripts/test-step-8-assessment.sh

Create an offline shell harness with a fake plugin root and stubbed `python/cli.py`.

Cover these scenarios:

- **Fresh start**:
  - Normalize requested kind order.
  - Compute and persist the normative covered fingerprint.
  - Establish the plugin Python import path required by the inline helper.
  - Clear stale merge-result state.
  - Start exactly one `implement-step8-assessment` bgjob with `--budget-s 2100` and the expected wrapper-child argv:
    bash "$SCRIPT_DIR/step-8-assessment.sh" \
  - Assert that `architectural-assessment run` is invoked only from the child-mode stub, not as the direct `bgjob start` command.
- **Static budget pin**:
  - Assert the helper text contains `--budget-s 2100`, matching the `test-step-8-ship.sh` static-pin pattern.
- **Live rejoin**:
  - Rejoin an identity-matching live registry row.
  - Assert the adapter calls `bgjob wait --max-wait-s 0` as the initial probe.
  - Assert a `WAIT` probe enters the repeated blocking wait path until `DONE`.
  - Assert terminal validation and a retryable attempt-1 failure route through the in-invocation attempt-2 path.
  - Do not start a duplicate child before the rejoined attempt becomes terminal.
- **Completed rejoin**:
  - Rejoin an identity-matching `ASSESSMENT_STATUS=complete` result with `BGJOB_RC=0`.
  - Rejoin an identity-matching terminal `ASSESSMENT_STATUS=fail-closed` result with non-zero `BGJOB_RC`, including `timeout`.
  - Require every canonical result KV.
  - Do not start attempt 3.
- **Deterministic skip**:
  - Accept Piece 2 output such as `guidelines:deterministic-clean`.
  - Publish it without launching an external author from the adapter.
- **Authored success**:
  - Accept valid `clean`, `deviation`, `violation`, `handled`, `log-pending`, or `unavailable` per-kind results under Piece 2’s success contract.
  - Preserve normalized multi-kind result coverage.
- **Stale rejection**:
  - Reject changed kind sets.
  - Reject changed `HEAD_SHA`, `BASE_REF`, or `DIFF_FINGERPRINT`.
  - Reject stale completed envelopes and dead stale registry rows.
  - Clear stale result and merge state before a fresh launch.
  - Refuse to delete or overwrite symlinks and non-regular files.
- **Active stale live row**:
  - When a live registry row’s launch identity mismatches current inputs, assert exit 2 and `ASSESSMENT_ERROR=active-stale-identity-mismatch`.
  - Do not start a fresh launch or remove the live row.
- **Timeout fallback**:
  - Attempt 1 timeout triggers an in-invocation attempt-2 relaunch.
  - The same behavior applies when an identity-matching rejoined live attempt 1 reaches timeout.
  - Attempt 2 timeout ends with `BGJOB_RC=timeout` and `ASSESSMENT_STATUS=fail-closed`.
  - Do not call Piece 2 inline from the foreground path.
- **Invalid-output fallback**:
  - Retry after missing status, missing results, malformed KVs, duplicate kinds, extra kinds, or coverage mismatch.
  - Fail closed after the second invalid result.
  - Do not fail success because post-run materialization changed.
- **Required KVs**:
  - Assert `STEP`, `BGJOB_RC`, `ASSESSMENT_REQUESTED_KINDS`, `ASSESSMENT_COVERED_FINGERPRINT`, `ASSESSMENT_STATUS`, `ASSESSMENT_ATTEMPT`, and `ASSESSMENT_RESULTS`.
  - Assert daemon-reserved keys cannot be forged through merge-result env.
- **Fingerprint grammar**:
  - Assert the shared helper and harness stubs produce the same digest for the same ordered per-kind tuples.
- **Path safety**:
  - Reject symlinked bgjob directory, result env, merge-result env, detail file, or materialization input.
- **Bash portability**:
  - Avoid associative arrays, namerefs, `mapfile`, uppercase parameter expansion, and Bash 4-only syntax.

Keep the harness deterministic. Stub git identity, materialization validation, registry state, bgjob start, bgjob wait, and child CLI output. Do not launch Claude or mutate the repository.

### NEW: skills/implement/scripts/test-step-8-assessment.md

Document the harness purpose and coverage.

- Explain that it uses fake Piece 2, bgjob, registry, materialization, and plugin-Python-path responses.
- List fresh start, wrapper-child launch shape, static budget pin, live rejoin through probe plus blocking wait, completed rejoin for both `complete` and terminal `fail-closed`, deterministic skip, authored success, stale rejection, active-stale live-row refusal, timeout retry, invalid-output retry, terminal fail-closed behavior, required KVs, fingerprint grammar, and path-safety coverage.
- State that no real assessment model, daemon, or repository mutation occurs.
- Add an edit-in-sync note for the adapter script and contract document.

## Edge cases

- `DETAIL` is empty, contains an unknown token, repeats a token, or contains only separators.
- `DETAIL_FILE` is missing, outside `$IMPLEMENT_TMPDIR`, symlinked, non-regular, or contains malformed data.
- One requested kind has valid materialization while another is missing or stale.
- A job is live and its launch identity matches current inputs; the zero-duration probe returns `WAIT`, so the adapter must continue waiting, validate the terminal result, and apply retry rules.
- A job is live but its launch identity differs from current inputs.
- A mismatched live registry row remains live and blocks fresh launch with `active-stale-identity-mismatch`.
- A registry row is dead while its stale result env remains.
- Piece 2 refreshes materialization during a valid child run; adapter success must not depend on post-run fingerprint equality.
- Piece 2 reports success but omits a requested kind or returns an extra kind.
- A timeout leaves only preseeded merge-result KVs on attempt 2.
- Attempt 1 fails, then inputs change before attempt 2.
- Cleanup encounters a symlink or non-regular path.
- A merge-result value contains a newline or carriage return.
- A terminal fail-closed completed envelope has non-zero `BGJOB_RC` and must still rejoin without attempt 3.

## Failure modes

- Fail with exit 2 on unsafe paths, malformed handoff data, invalid materialization identity, missing plugin Python import setup, registry inspection errors, or `active-stale-identity-mismatch`.
- Treat input mismatch as stale work, not successful completion.
- For identity-matching live work, do not stop at a `WAIT` rejoin probe; wait for a terminal state and apply the normal validation and retry rules.
- Retry one execution failure inside foreground mode’s attempt loop.
- Preserve the daemon’s non-zero or timeout `BGJOB_RC` after retry exhaustion.
- Emit terminal `ASSESSMENT_STATUS=fail-closed` after the second failed attempt.
- Never fall back to inline assessment authoring.
- Never consume a result whose requested kind set or launch-time covered fingerprint differs from current inputs.
- Never start a third attempt after terminal `fail-closed`.

## Testing strategy

Run only checks relevant to the four new files:

1. `bash skills/implement/scripts/test-step-8-assessment.sh`
2. `bash -n skills/implement/scripts/step-8-assessment.sh`
3. `bash -n skills/implement/scripts/test-step-8-assessment.sh`
4. Run ShellCheck on both new shell files through the repository’s changed-file lint path.
5. Run the Bash 3.2 lint against both new shell files.
6. Run the repository Markdown lint against both new contract documents.
7. Re-run `python/tests/implement/test_architectural_assessment.py` only if the adapter exposes an unexpected incompatibility with Piece 2’s existing CLI output. Do not change Piece 2 merely to simplify the Bash wrapper.

## Scope controls

- Do not change `skills/implement/SKILL.md`.
- Do not activate or reroute Step 8. Piece 4 owns route integration.
- Do not change Piece 2’s Python implementation unless direct testing proves its documented CLI contract is insufficient. The current plan does not expect such a change.
- Do not add a second implementation of materialization, deterministic filtering, authoring, persistence, or HEAD-drift handling.
- Do not add main-agent fallback authoring.

Confidence: high
difficulty: MODERATE
diff_added: 760
diff_deleted: 0
mechanical_churn: false
diff_lines: 760
