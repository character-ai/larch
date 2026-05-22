Here is the normalized structured finding list. In-scope items are merged by shared behavioral risk; out-of-scope items are separate blocks with `[OUT_OF_SCOPE]` preserved on the heading first line where the source used that tag.

---

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

### FINDING_7: Sidecar directory resolver can create `round-1` under `IMPLEMENT_TMPDIR` as a side effect of misconfiguration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Resolver may `mkdir` `IMPLEMENT_TMPDIR/round-1` when output is not under `round-*` but an implement dir exists, creating a directory unrelated to real rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Avoid mkdir side effect or use dedicated subdir with explicit contract.

---

### FINDING_8: `ps` argv snapshot may include unrelated same-UID processes whose argv contains “cursor”
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Broad `ps`/`grep` style argv snapshot for the same UID can include unrelated processes; redactors may miss patterns, inflating sensitive or misleading content in stall JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Scope argv capture to target_pid process tree only

---

### FINDING_9: No wall-clock bound on the background stall JSON emitter if `jq` blocks despite bounded raw inputs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Waiting on the background emitter can hang the stall monitor past SIGKILL and delay launcher teardown in rare cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Wrap jq or whole emitter in timeout with diag marker on timeout.

---

### FINDING_10: Process snapshot implementation differs from plan’s `ps -ef | grep cursor` (uid scope, caps, deliberate `grep` pattern)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Implementation uses uid-scoped `ps` with caps and argv filtering rather than a full `ps -ef` tree, so cross-UID or beyond-cap / oddly named workers may be missing; audits or plan readers may treat the implementation as incomplete versus the written plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document tradeoff or add optional full-tree capture behind a flag.
  - From cursor-specialist-correctness-output.txt: Match planned capture or document scope and cap in user-facing docs and JSON note fields.
  - From cursor-specialist-plan-fidelity-output.txt: Align plan wording or document the deliberate substitution for privacy and portability.

---

### FINDING_11: Operator doc claims “last 50 lines per stream” while merged transcript tail logic differs (110-line cap)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Doc and `jq` tail length can be misread relative to each other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align doc with 110-line cap or change jq to 100 lines.

---

### FINDING_12: `cursor_launcher_emit_cursor_ci_stall_json_sidecar` is a large monolith
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Harder localized edits and testing over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract capture helpers on next change.

---

### FINDING_13: Renamed assertion label in `test-audit-runs.sh` may add churn for failure-tag archaeology
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Renamed `[35c]` assertion label unrelated to stall feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Revert label unless required by harness.

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

### FINDING_16: `tree:` channel embeds absolute `PWD` in JSON/diagnostics
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Workspace path is copied into stall artifacts and audit channel keys; may be sensitive in some environments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use repo-relative or redacted channel token if path sensitivity matters

---

### FINDING_17: Post-SIGKILL `wait` can extend stall-handler return by bounded capture/redact work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Parent may not return promptly after kill, slightly delaying teardown or follow-up steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional overall cap on waiting or document the extra post-kill latency budget explicitly.

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

### FINDING_20: [OUT_OF_SCOPE] Review session used empty branch delta / wrong diff base (HEAD == `main`, empty precomputed diff)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-robustness-output.txt, dyn-audit-scan-correctness-output.txt, dyn-test-coverage-output.txt
- **Concern**: Reviewers note empty precomputed diff and no commits on `$(git merge-base HEAD main)..HEAD`, so review was against the current tree rather than an intended branch patch; re-run with correct base or non-empty diff as appropriate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-run session with non-empty diff or compare against intended base ref.
  - From cursor-specialist-plan-fidelity-output.txt: Reviewer must use origin/main or another correct base to see the branch patch. Use correct precomputed diff or diff against origin/main.
  - From dyn-shell-robustness-output.txt: The precomputed diff at `<TMPDIR>/round-4/diff.txt` was empty and `git log "$(git merge-base HEAD main)"..HEAD --oneline` produced no commits because this checkout’s `HEAD` and `main` both resolve to `df3dd544671eae219be3a78c800a14f03f370be2`, so the review used the current tree rather than a non-empty branch delta.
  - From dyn-audit-scan-correctness-output.txt: The path `<TMPDIR>/round-4/diff.txt` was empty, and in this workspace `HEAD` equals `main` at `df3dd544`, so there was no merge-base diff to attribute line-by-line; the finding above is from the shipped layout of `audit-scan-run.sh` (353-381), `scans.tsv` (line 7), and `larch-log.sh` (67-97) together.
  - From dyn-test-coverage-output.txt: The path `<TMPDIR>/round-4/diff.txt` was empty and `git log $(git merge-base HEAD main)..HEAD` produced no commits in this workspace, so this review is based on the current tree contents of [`scripts/test-launch-cursor-ci.sh`](scripts/test-launch-cursor-ci.sh) and the sidecar producer in [`scripts/lib-cursor-launcher-common.sh`](scripts/lib-cursor-launcher-common.sh), not on a non-empty branch diff artifact.

---

### FINDING_21: [OUT_OF_SCOPE] CI runs harnesses via Makefile shards (workflow grep not the source of truth for “which script runs where”)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Context for where tests run; none for this PR scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_22: [OUT_OF_SCOPE] `ship-pr.sh` Phase 2 stall-aware retry policy not in branch diff
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Track as follow-up PR / not applicable to judging Phase 1 code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Track in follow-up PR
  - From cursor-specialist-edge-cases-output.txt: Not applicable to judging Phase 1 code; track as separate follow-up PR. Implement Phase 2 when diagnostics justify policy changes.

---

### FINDING_23: [OUT_OF_SCOPE] NDJSON composition style in `audit-scan-run.sh` pre-exists new scan work
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: No change required for this review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

### FINDING_24: [OUT_OF_SCOPE] Reviewer-noted positives / confirmed-good behaviors (not actionable defects in this pass)
- **Reviewer(s)**: dyn-shell-robustness-output.txt, dyn-sidecar-integrity-output.txt, dyn-audit-scan-correctness-output.txt, dyn-test-coverage-output.txt
- **Concern**: Multiple reviewers recorded positives or confirmed existing robustness (timeouts around probes, `pipefail` isolation for `lsof|head`, `jq`-based encoding, basename/temp collision notes, audit aggregation fallbacks matching tests/docs, macOS Bash 3.2 compatibility in new fixture blocks).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-robustness-output.txt: Positives not tied to defects: `lsof` is wrapped with `timeout`/`gtimeout` when available and explicitly skipped otherwise (`scripts/lib-cursor-launcher-common.sh:200-217`); the subshell around `lsof|head` disables `pipefail` to avoid SIGPIPE clobbering the capture (`scripts/lib-cursor-launcher-common.sh:202-206`); `git status` / `git rebase --show-current-patch` use wall-clock wrappers or are omitted when no `timeout` exists (`scripts/lib-cursor-launcher-common.sh:265-286`); argv “full tree” probing uses `grep '[c]ursor'` and uid-scoped `ps` instead of a naive `ps -ef|grep cursor` (`scripts/lib-cursor-launcher-common.sh:192-197`), which is more robust on shared hosts.
  - From dyn-sidecar-integrity-output.txt: JSON assembly uses `jq` with `--arg` / `--argjson` / `--rawfile`, so `ps`, `lsof`, `git_state` strings, and `last_transcript_lines` (array of strings from `split("\n")`) are encoded as proper JSON values without manual string concatenation; invalid UTF-8 or other jq-hard failures drop the sidecar and append a `cursor-ci-stall-json: jq assembly failed` line to the diag file rather than writing truncated JSON (`scripts/lib-cursor-launcher-common.sh:295-333`).
  - From dyn-sidecar-integrity-output.txt: Basenames use `cursor-ci-stall-$(date +%s)-$$-${RANDOM}.json` plus `mktemp` for the staging file; with at most one stall emission per `cursor_launcher_run_stall_monitor` invocation before `return`, same-second collisions are not a practical concern (`scripts/lib-cursor-launcher-common.sh:288-333`, `scripts/lib-cursor-launcher-common.sh:453-504`).
  - From dyn-sidecar-integrity-output.txt: The `cursor-ci-stall-causes` audit scan treats non-`jq -e` parseable files as unparsed while still bucketing them as `UNKNOWN` in the histogram, so malformed sidecars do not silently skew parsed JSON aggregation (`.claude/skills/audit-runs/scripts/audit-scan-run.sh:354-380`, mirrored in `test-audit-runs.sh` around the `not json` fixture).
  - From dyn-audit-scan-correctness-output.txt: The aggregation loop in `audit-scan-run.sh:366-381` uses `shopt -s nullglob`, `jq -e .` for `parsed_files`, and a fallback `UNKNOWN` line per file when per-file `jq` fails; `channels_detail` mirrors `ns-retry-sidecars` when the histogram `jq` fails; this matches `test-audit-runs.sh:1269-1285` and the prose in `audit-scan-run.md:37`. The `expected_outcome` text in `scans.tsv:7` is descriptive (registry is not parsed for pass/fail semantics beyond human docs), and is consistent with emitting `result:"informational"` whenever any matching file exists.
  - From dyn-test-coverage-output.txt: Stall fixtures 7–8 use constructs compatible with macOS Bash 3.2 (`shopt -s nullglob`, `[[ ]]`, arithmetic `$(())`, `case`), with no obvious Bash 4-only features in the added blocks.

---

### FINDING_25: `channels_detail` histogram fallback path not covered by Test 35g
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Regression in UNKNOWN rollup or `channels_detail` emission could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture or injected failure to assert channels_detail when histogram jq fails.

---

Note on **FINDING_21**: the source slot only offered “Address the concern above,” which is not substantive fix direction; the bullet is included only because the instructions require verbatim text when present.

---

Because this output contains one or more `### FINDING_N:` blocks, the line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must **not** appear anywhere above.
