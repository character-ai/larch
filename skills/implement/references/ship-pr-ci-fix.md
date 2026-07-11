# Ship PR autonomous CI-fix

**Consumer**: `/implement` Step 8 `NEXT_ACTION=ci-fix` after the pre-fix rebase gate.

**Contract**: delegate each default-path fixer tier through the identity-bound wrapper and keep the main agent as the sole bgjob wait owner.

**When to load**: after the pre-fix rebase succeeds and before any CI-fix action.

**MANDATORY: READ ENTIRE FILE before executing this route.** Complete the procedure through the required re-invoke `step-8-ship.sh` handoff.

Preserve the existing fork, repository-unavailable, ledger, operator-bail, and pre-fix rebase gates. Complete the pre-fix rebase before loading this child reference.

## Default delegated waterfall

Treat `NEEDS_USER_REASON=architectural-invariants-violation` as the first executable branch. It does not require a failed GitHub Actions run. The wrapper uses validated `LARCH_RUN_ID` from `session-env.sh`, allocates the launch identity, materializes canonical invariant evidence, then launches an invariant-only fixer lane.

For ordinary CI recovery, `.ship-route-exit-handoff.env` must include `CI_FAILURE_SCOPE`. Scope `pr` selects `FAILED_RUN_ID` from that handoff. Scope `main` selects `MAIN_FAILED_RUN_ID` from `main-health.env`. Missing, malformed, unknown, or conflicting IDs fail closed.

Run one tier with this protocol:

1. Run `bash "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ci-fixer.sh" --start`.
2. Require `BGJOB_STATUS=STARTED`. Capture the emitted dynamic `STEP` exactly. Never derive, hardcode, or reuse it.
3. Run only `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob wait --step "$STEP" --max-wait-s 270` while that tier is active.
4. On `BGJOB_STATUS=WAIT`, repeat that byte-identical wait command. Run no prose, reads, sleeps, wrapper calls, or alternate polling between waits.
5. On `BGJOB_STATUS=DONE`, require `BGJOB_RC=0`. Then run `bash "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ci-fixer.sh" --finalize --step "$STEP"`.

Start and finalize never wait. The Step 8 prompt is the sole wait owner. Only finalize may validate the launch envelope, bgjob merge envelope, `fixer-status.env`, final `HEAD`, and waterfall lineage, then emit compact routing KVs.

Route `RESULT=reship` through the existing Step 8 ship bgjob. Route `RESULT=retry-next-tool` through a fresh start, wait, and finalize cycle. Capture its new dynamic `STEP`; the wrapper retains stable lineage while binding the new launch to the current `HEAD` and diff fingerprint. Route exhausted lineage to `ci-fix-exhausted`. Route `RESULT=operator-bail` through the existing operator-bail gate.

Do not rerun architectural-guidelines Phase A and do not call guideline invalidate or pin helpers. The main agent must not read default-path CI evidence, invariant evidence, merge envelopes, `fixer-status.env`, lane transcripts, or failure digests. It must not run `gh run-logs`, `ci distill-log`, Agent-tool fixer rounds, or edit repository files on this path.

## Kill switch

`LARCH_CI_FIXER=0` is the sole inline exception. Preserve the existing `main-agent-ci-fix.count` budget of attempts 1 through 30, explicit staging, relevant checks, fixer commit, run-log refresh, push through `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch`, and re-invoke `step-8-ship.sh`.

Ordinary inline recovery may use the existing redacted CI-log flow. Invariant-primary inline recovery uses a separate invariant-inline counter and the sanctioned `ci materialize-invariant-evidence` helper with an inline identity (`MODE=inline`, `TIER=inline`, and a per-attempt `STEP`). It consumes only validated canonical invariant evidence. It never requires `FAILED_RUN_ID`, runs `gh run-logs`, or runs `ci distill-log`.
