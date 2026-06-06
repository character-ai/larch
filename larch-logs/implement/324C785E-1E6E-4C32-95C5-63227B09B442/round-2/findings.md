### FINDING_1: Post-success add-dir serialization destroys successful Codex output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cleanup-lifecycle-output.txt
- **Severity**: important
- **Concern**: After a successful `codex exec`, `launch-codex-exec.sh` can call `write_preflight_bundle` when `--add-dir` metadata serialization fails (e.g., `jq` absent and path contains whitespace/control chars). That helper truncates `$OUTPUT`, overwrites collector sidecars (`.meta`, `.diag`, `.done`), skips `codex_launcher_promote_inner_done`, and emits `LAUNCHER_EXIT=2` — reporting failure and destroying a succeeded run’s transcript.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split post-success metadata failure from preflight handling; do not truncate OUTPUT or reuse write_preflight_bundle after dispatch.
  - From cursor-specialist-correctness-output.txt: Restrict write_preflight_bundle to pre-dispatch; on post-exec metadata failure warn append safe meta promote inner done emit real LAUNCHER_EXIT.
  - From cursor-specialist-edge-cases-output.txt: Serialize add-dir before dispatch and fail preflight without running Codex; or preserve output on post-run metadata failure and emit actual LAUNCHER_EXIT while documenting workdir-only retry fallback.
  - From dyn-cleanup-lifecycle-output.txt: Serialize `--add-dir` JSON before the retry loop (or fail closed at argv-parse time for unserializable paths). If serialization still fails after a successful exec, log a warning and append outer meta with a safe fallback (e.g. `[]` or workdir-only JSON per collector defaults) instead of calling `write_preflight_bundle`; reserve `write_preflight_bundle` for pre-dispatch failures only.

### FINDING_2: Codex-exec outer-retry logic duplicated with divergent jq fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-retry-path-parity-output.txt
- **Severity**: important
- **Concern**: `collect-agent-results.sh` implements Codex-exec outer-retry logic twice — in `launch_outer_retry_or_mark` (~700–710) and inline in the empty-output retry queue (~1129–1145) — with divergent behavior. The inline path always pipes `OUTER_LAUNCHER_ADD_DIRS_JSON` through `jq` with no `command -v jq` guard; the helper path falls back to `--add-dir "$META_OUTER_LAUNCHER_WORKDIR"`. On jq-less hosts, `/research` empty-output retries can reject valid launcher metadata and fail to retry (or lose non-workdir add-dir grants). Duplication also risks further drift on metadata-field changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Route empty-output outer retries through launch_outer_retry_or_mark or extract one shared helper used by both paths.
  - From cursor-specialist-correctness-output.txt: Add command -v jq branch to inline block mirroring launch_outer_retry_or_mark lines 700-709.
  - From cursor-specialist-edge-cases-output.txt: Parse add-dir metadata without jq via repeated meta keys or shared json_array_from_args helper.
  - From cursor-specialist-plan-fidelity-output.txt: Mirror launch_outer_retry_or_mark jq fallback (lines 708-709) in the 1129 block or delegate to that helper.
  - From dyn-retry-path-parity-output.txt: Reuse the same `command -v jq` branch from `launch_outer_retry_or_mark` in the inline codex-exec block (or route empty-output outer-launcher retries through the helper with the original `${ORIG_OUTPUT}.prompt` sidecar), and add a harness case that runs empty-output retry with `PATH` excluding `jq` and asserts a launcher retry with `--add-dir "$WORKDIR"`.
  - From dyn-retry-path-parity-output.txt: Extract a shared helper (e.g. `build_codex_exec_outer_retry_args` + `launch_codex_exec_outer_retry`) used by both call sites; keep only the prompt-source difference (strengthened temp file vs `.prompt` sidecar) at the call site.

### FINDING_3: Missing launch-codex-exec outer-retry fixture in test-collect-agent-results.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-retry-path-parity-output.txt
- **Severity**: important
- **Concern**: Plan-required harness coverage for `launch-codex-exec.sh` empty-output outer-retry is absent from `test-collect-agent-results.sh`. Collector retry regressions (raw `CMD_JSON` replay, dropped auth/metadata, missing jq-fallback behavior) could ship without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add the planned fixture asserting launch-codex-exec retry argv preservation and no CMD_JSON fallback.
  - From cursor-specialist-correctness-output.txt: Add fixture asserting retry invokes launch-codex-exec.sh with preserved metadata.
  - From cursor-specialist-testing-output.txt: Add fixture asserting launch-codex-exec.sh re-entry with preserved sandbox effort usage timing and add-dir metadata.
  - From cursor-specialist-edge-cases-output.txt: Add fixture asserting collector invokes launch-codex-exec.sh with retargeted output and preserved sandbox effort usage-label timing-kind and add-dir args.
  - From cursor-specialist-plan-fidelity-output.txt: Add fixture asserting collector invokes launch-codex-exec.sh with codex-exec metadata and *-retry.txt output.
  - From dyn-retry-path-parity-output.txt: Add the planned fixture (including a no-`jq` variant) to `scripts/test-collect-agent-results.sh` per the plan’s acceptance criteria.

### FINDING_4: Stale unused `run_codex` second argument at call site
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `lint-fix-loop.sh:534` still passes an unused `prompt_body` second argument to `run_codex` after a signature change, misleading readers into thinking the inline prompt is used instead of `prompt.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the stale second argument at the call site.

### FINDING_5: Stale agent-model-args temp-file comments in protocol docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Stale `agent-model-args` temp-file comments remain in `skills/shared/voting-protocol.md:161` and `skills/shared/dialectic-protocol.md:229` after switching to `launch-codex-exec.sh`, creating a maintenance hazard where raw model-args boilerplate could be reintroduced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update the comment to state the launcher owns model args and auth.

### FINDING_6: launch-codex-exec duplicates launch-codex-ci mechanics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The new `launch-codex-exec.sh` largely duplicates `launch-codex-ci` mechanics, increasing long-term drift surface; future auth/retry fixes may require parallel edits across launchers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Track follow-up extraction of shared Codex prepare/retry/record helpers after stabilization.

### FINDING_7: test-launch-codex-exec.sh coverage gaps vs documented contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-launch-codex-exec.sh` is thinner than the sibling `test-launch-codex-exec.md` contract and plan acceptance criteria. Auth-prep, model-args failure, env-key/login, sandbox, prompt-file, and temp-`CODEX_HOME` cleanup cases are documented but largely unimplemented, so auth/retry/preflight regressions may pass CI on happy-path-only coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend test-launch-codex-exec.sh per scripts/test-launch-codex-exec.md.
  - From cursor-specialist-testing-output.txt: Extend harness with stubbed auth and model-args failure cases per test-launch-codex-exec.md and plan acceptance.
  - From cursor-specialist-edge-cases-output.txt: Implement documented harness cases or narrow the .md contract to match the shell harness.
  - From cursor-specialist-plan-fidelity-output.txt: Implement missing cases in test-launch-codex-exec.sh or align launch-codex-exec.md and test-launch-codex-exec.md with actual coverage.

### FINDING_8: [OUT_OF_SCOPE] SECURITY.md outer-retry docs omit launch-codex-exec.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md:188` outer-launcher retry documentation still mentions only `launch-review.sh`, not `launch-codex-exec.sh`, so security readers may underestimate which retry replay paths exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update the outer-retry paragraph to include launch-codex-exec.sh metadata contract.

### FINDING_9: [OUT_OF_SCOPE] run-external-agent.sh still bypasses shared Codex auth
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cleanup-lifecycle-output.txt, dyn-retry-path-parity-output.txt
- **Severity**: latent
- **Concern**: `run-external-agent.sh` direct `codex exec` paths remain unwired for shared `external_prepare_codex_auth` / env-key preference by explicit plan OOS. Callers bypassing `launch-codex-exec.sh` (and the linter) can still skip `OPENAI_API_KEY` handling; deferred follow-up sweep per OOS #3475.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Continue the planned follow-up sweep noted in the OOS issue.
  - From cursor-specialist-testing-output.txt: Follow-up sweep wiring external_prepare_codex_auth at remaining call sites.
  - From cursor-specialist-edge-cases-output.txt: Follow-up sweep or wrapper-level auth hook as noted in OOS #3475.
  - From cursor-specialist-plan-fidelity-output.txt: Follow-up sweep per OOS issue; explicitly out of plan scope.

### FINDING_10: Codex model-args failure emits contradictory RESPONSE_FILE=
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `run-negotiation-round.sh:89-93` emits `RESPONSE_FILE=` on Codex model-args failure, contradicting `run-negotiation-round.md` and behaving asymmetrically vs the Cursor branch. Invalid `LARCH_CODEX_MODEL` yields exit 1 plus empty `RESPONSE_FILE`, so callers may read empty output as a negotiation result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove RESPONSE_FILE emit on model-args failure or align contract and all tool branches.

### FINDING_11: [OUT_OF_SCOPE] Research lanes pass full prompt via inline --prompt CLI arg
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/research/references/research-phase.md:150-156` passes the full prompt via `--prompt` CLI substitution. Very long `RESEARCH_QUESTION` risks `ARG_MAX` / E2BIG; crafted question text also preserves a shell-quoting injection surface at orchestration time. Validation-phase already uses `--prompt-file`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use --prompt-file with orchestrator-written tmp file like validation-phase.
  - From cursor-specialist-security-output.txt: Document --prompt-file via a pre-written tmpdir file (as validation-phase does) instead of inline --prompt substitution.

### FINDING_12: Missing negotiation Codex auth regression tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-required auth regression tests for the negotiation Codex branch are absent from `test-run-negotiation-round.sh`. Inline Codex auth wiring (`OPENAI_API_KEY`, login fallback, auth-prep exit 2, temp `CODEX_HOME` cleanup) can regress without harness detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add env-key login trust -c cleanup and auth-prep exit 2 fixtures per plan.
  - From cursor-specialist-testing-output.txt: Add env-key login trust -c cleanup and auth-prep exit 2 cases modeled on test-launch-codex-ci.sh.
  - From cursor-specialist-edge-cases-output.txt: Add env-key login auth-prep-exit-2 and temp-home cleanup assertions mirroring other Codex auth harnesses.
  - From cursor-specialist-plan-fidelity-output.txt: Add env-key/login/trust/cleanup/auth-prep-failure cases with stubbed Codex home and auth helpers.

### FINDING_13: FAILURE_REASON string drift breaks test-collect-agent-retry case-s2
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After `collect-agent-results.sh` allowlisted `launch-codex-exec.sh`, `test-collect-agent-retry.sh:727` expects a stale `FAILURE_REASON` string. `make test-collect-agent-retry` case-s2 fails on every CI run because `assert_fail_closed` requires an exact match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update expected reason to the new canonical string and add a positive launch-codex-exec.sh outer-retry case.

### FINDING_14: Missing LAUNCHER_EXIT=1 with wrapper-exit-0 regression in test-lint-fix-loop.sh
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No harness case covers launcher emitting `LAUNCHER_EXIT=1` while the wrapper exits 0. `lint-fix-loop` could treat Codex launcher failures as success if `LAUNCHER_EXIT` parsing regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub launcher case emitting LAUNCHER_EXIT=1 exit 0 and assert run_codex returns non-zero.

### FINDING_15: Missing lint-codex-exec-auth harness fixtures from plan
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-lint-codex-exec-auth.sh` lacks plan-listed fixtures (helper-plus-raw-exec, plain markdown fence, comments, out-of-scope paths). Linter regressions on those shapes would not be caught by `make test-lint-codex-exec-auth`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add mixed-auth.sh and one-line markdown fence negative fixtures.
  - From cursor-specialist-plan-fidelity-output.txt: Add the four missing fixture trees from the plan harness spec.

### FINDING_16: Codex-exec retry replays add-dir without path containment validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `collect-agent-results.sh` replays `OUTER_LAUNCHER_ADD_DIRS_JSON` as `--add-dir` without path containment validation. A same-UID process tampering session `.meta` before empty-output retry could add full-auto write grants outside the repo workdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each replayed add-dir against canonical OUTER_LAUNCHER_WORKDIR/session root; reject .. and non-directory paths; fail closed like launch-review.sh --codex-add-dir.

### FINDING_17: Linter misses run-external-agent.sh codex exec dispatch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `lint-codex-exec-auth.sh` only matches literal `codex exec` tokens, not `run-external-agent.sh -- codex exec` dispatch. New scripts could pass lint while launching unwired Codex without `OPENAI_API_KEY` handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Also flag codex exec after -- or require auth helper / launch-codex-exec.sh on run-external-agent Codex dispatch lines.

### FINDING_18: launch-codex-exec --add-dir paths not bounded to workdir at launch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-exec.sh` accepts `--add-dir` paths without bounding them to workdir/session root at launch time. Misconfigured or future call sites could grant full-auto Codex write access to sensitive directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add containment checks for --add-dir mirroring launch-review.sh session-root validation.

### FINDING_19: Stale voting-protocol prose references run-external-agent for Codex voter
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/voting-protocol.md:71-77` prose says the Codex voter uses `run-external-agent.sh` while the fence uses `launch-codex-exec.sh`, which may mislead operators debugging voter auth failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update Codex voter documentation to name launch-codex-exec.sh.

### FINDING_20: [OUT_OF_SCOPE] dialectic-execution.md stale Codex judge launch reference
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/design/references/dialectic-execution.md` still references `run-external-agent` for the Codex judge while `dialectic-protocol.md` uses the launcher, risking stale operator instructions during design sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align dialectic-execution.md with dialectic-protocol.md launcher.

### FINDING_21: lib-external-launcher-common.md missing canonical env-key inventory
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/lib-external-launcher-common.md:13` lacks the canonical merged env-key inventory required by plan acceptance; only a shorter wired-call-site list is present, so operators reading the lib contract see incomplete coverage vs `SECURITY.md` and sibling docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Paste verbatim merged inventory from SECURITY.md or link to canonical consumer docs.

### FINDING_22: negotiation-round missing EXIT trap for temp CODEX_HOME cleanup
- **Reviewer(s)**: dyn-cleanup-lifecycle-output.txt
- **Severity**: important
- **Concern**: `run-negotiation-round.sh:73-117` creates `mktemp`-backed `codex_home` with `_negotiation_codex_cleanup` at explicit call sites only. Unlike `launch-codex-exec.sh` and `launch-codex-ci.sh`, there is no `EXIT` trap, so `SIGTERM`/`SIGINT` during long `codex exec` can leave `/tmp/larch-codex-negotiation-home-*` behind (possibly including symlinked auth). Contract prose (“removed on exit”) overstates coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cleanup-lifecycle-output.txt: Register `trap '_negotiation_codex_cleanup' EXIT` immediately after `mktemp` (before auth prep), matching other Codex launchers; keep explicit cleanup calls if desired, and extend `scripts/test-run-negotiation-round.sh` with a simulated interrupt path that asserts the temp home is removed.

### FINDING_23: [OUT_OF_SCOPE] Pre-existing empty-output retry loop duplicates parse_retry_meta
- **Reviewer(s)**: dyn-retry-path-parity-output.txt
- **Severity**: latent
- **Concern**: The empty-output retry main loop (~962–1157) inlines full `.meta` parsing instead of calling `parse_retry_meta` (504–546). This predates the branch but grew with new `OUTER_LAUNCHER_*` fields duplicated in both places, increasing maintenance burden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-path-parity-output.txt: Address the concern above.
