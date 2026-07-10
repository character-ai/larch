## Goal
Implement issue #6820: [IMPLEMENTING] Dormant CI-fixer lane and bgjob wrapper.

## Implementation Plan
## Plan

## Approach

Implement the approved single-bgjob-layer design, with the child’s typed outcome persisted directly into the bgjob merge-result envelope rather than relying on stdout.

- Add a Python child that validates its complete invocation before collecting evidence, changing directory, launching a fixer, or writing results.
- Run exactly one selected `implement.ci_recovery_fixer` tier per invocation. Call the existing Codex, Cursor, or Claude CI launcher directly with `FIXER_LANE_TIMEOUT_SEC`.
- Wire each completed recoverable outcome into both the durable handoff files and the bgjob daemon’s configured merge-result env. Stdout remains a diagnostic `KEY=value` envelope only; it is not the transport the wrapper consumes.
- Keep evidence collection autonomous inside the child. Resolve missing run IDs once, wait within existing bounds for in-progress runs, retry digest creation within a fixed bound, and use a bounded redacted raw-log fallback only when safe collection cannot produce a digest.
- Accept architectural-invariant evidence only from a canonical, regular, non-symlink path under the expected implement tmpdir and with the expected identity. Pass that validated evidence explicitly through the CI launcher interface rather than relying on launcher-side repository rediscovery.
- Pin in-process launcher execution to the validated repository root: immediately before dispatch, change process cwd to that root through a restoring context manager; reject an unsuccessful or unexpected cwd transition and always restore the caller cwd in `finally`.
- Persist recoverable outcomes through atomic, identity-bound `fixer-status.env`, `fixer-rounds.tsv`, `fixer-bail.md`, and the bgjob merge-result env writes. Treat unsafe paths, identity drift, malformed wire data, merge-envelope write failures, and durable-write failures as closed failures.
- Add a dormant shell wrapper. It selects the next untried available tier, starts or rejoins one fixer bgjob, and delegates waiting only to `python/cli.py bgjob wait`.
- Keep the foreground wrapper free of CI evidence reads and repository mutations.
- Do not wire the wrapper into `skills/implement/SKILL.md`, `step-8-ship.sh`, the ship loop, or `ship-pr-ci-fix.md`.

## Files to modify/create

### NEW: python/larch/implement/ci_fixer_lane.py

Create the one-tier child implementation.

- Define frozen input and result domain types for validated invocation identity, evidence state, launcher outcome, and the public result tokens `reship`, `retry-next-tool`, and `operator-bail`.
- Parse and validate repository root, implement tmpdir, handoff directory, run ID, tier, positive attempt number, starting HEAD, input fingerprint, configured bgjob merge-result env path, and optional evidence paths.
- Require canonical directories and regular files. Reject symlinks, escaping paths, control characters, unsupported tiers, mismatched repository roots, malformed fingerprints, stale starting HEAD values, and an unsafe merge-result target before any side effect.
- Require the configured bgjob merge-result env to be a validated tmpdir-contained handoff sidecar with an identity-derived deterministic name. Reject a caller-controlled arbitrary output file, an existing foreign result, a symlink, or a path whose parent is unsafe.
- Re-read `HEAD` before evidence use, before launching, and before committing a result. Route expected fixer-created HEAD movement through the typed result protocol, but reject unexplained pre-launch drift.
- Resolve a missing CI run ID once through the existing CI status helpers. Record failure to resolve as a typed bail rather than looping.
- Reuse exported `ci_monitor` helpers to classify failed jobs, collect failed logs, handle in-progress runs within the existing timeout, and distinguish transient collection failures.
- Produce or validate `distilled-failure.md` without exposing its contents to the foreground wrapper. Retry digest collection only within an explicit bound.
- When digest collection fails, create a size-bounded, redacted raw-log artifact inside the validated handoff directory. Fail closed if redaction or safe persistence fails.
- Validate optional architectural-invariant evidence against the expected tmpdir-owned path and identity metadata before passing it to the launcher. Do not accept an arbitrary caller path, ignore no identity mismatch, and bind the accepted evidence path and digest to the invocation identity.
- Build tier-specific launcher arguments with the validated repository as the working directory, `role=fix`, the selected output path, the failure-evidence path, the validated optional invariant-evidence path, and `FIXER_LANE_TIMEOUT_SEC`.
- Dispatch only `launch_codex_ci_main`, `launch_cursor_ci_main`, or `launch_claude_ci_main` for the selected tier.
- Immediately before launcher dispatch, enter a narrow cwd-restoring context that:
  - records the inherited cwd;
  - changes cwd to the validated repository root;
  - verifies `Path.cwd()` resolves to that same canonical root;
  - invokes exactly one selected launcher; and
  - restores the inherited cwd even when the launcher, sentinel handling, or result persistence raises.
- Resolve the actual launcher exit from its sentinel and diagnostics rather than trusting the wrapper return code alone.
- Convert launcher success, timeout, unavailable/auth failure, no progress, rebase need, unsafe state, and exhausted evidence paths into the three typed public results.
- For every successfully handled typed result, atomically write matching identity-bound payloads to `fixer-status.env` and the configured bgjob merge-result env, append one identity-bearing `fixer-rounds.tsv` row per dispatched attempt, and write a redacted, untrusted-evidence-framed `fixer-bail.md` for recoverable bail outcomes.
- Make the bgjob merge-result payload the explicit wrapper contract. Include at least result token, run ID, attempt, tier, starting HEAD, input fingerprint, final HEAD, status-file identity, and any bounded routing metadata required by the wrapper. Do not require the wrapper to infer routing from `BGJOB_RC`, stdout, or CI evidence files.
- Verify that the durable status payload and merge-result payload are byte-equivalent for shared identity and result fields before reporting success. Re-verify every integrity-critical write before reporting success.
- Exit `0` only after a valid typed result has been persisted and verified in the merge-result env, including `retry-next-tool` and `operator-bail`. Use distinct nonzero exits for usage and closed failures, where no safe typed merge result can be trusted. This keeps `BGJOB_RC=0` compatible with all valid wrapper-routable results.
- Emit a stable, bounded `KEY=value` stdout diagnostic envelope suitable for logs, but do not treat stdout as bgjob result transport.
- Use shared `larch.io` parsing and atomic-write helpers with explicit duplicate-key, newline, symlink, containment, and overwrite policies.

### UPDATED: python/larch/implement/ci_monitor.py

Expose the existing CI evidence behavior needed by the child without changing the non-pending `run_ci_fix` stub.

- Keep `ClassifiedJobs`, `collect_failed_logs`, and existing classification semantics available as public imports.
- Extract or expose narrow helpers for bounded in-progress log waiting, failed-run re-resolution, and rebase-pending evidence preparation where the current logic is private or embedded in `evaluate_failure`.
- Preserve current production call paths and return values.
- Keep GitHub reads behind the injected `Runner` seam so the new child remains offline-testable.
- Ensure collection states distinguish ready evidence, in-progress runs, transient failures, and terminal health failures. Do not collapse them through truthiness.
- Keep all collected text redacted and bounded before it crosses into persisted evidence.

### UPDATED: python/larch/implement/_ci_launcher.py

Extend the launcher contract so validated architectural-invariant evidence reaches the selected fixer.

- Add an optional `--invariant-evidence` launcher argument to the shared CI-launcher parsing and launch-argument construction path used by Codex, Cursor, and Claude CI launchers.
- Preserve existing behavior when the option is absent, including current plan-file and failure-log inputs.
- Treat this option as a child-owned, already-validated path: do not replace it with an ambient repository search or silently substitute unrelated invariant context.
- Include the supplied invariant-evidence file in the fixer prompt/context using the same bounded, untrusted-evidence framing used for failure evidence.
- Reject unreadable, non-regular, or unsafe supplied evidence at the launcher boundary as a defensive failure, while leaving containment and identity validation authoritative in `ci_fixer_lane`.
- Keep launcher prompt construction deterministic so the selected fixer receives the same validated evidence path and content regardless of inherited cwd.

### UPDATED: python/larch/implement/ci.py

Add the public CLI entry function while leaving existing CI commands unchanged.

- Add `fixer_lane_main(argv)` as a thin delegation boundary into `ci_fixer_lane`.
- Define CLI arguments for all identity-bearing child inputs, including the configured bgjob merge-result env path and the optional invariant-evidence path.
- Preserve argparse help and usage behavior consistent with other `ci` verbs.
- Pass the production runner and environment through explicit injectable seams.
- Keep digest behavior byte-compatible for current `ci distill-log` callers.
- Avoid importing launcher orchestration logic into this CLI module beyond the new child delegation.

### UPDATED: python/larch/cli.py

Register the new runtime command.

- Add `("ci", "fixer-lane")` mapped to `larch.implement.ci.fixer_lane_main`.
- Preserve registry ordering and lazy import behavior.
- Do not add a script shim or a production Step 8 dispatch entry.

### NEW: skills/implement/scripts/step-8-ci-fixer.sh

Create the dormant foreground bgjob wrapper.

- Start with Bash 3.2-compatible strict mode.
- Resolve `${CLAUDE_PLUGIN_ROOT}`, `IMPLEMENT_TMPDIR`, repository state, run identity, and handoff identity through established session and ship-state sources. Do not derive the repository from ambient cwd.
- Validate the handoff directory, rounds file, status file, bail file, bgjob directory, configured bgjob merge-result env, and result env. Reject symlinks, non-regular files, unsafe parents, and paths outside the implement tmpdir.
- Parse only identity and tier metadata from `fixer-rounds.tsv`. Never read `distilled-failure.md`, raw logs, architectural-invariant evidence, or other CI evidence.
- Call the existing `next_untried_tier` surface to select the first available untried `implement.ci_recovery_fixer` tier. Return `operator-bail` when the waterfall is exhausted or no safe tier is available.
- Give each attempt a deterministic bgjob step identity derived from validated durable inputs so re-entry rejoins the same job instead of starting a duplicate.
- Derive one validated deterministic merge-result env path for that bgjob step and configure it as the existing `python/cli.py bgjob start` result-merge target. Pass that identical path to `python/cli.py ci fixer-lane --bgjob-result-env ...`; do not rely on child stdout being captured into the merge result.
- If the bgjob result is pending, invoke only the documented `python/cli.py bgjob wait` command and pass its envelope through.
- If no matching job exists, clear only validated stale result sidecars, then call `python/cli.py bgjob start` with the full waterfall budget, the configured merge-result env, and a child command of `python/cli.py ci fixer-lane`.
- On completion, require `BGJOB_STATUS=DONE`, `BGJOB_RC=0`, a regular merge-result env, and matching run ID, attempt, tier, starting HEAD, input fingerprint, and deterministic step identity.
- Read only the validated identity and typed routing KVs from the merge-result env. Cross-check its shared fields against the durable `fixer-status.env`; reject disagreement, stale data, malformed fields, foreign result files, or symlinked results instead of routing from them.
- Route only from the explicit typed result token in the validated merge-result env: `reship`, `retry-next-tool`, or `operator-bail`. Never infer success from `BGJOB_RC=0` alone.
- Emit only the typed result and bounded identity/status KVs needed by a future production caller.
- Do not run `gh`, inspect CI logs, edit files in the repository, commit, push, change the repository cwd for fixer work, or invoke the fixer launcher directly.
- Leave the script unreferenced by production Step 8.

### NEW: skills/implement/scripts/test-step-8-ci-fixer.sh

Add a self-contained offline wrapper harness.

- Build isolated fake plugin, repository, tmpdir, state, and bgjob command surfaces.
- Stub `python/cli.py` commands and record exact argv without network or vendor tool access.
- Model the configured bgjob result-merge target explicitly: make the fake child write its typed result only to the requested merge-result env, not stdout, and assert the wrapper routes from that file.
- Cover first-tier selection, skipping unavailable tiers, next-tier selection from valid rounds, exhaustion, and invalid attempted-tier data.
- Cover a fresh bgjob start, a live-job rejoin, `WAIT` passthrough, valid `DONE` consumption, nonzero bgjob completion, and missing result files.
- Assert that the start command configures the same deterministic merge-result env path that the child receives through `--bgjob-result-env`.
- Cover merge-result/status disagreement, missing typed result, stale run ID, attempt, tier, HEAD, input fingerprint, and deterministic step identity rejection.
- Cover symlinked directories, status files, result envs, rounds files, merge-result envs, and evidence-adjacent paths.
- Assert that foreground execution never calls `gh`, reads evidence files, invokes a vendor launcher, changes repository contents, or mutates the repository.
- Assert that production `step-8-ship.sh` and `skills/implement/SKILL.md` do not reference the dormant wrapper.

### UPDATED: python/tests/implement/test_ci.py

Test the new CLI boundary, launcher integration, and core child behavior.

- Assert CLI help, required arguments, invalid tiers, invalid attempts, malformed fingerprints, repository mismatch, tmpdir escape, unsafe merge-result targets, and symlink rejection.
- Assert `python/larch/cli.py` registers `ci fixer-lane`.
- Use injected runners and launcher fakes to prove each invocation launches exactly one selected tier with `FIXER_LANE_TIMEOUT_SEC`.
- Cover Codex, Cursor, and Claude dispatch argument construction, including delivery of the validated optional invariant-evidence path through the launcher interface.
- Cover launcher behavior with invariant evidence absent and supplied, and assert an arbitrary or identity-mismatched path cannot reach a launcher.
- Cover one bounded missing-run-ID resolution attempt and refusal to continue without a stable run identity.
- Cover supplied digest validation, digest retry, in-progress evidence, collection failure, bounded redacted raw-log fallback, and redaction/write failure.
- Cover architectural-invariant evidence acceptance only for the expected validated path and identity.
- Cover HEAD and fingerprint checks before launch and result consumption.
- Invoke the child from a deliberately wrong inherited cwd and assert the selected launcher observes the validated repository root; assert cwd is restored after success, typed recoverable outcomes, launcher exceptions, and closed failures.
- Assert identity fields in all successful and recoverable result files.
- Assert the child writes a valid bgjob merge-result env for every valid typed result, that shared fields match `fixer-status.env`, and that stdout alone cannot satisfy the result protocol.
- Assert valid `reship`, `retry-next-tool`, and `operator-bail` result persistence exits with `0`; assert usage and closed failures exit nonzero without a routable merge result.
- Assert newline injection, duplicate keys, malformed rows, unsafe output paths, atomic-write failures, merge-result write failures, and status/merge consistency failures fail closed.
- Assert typed routing for success, next-tool retry, and operator bail.

### UPDATED: python/tests/implement/test_ci_monitor.py

Test newly exposed evidence helpers and preserve existing monitor behavior.

- Cover ready, in-progress, transient-error, and terminal-error collection states.
- Cover bounded in-progress polling and timeout without real sleeps.
- Cover one-shot run-ID re-resolution success, ambiguity, empty results, and query failure.
- Cover failed-job classification passed to the child, including malformed names and aggregator gate filtering.
- Cover rebase-pending preparation helpers without changing the existing non-pending `run_ci_fix` result.
- Add regression assertions that existing `evaluate_failure`, monitor, rerun, and production fixer tests retain their current behavior.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Add wrapper-specific structural and dispatch coverage.

- Assert the new wrapper and its shell harness exist and use `python/cli.py ci fixer-lane`.
- Pin the required `bgjob start` result-merge configuration, the child `--bgjob-result-env` forwarding, and the exact documented `bgjob wait` shape.
- Assert the wrapper uses a merge-result env, cross-checks it with the durable status env, and validates identity before routing.
- Assert it calls the tier-selection surface and does not hard-code a parallel waterfall.
- Assert no production Step 8 registry entry, skill prompt, ship wrapper, or ship driver invokes `step-8-ci-fixer.sh`.
- Add subprocess-level wrapper cases that complement the shell harness for environment rehydration, bgjob envelopes, merge-result disagreement, stale results, and symlink rejection.

## Edge cases

- A run ID is absent, changes during the bounded resolution attempt, or refers to another repository.
- The selected run is still queued or in progress for the full evidence wait budget.
- GitHub returns a failed-jobs list but no usable failed-log body.
- Digest generation succeeds but writes a stale, empty, oversized, foreign, or symlinked file.
- Raw logs contain secrets, control characters, forged `KEY=value` rows, or fence terminators.
- Optional invariant evidence is valid at initial parsing but changes, becomes a symlink, or no longer matches its recorded identity before launcher dispatch.
- The repository HEAD changes before launch, changes during a failed launcher, or changes after a successful fixer.
- The child begins from a cwd outside the validated repository, fails to change to the validated repository, or cannot restore its inherited cwd after dispatch.
- A launcher wrapper returns zero while its `.done` sentinel records failure or timeout.
- A fixer reports success without a valid repository change or with a stale identity.
- `fixer-rounds.tsv` contains duplicate attempts, unknown tiers, malformed columns, or a row from another run.
- A previous bgjob result exists for the same step name but a different HEAD or fingerprint.
- The bgjob is live but its result env is missing, or it is dead with only a partial result.
- The child emits a valid-looking stdout envelope but does not write the configured merge-result env.
- The merge-result env exists but disagrees with `fixer-status.env`, lacks a typed result, or contains a stale deterministic step identity.
- Codex or Cursor disappears between tier selection and launch.
- Claude is disabled by launch-time availability.
- A result, merge-result, or bail write fails after a launcher has modified the repository.
- Optional architectural evidence exists but its metadata no longer matches the current diff.

## Failure modes

- Return a usage or closed-failure exit before launch for invalid roots, identities, tiers, attempts, paths, cwd transition, or merge-result targets.
- Return `retry-next-tool` through verified durable and merge-result payloads when the selected vendor is unavailable, times out, fails safely, or produces no usable progress while another tier may remain.
- Return `operator-bail` through verified durable and merge-result payloads when evidence cannot be made safe, identity cannot be proven, the waterfall is exhausted, repository state is unsafe, or result persistence cannot be verified.
- Return `reship` through verified durable and merge-result payloads only after the selected fixer completes successfully and all result identities and writes verify.
- Use `BGJOB_RC=0` only for a fully persisted, verified typed result. Treat nonzero bgjob completion as closed failure; never let a wrapper route from it as though it were a recoverable typed outcome.
- Never treat missing, malformed, stale, stdout-only, or status/merge-disagreeing files as an empty successful result.
- Never let a foreground wrapper compensate by reading CI evidence, changing cwd for launcher work, or editing the repository.
- Keep production Step 8 unchanged even if all dormant tests pass.

## Testing strategy

- Run targeted Python tests:
  - `python3 -m pytest -q python/tests/implement/test_ci.py`
  - `python3 -m pytest -q python/tests/implement/test_ci_monitor.py`
  - `python3 -m pytest -q python/tests/implement/test_implement_dispatch.py`
- Run the offline shell harness:
  - `bash skills/implement/scripts/test-step-8-ci-fixer.sh`
- Run Bash syntax and Bash 3.2 compatibility checks for both new scripts.
- Run the repository’s configured Python linters and type checker only against the changed Python files.
- Run the residual-Bash and script-structure checks that cover new files under `skills/implement/scripts/`.
- Confirm with targeted reference searches that `step-8-ci-fixer.sh` is absent from `skills/implement/SKILL.md`, `skills/implement/scripts/step-8-ship.sh`, and production Python ship dispatch.
- Keep all tests offline. Stub `gh`, bgjob, git mutation, cwd-sensitive launchers, and vendor launchers.

## Acceptance

- Run targeted Python tests:
  - `python3 -m pytest -q python/tests/implement/test_ci.py`
  - `python3 -m pytest -q python/tests/implement/test_ci_monitor.py`
  - `python3 -m pytest -q python/tests/implement/test_implement_dispatch.py`
- Run the offline shell harness:
  - `bash skills/implement/scripts/test-step-8-ci-fixer.sh`
- Run Bash syntax and Bash 3.2 compatibility checks for both new scripts.
- Run the repository’s configured Python linters and type checker only against the changed Python files.
- Run the residual-Bash and script-structure checks that cover new files under `skills/implement/scripts/`.
- Confirm with targeted reference searches that `step-8-ci-fixer.sh` is absent from `skills/implement/SKILL.md`, `skills/implement/scripts/step-8-ship.sh`, and production Python ship dispatch.
- Keep all tests offline. Stub `gh`, bgjob, git mutation, cwd-sensitive launchers, and vendor launchers.

oversize_override: operator
diff_lines: 2050

## Test plan
(no test plan section in plan-file)
