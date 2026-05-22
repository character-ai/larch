### FINDING_1: Pre-stall transcript temp (`tr_pre` / `transcript_pre`) leaks on emitter early exit
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-sidecar-integrity-output.txt
- **Concern**: When `cursor_launcher_emit_cursor_ci_stall_json_sidecar` returns before normal JSON/cleanup work (e.g. missing `jq`, sidecar dir resolution failure, early `mktemp` failure for capture temps), the caller-owned pre-stall transcript snapshot path is left on disk under `${TMPDIR:-/tmp}` (e.g. `larch-stall-tr-pre.*`). Repeated stalls or `jq`-less environments accumulate leaked files, enlarge disk use, and widen accidental disclosure of raw tails versus redacted sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: After wait on emit_pid, rm -f nonempty tr_pre; when _tr_owned=0 skip rm of transcript file inside emit (single owner).
  - From cursor-specialist-correctness-output.txt: After wait emit_pid run rm -f "$tr_pre" when set, or unlink transcript_pre on every emitter early return path.
  - From cursor-specialist-testing-output.txt: Parent rm -f tr_pre after wait or trap unlink transcript_pre on all emit exits including early returns.
  - From cursor-specialist-security-output.txt: After wait on emit_pid rm -f tr_pre in parent or trap EXIT in emitter for transcript_pre when not owned
  - From dyn-sidecar-integrity-output.txt: On every early `return 0` before normal cleanup runs, remove `transcript_pre` when it is a non-empty path and points at a regular file (mirroring the successful-path `rm -f "$tr_tmp"`), or have `cursor_launcher_run_stall_monitor` `rm -f "$tr_pre"` immediately after `wait "$emit_pid"` so cleanup is unconditional.

---


### FINDING_10: Process snapshot implementation differs from plan’s `ps -ef | grep cursor` (uid scope, caps, deliberate `grep` pattern)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Implementation uses uid-scoped `ps` with caps and argv filtering rather than a full `ps -ef` tree, so cross-UID or beyond-cap / oddly named workers may be missing; audits or plan readers may treat the implementation as incomplete versus the written plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document tradeoff or add optional full-tree capture behind a flag.
  - From cursor-specialist-correctness-output.txt: Match planned capture or document scope and cap in user-facing docs and JSON note fields.
  - From cursor-specialist-plan-fidelity-output.txt: Align plan wording or document the deliberate substitution for privacy and portability.

---


### FINDING_14: `jq`-less environments: no JSON sidecar while harness/tests skip `jq`-dependent coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-coverage-output.txt
- **Concern**: Without `jq`, Phase 1 stall JSON may be absent while tests skip fixtures, weakening diagnostics and allowing regressions to pass unnoticed on minimal hosts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fail closed if jq required or add non-jq assertion path.
  - From cursor-specialist-plan-fidelity-output.txt: Declare jq required for forensics or add a minimal fallback artifact.
  - From dyn-test-coverage-output.txt: If skipping is intentional, add a separate lightweight check (e.g. `test -n` after stall that a `cursor-ci-stall-*.json` file exists with non-zero size via `python3 -c` or `grep` for required substrings) so non-jq CI still catches “no sidecar written” regressions, or document that `jq` is mandatory for this harness in CI.

---


### FINDING_15: Plan still anchors stall strings in `launch-cursor-ci.sh` while logic lives in `lib-cursor-launcher-common.sh`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Triage following plan grep may waste time in the wrong file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update the plan file list or add a pointer comment in launch-cursor-ci.sh.

---


### FINDING_18: Stall JSON fixtures 7–8 do not assert the full stable sidecar contract / schema
- **Reviewer(s)**: dyn-test-coverage-output.txt
- **Concern**: Fixture 7 checks a subset of fields; fixture 8 is weaker (file + `tree:` prefix + timing). Regressions that null keys, strip fields, or produce minimal JSON may still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-output.txt: Add one or two `jq -e` guards on `$sc0` that require the full stable key set and types (`channel`, `pid`, `time_since_last_progress`, `capture_phase`, `transcript_tail_capture_phase`, `diag_capture_note`, `ps`, `lsof`, `git_state`, `transcript_tail_contract`, `last_transcript_lines`) plus minimal sanity (e.g. `time_since_last_progress >= 3` under `stall_env`, `ps` contains a marker substring such as `stall ps snapshot` from the implementation’s banner lines).
  - From dyn-test-coverage-output.txt: Reuse the same `jq -e` schema checks against `$sc8` (and the same optional `lsof` policy as fixture 7) so both stdout and tree stalls exercise the same sidecar contract.

---


### FINDING_19: Stall fixtures rely on launcher kill sequence for long-running synthetic children without explicit test-local cleanup
- **Reviewer(s)**: dyn-test-coverage-output.txt
- **Concern**: If the launcher exits early or kill regresses, multi-minute `sleep` children could leak into later cases or the host.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-output.txt: After each stall fixture completes, assert the wrapper/agent PID from `.diag` or the sidecar is not still running (`kill -0` fails) or record the stub PID and `kill -9` it in a subshell `trap` so a launcher bug cannot leave a multi-minute `sleep` behind for later cases or the host.

---


### FINDING_2: Stall sidecar dir fallback can attribute stalls to the wrong `round-*` when output is not under a round path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Fallback that picks the maximum `round-*` when the output path is not under `round-N` can write `cursor-ci-stall-*.json` under a directory that does not match the round where the failing step’s artifacts live, misleading audits and humans correlating stalls to steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Resolve round from the same source of truth as run logging (manifest / explicit round env) or record both intended and resolved round in the JSON and tighten the fallback heuristic.

---


### FINDING_3: `larch-log.sh` round artifact allow-list omits `cursor-ci-stall-*.json`, breaking post-merge audit aggregation on committed run trees
- **Reviewer(s)**: dyn-audit-scan-correctness-output.txt
- **Concern**: Stall JSON sidecars are written under `round-N/cursor-ci-stall-*.json` and `audit-scan-run.sh` globs them correctly, but `round_artifact_included` does not allow that pattern, so `larch-log.sh write-round` will not copy them into committed `larch-logs/implement/<RUN_ID>/round-<N>/`. Audits using `--run-dir` on committed trees can report `result:"pass"` with `count:0` even after a real stall, defeating the intended channel-distribution measurement path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-scan-correctness-output.txt: Add `cursor-ci-stall-*.json` to the `round_artifact_included` allow-list (and any needed staging/redaction behavior in `stage_round_artifact`), then extend `scripts/test-larch-log.sh` / `scripts/test-larch-log-write-round.sh` so committed round directories retain these sidecars for `audit-scan-run.sh` to aggregate.

---


### FINDING_4: Inherited `pipefail` plus `head -c` truncation can abort the stall JSON subshell before `jq` (SIGPIPE / exit 141)
- **Reviewer(s)**: dyn-shell-robustness-output.txt
- **Concern**: The stall JSON sidecar builder runs in a background subshell that inherits `set -o pipefail` from `launch-cursor-ci.sh`. Truncations such as `git_porcelain=$(printf '%s' "$git_porcelain" | head -c 32000)` and `rebase_patch=$(printf '%s' "$rebase_patch" | head -c 32000)` can yield non-zero pipeline status when the blob exceeds the cap, aborting the subshell under `set -e` before `jq` runs and dropping the sidecar without surfacing a launcher error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-robustness-output.txt: Avoid that pipeline under inherited `pipefail` (for example wrap only those lines in `set +o pipefail` / `set -o pipefail`, use a temp file plus `head -c` on the file, or append `|| true` with an explicit empty fallback only if you still validate the truncated content before `jq`).

---


### FINDING_5: Successful `jq` write followed by failed final `mv` to the sidecar path drops the artifact without an analogous diag marker
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Read-only run-log dir or full disk can lose the JSON sidecar after a real stall; operators/audits cannot distinguish omission due to I/O from omission due to missing `jq` or other assembly failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Append a `cursor-ci-stall-json: write failed …` line to the diag file when `mv` fails, analogous to the jq failure marker.

---


### FINDING_6: `git_state` capture vs `tree:` channel can describe different repos if `PWD` is not the monitored workspace root
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `git_state` uses the current working directory while the tree channel is tied to `PWD` at invocation; without an enforced `cwd == workspace` invariant, forensics can look coherent but reference the wrong repository relative to the tree root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Run git probes via `git -C` against the resolved workspace/tree root or assert matching cwd before capture.

---


