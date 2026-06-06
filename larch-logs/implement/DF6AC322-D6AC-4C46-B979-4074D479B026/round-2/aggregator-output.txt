### FINDING_1: Dynamic-Codex explicit allow is not regression-locked
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-test-runner-output.txt
- **Severity**: latent
- **Concern**: The explicit dynamic-Codex allow arm is currently subsumed by broad `*-output*` allows, so tests can pass even if the explicit contract clause is deleted or reordered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add unit pins for every explicit pattern or drop redundant return-0 patterns and rely on comment plus broad allow.
  - From cursor-specialist-testing-output.txt: Add a structural harness pin for clause ordering (after static codex denies, before broad allows) and absence of dyn-*-codex-output-*.txt catch-all globs.
  - From dyn-test-runner-output.txt: Add a structural pin (e.g., in `scripts/test-larch-log.sh` or a small companion harness) that asserts the explicit dynamic-Codex `case` arm exists between the static `codex-specialist-*` deny and the broad output allow, or temporarily stub out the broad allow in an isolated test and verify dynamic Codex sidecars (`.meta`, `.json`, `.cap-hit`) and phased shapes still return included.

### FINDING_2: Dynamic-Codex sidecar and prompt unit coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-runner-output.txt
- **Severity**: latent
- **Concern**: Unit-level `round_artifact_included()` pins do not mirror the full dynamic-Codex sidecar and prompt exclusion matrix, leaving regressions to slower integration coverage or broad-pattern overlap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Mirror write-round coverage with assert_round_artifact_included for .meta .json .cap-hit phased variants and codex-specialist-security-output-phase2.txt.
  - From cursor-specialist-testing-output.txt: Add assert_round_artifact_included rows for dyn-api-contract-codex-output.txt.meta/.json/.cap-hit, dyn-api-contract-codex-output.txt.prompt, and dyn-api-contract-codex-output-phase2.txt.prompt.
  - From cursor-specialist-edge-cases-output.txt: Add assert_round_artifact_included rows for dyn-api-contract-codex-output.txt.meta .cap-hit and .prompt exclusion
  - From dyn-test-runner-output.txt: Mirror the write-round negative/inclusion matrix at the `assert_round_artifact_included` layer for at least `dyn-api-contract-codex-output.txt.meta`, `.cap-hit`, `dyn-api-contract-codex-output-phase2.txt.meta`, and `dyn-api-contract-codex-output.txt.prompt` so both harnesses enforce the same contract.

### FINDING_3: Dense dynamic-Codex glob arm is hard to maintain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Eight globs on one `case` line reduce scanability in ordering-sensitive deny/allow logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split into two case arms or add a four-family comment above the pattern list.

### FINDING_4: [OUT_OF_SCOPE] Design and implement log allowlists may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Parallel implement/design artifact retention matchers diverge without shared deny primitives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared deny primitives when next touching both matchers (pre-existing).

### FINDING_5: [OUT_OF_SCOPE] Branch/diff bundles unrelated Python Step 8 cutover
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-test-runner-output.txt
- **Severity**: latent
- **Concern**: The reviewed branch/diff includes unrelated Python Step 8 cutover work alongside the dynamic-Codex log-retention change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split or label commits/PR sections by concern (pre-existing branch composition).
  - From dyn-test-runner-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Stale finalize stall metadata can survive restore assumptions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Restore preserves existing `STALL_TRACKING=true` under assumptions about later finalize rewrites; stale finalize state could route teardown down a stalled path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Phased dynamic-Codex artifacts are not currently produced
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-runner-output.txt
- **Severity**: latent
- **Concern**: Phased dynamic-Codex fixtures document forward-looking retention for artifact shapes not emitted by current dynamic Codex dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: No change required for this PR; revisit if waterfall starts emitting phased Codex twins
  - From dyn-test-runner-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Static Codex sidecar exclusions lack fixtures
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Unphased static Codex `.json` and `.cap-hit` exclusions are not asserted in write-round fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add excluded fixtures and assert_not_file for codex-specialist-security-output.txt.json and .cap-hit.

### FINDING_9: Internal errors expose raw exception details in stdout JSON
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `INTERNAL_ERROR` now exposes raw exception text through orchestrator-visible JSON, risking leakage of paths or sensitive substrings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Keep INTERNAL_ERROR detail generic or run a stricter internal-error scrubber; keep full tracebacks on the quiet-log path only.

### FINDING_10: Retry-only dynamic-Codex retention depends on broad patterns
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Retry-shaped dynamic-Codex artifacts are not explicitly allowed and would be lost if broad output patterns are narrowed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add retry-only positive fixtures to test-larch-log-write-round.sh or extend the explicit clause when retry generators exist; clarify in larch-log.md that retry shapes are broad-pattern-only today

### FINDING_11: Contract JSON write failures can be swallowed
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: important
- **Concern**: `emit_result()` suppresses contract-stream write failures, allowing an empty or partial stdout contract with no breadcrumb or exit override.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Track whether any bytes were written to the contract stream; on failure, log via `BreadcrumbWriter` (mirroring the journal skip path at `730`) and either retry on fd 3 directly or downgrade to `Outcome.INTERNAL_ERROR` when zero contract bytes were emitted.

### FINDING_12: `quiet_init()` may clobber inherited fd 3
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: important
- **Concern**: Python quiet initialization always saves stdout into fd 3, potentially overwriting an inherited parent contract stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Before `dup2(1, 3)`, detect an open fd 3 that differs from fd 1 (e.g., `fcntl(F_GETFD)`/`stat` parity with bash’s preserved contract fd) and skip re-saving fd 3 when inheriting a valid parent contract stream; add a subprocess regression test that sets `LARCH_QUIET_ACTIVE=1` with a foreign `LARCH_QUIET_PID`, pre-seeds fd 3, and asserts JSON still reaches the capture pipe.

### FINDING_13: fd-3 open failure falls back to quiet log
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: important
- **Concern**: If `contract_stream()` cannot open fd 3 after quiet init, it silently falls back to redirected stdout, sending JSON to the quiet log instead of the orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Treat fd-3 open failure as fatal for the contract path: log loudly and either write directly with `os.write(3, …)` as a last resort or surface `Outcome.INTERNAL_ERROR` instead of silently falling back to redirected stdout.

### FINDING_14: [OUT_OF_SCOPE] CI monitor warnings are hidden in quiet logs
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: nit
- **Concern**: CI suspend and `git rev-list` warnings may no longer appear in orchestrator transcripts when quiet mode is active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Pre-existing finalize writers have unquoted state hazards
- **Reviewer(s)**: dyn-quiet-fd-output.txt, dyn-shell-quoting-output.txt
- **Severity**: latent
- **Concern**: Other finalize-state writers still emit unquoted `KEY=value` lines without newline rejection, preserving pre-existing spoofed-key/metacharacter risks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.
  - From dyn-shell-quoting-output.txt: Address the concern above.

### FINDING_16: Stall recovery can choose `STALL_STEP` from a non-stalled layer
- **Reviewer(s)**: dyn-stall-state-output.txt
- **Severity**: important
- **Concern**: `cmd_classify` uses unconditional `first_nonempty` for `STALL_STEP`/`EXIT_CODE`, so stale values from `ship-pr-state.sh` can override the layer that actually reports `STALL_TRACKING=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stall-state-output.txt: Gate `STALL_STEP`/`EXIT_CODE` selection on the same layer that made `stall_tracking` true—e.g. only read `state_stall_step` when `truthy "$state_stall_tracking"`, else fall through to finalize, then session—or add a regression where `ship-pr-state.sh` has `STALL_TRACKING=false` plus a non-empty `STALL_STEP` and `finalize-state.sh` has `STALL_TRACKING=true` with a different `STALL_STEP`, asserting classify emits the finalize step.

### FINDING_17: [OUT_OF_SCOPE] Restore preservation accepts only canonical `true`
- **Reviewer(s)**: dyn-stall-state-output.txt
- **Severity**: nit
- **Concern**: `restore-finalize-state.sh` preserves stall metadata only for canonical `true`, unlike broader truthy handling elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stall-state-output.txt: Address the concern above.

### FINDING_18: Restore rewrites Python-quoted state as unquoted lines
- **Reviewer(s)**: dyn-shell-quoting-output.txt
- **Severity**: important
- **Concern**: `restore-finalize-state.sh` rebuilds `finalize-state.sh` with bare `printf`, stripping Python’s shell quoting and allowing newline-injected spoofed keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-quoting-output.txt: Reuse the same single-quote writer on the bash side (small shared helper mirroring `_shell_single_quote`), reject `\n`/`\r` in every value before write, and add harness cases for newline/metacharacter `PR_TITLE`/`BAIL_REASON` round-tripping through restore → `implement-finalize.sh teardown`.

### FINDING_19: Quoted finalize booleans are misread before restore
- **Reviewer(s)**: dyn-shell-quoting-output.txt
- **Severity**: important
- **Concern**: Python now emits quoted booleans, but stall recovery and final-report readers compare raw strings, so `'true'`/`'false'` can be misclassified before restore rewrites them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-quoting-output.txt: Centralize finalize-state reads through the same unquote helper used in `implement-finalize.sh` (or teach `read-session-env-key.sh` an optional `--unquote-shell` mode), extend `truthy` to accept quoted `'true'`/`'false'`, and add regression tests for Python-quoted `finalize-state.sh` consumed by stall-recovery and write-final-report without an intervening restore.

### FINDING_20: [OUT_OF_SCOPE] Python and bash finalize-state parsers diverge
- **Reviewer(s)**: dyn-shell-quoting-output.txt
- **Severity**: latent
- **Concern**: Python handles shell-like quoting via `shlex.split`, while bash consumers only strip POSIX single-quoted literals, so future or hand-edited state files can parse differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-quoting-output.txt: Address the concern above.
