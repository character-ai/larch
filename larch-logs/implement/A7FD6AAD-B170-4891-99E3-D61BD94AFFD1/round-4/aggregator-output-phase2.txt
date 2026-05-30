Normalized aggregator output from the supplied reviewer slots (merged by shared behavioral risk; first-seen `FINDING_N` order).

### FINDING_1: Accidental `.tmp-debug-cf*.sh` scripts committed at repo root
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-hook-correctness-output.txt, dyn-debug-artifact-leak-output.txt
- **Severity**: important
- **Concern**: Four (or more) ad-hoc `.tmp-debug-cf*.sh` debug scripts are git-tracked at the repo root with hardcoded `/Users/zhupanov/larch4` (or similar operator-specific) absolute paths. They are outside the #3202 plan, not registered in the Makefile harness, ship with the full plugin tree, may be shellchecked or run by mistake, expose operator filesystem layout, and duplicate coverage that belongs in `test-collect-findings.sh` / `test-collect-agent-results.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Delete all .tmp-debug-cf*.sh; rely on Makefile harness tests only.
  - From cursor-specialist-correctness-output.txt: Delete all .tmp-debug-cf*.sh before merge.
  - From cursor-specialist-testing-output.txt: Remove all `.tmp-debug-cf*.sh` from the branch before merge.
  - From cursor-specialist-security-output.txt: Remove all four files before merge; gitignore .tmp-debug-* for local use.
  - From cursor-specialist-edge-cases-output.txt: Remove all four files before merge; add a gitignore rule for .tmp-debug-* if needed for future local debugging.
  - From cursor-specialist-plan-fidelity-output.txt: Remove all .tmp-debug-cf*.sh files; rely on test-collect-findings.sh
  - From dyn-bash-hook-correctness-output.txt: Delete all `.tmp-debug-cf*.sh` from the branch before merge; if any scenario still needs manual reproduction, fold it into `scripts/test-collect-findings.sh` or `scripts/test-collect-agent-results.sh` using repo-relative paths and the existing harness tempdir pattern.
  - From dyn-debug-artifact-leak-output.txt: Remove all four from the index and branch history before merge (`git rm` the paths; do not leave them in the PR). Add a repo-root ignore rule such as `.tmp-debug-*.sh` (or a broader `.tmp-*.sh` if consistent with existing harness conventions) so a repeat local debug session cannot be committed again. Rely on `skills/review/scripts/test-collect-findings.sh` and extended `scripts/test-collect-agent-results.sh` for regression coverage; do not relocate these scripts into `scripts/` without Makefile registration and portable `SCRIPT_DIR`/`REPO_ROOT` resolution.

### FINDING_2: Unrelated #3175 hook expansion bundled into #3202 PR
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Large `hook-anti-read-poll.sh` / AGENTS / orchestrator-never changes unrelated to stderr-tail surfacing are bundled in the same PR as #3202. That couples features, makes bisect and review harder, and increases regression risk for unrelated behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split hook/AGENTS/orchestrator-never changes to a separate PR or revert from this branch.

### FINDING_3: `collect-findings.sh` replay fallback omits collector §3.8 tail resolution / tee
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-hook-correctness-output.txt
- **Severity**: important
- **Concern**: When collector stderr capture is empty but failure tails exist on retry, NS-retry, or `.launch-stderr` paths (or collector stderr fails quietly), `replay_collector_failed_stderr_tails` only reads `${REVIEWER_FILE}.stderr-tail` and may show nothing, duplicate undeduped tails, or miss root cause versus the collector’s `_resolve_collector_stderr_tail_file` / tee path used on `/design`. This diverges from the planned tee pattern and acceptance criteria for surfacing failed-agent stderr on `/review`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use tee pattern like plan-review-loop.sh:757-762; remove or share collector tail resolver for any replay fallback.
  - From cursor-specialist-structure-output.txt: Prefer tee capture; drop replay or delegate to shared resolver + captured collector log.
  - From cursor-specialist-correctness-output.txt: Share `_resolve_collector_stderr_tail_file` with replay or always tee live collector stderr.
  - From cursor-specialist-edge-cases-output.txt: Factor shared tail resolution (`_resolve_collector_stderr_tail_file`) into the replay path.
  - From cursor-specialist-plan-fidelity-output.txt: Mirror §3.8 dedup in replay or use live tee per plan FINDING_3
  - From dyn-bash-hook-correctness-output.txt: Reuse the same resolver as the collector (factor `_resolve_collector_stderr_tail_file` into a shared lib or call it from both places) before replaying blocks to the wrapper FD.

### FINDING_4: Triplicate fenced-tail emit logic across lib, collector, collect-findings
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Fenced stderr-tail emit loops are duplicated in `lib-failed-agent-stderr-tail.sh`, `collect-agent-results.sh`, and `collect-findings.sh`. Sanitization, fence format, caps, and redaction can drift; future changes require triple maintenance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add shared lib emit helper (quiet vs raw); delete duplicate loops in collector and collect-findings.

### FINDING_5: Collector §3.8 dedup/resolve helpers inlined in large collector script
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: §3.8 stderr-tail dedup and resolve helpers live inline in a ~1580-line `collect-agent-results.sh`, mixing stderr-tail concerns with retry/validation logic and making the behavior harder to test and reason about.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract §3.8 helpers to lib-failed-agent-stderr-tail.sh or a collector-specific sourced module.

### FINDING_6: `lib-failed-agent-stderr-tail` contract disagrees with implementation and callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `lib-failed-agent-stderr-tail.md` claims a dependency-free lib with a single `>&2` emit path and that `emit_failed_agent_stderr_tail_raw` is only for `run-external-agent.sh`, but the implementation sources `lib-quiet`, uses multiple `>&2` paths, and `launch-claude-review.sh` also calls the raw emitter—misleading contributors and lint/quiet expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update contract to document lib-quiet coupling and emit variants, or narrow implementation to match doc.
  - From cursor-specialist-edge-cases-output.txt: Update contract to list launch-claude-review.sh as a caller.
  - From cursor-specialist-plan-fidelity-output.txt: Remove launch-claude-review emit call; update contract if needed

### FINDING_7: Extra redacted stdout tail block on FAILED in `run-external-agent.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Beyond planned additive stderr surfacing, FAILED handling may render an extra redacted stdout tail from `OUTPUT_FILE`, producing duplicate or confusing failure blocks (stdout snippet plus stderr tail) not in acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove extra render on OUTPUT_FILE unless explicitly desired; keep stderr-tail sidecar + emit only.

### FINDING_8: `launch-claude-review.sh` failure stderr routing and re-emit gaps under quiet init
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: On non-zero exit when a `.stderr-tail` sidecar exists, full subprocess stderr may skip `_larch_emit_redacted_subprocess_stderr`, contradicting additive full re-emit. Under `larch_quiet_init`, `emit_failed_agent_stderr_tail_raw` writes FD 2 only while validation/errors may go to quiet logs; combined with skipped re-emit, failures can be invisible in transcript/chat versus `.launch-stderr` waterfall capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Always re-emit redacted SUBPROCESS_STDERR via larch_err on failure; add fenced tail as extra output.
  - From cursor-specialist-correctness-output.txt: Emit tails via larch_err fence loop or larch_quiet_write_diagnostic_stream; remove emit_failed_agent_stderr_tail_raw from launch-claude-review.sh.
  - From cursor-specialist-edge-cases-output.txt: Use larch_err for tails when quiet is active or copy validation stderr into .launch-stderr.
  - From cursor-specialist-plan-fidelity-output.txt: Remove emit_failed_agent_stderr_tail_raw; keep write_failed_agent_stderr_tail plus existing larch_err re-emit

### FINDING_9: Aggressive stderr-tail signature normalization may over-dedup distinct failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Replacing all `[0-9]+` runs with `#` in tail signatures can collapse materially different failures (line numbers, HTTP status, exit codes) into one emitted tail plus suppression lines, hiding separate root causes in one batch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Tighten normalization or exempt certain STATUS values from signature dedup.
  - From cursor-specialist-edge-cases-output.txt: Tighten normalization or dedup on a stable error-class prefix instead of all digits.

### FINDING_10: Missing integration test for review-mode sidecar-first stderr source in `run-external-agent.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-required coverage that default review mode prefers `.sidecar` over `.diag`/output is absent from `test-run-external-agent.sh`; only unit tests `select_failed_agent_stderr_source`, so FAILED/TIMED_OUT branch preference can regress undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add an end-to-end `run-external-agent.sh` failure case with a populated `${OUTPUT}.sidecar` and assert `.stderr-tail`/FD2 fence content comes from the sidecar.
  - From cursor-specialist-plan-fidelity-output.txt: Add failure case with seeded .sidecar and assert tail content

### FINDING_11: No harness for invalid `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` env fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non-numeric `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` fallback to 30 lines is untested; under `set -u` or bad env, tail behavior could regress to empty/disabled tails without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=abc` yields 30 lines from a 40-line source.

### FINDING_12: Harness does not assert `.stderr-tail` written before `.done` on launcher failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `test-launch-claude-subprocess.sh` does not verify ordering between `${fail_out}.stderr-tail` and `${fail_out}.done`; reordering could let the collector observe `.done` without a tail sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add mtime/ordering assertion between `${fail_out}.stderr-tail` and `${fail_out}.done`.
  - From cursor-specialist-plan-fidelity-output.txt: Add ordering assertion or stub-based intermediate check

### FINDING_13: Plan-review collector stderr tee lacks behavioral tail visibility test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-plan-review-loop.sh` pins golden layout only; degraded `/design` collector failures might tee to `plan-review-collector.stderr` without fenced tails reaching orchestrator FD 2/4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub a failed collect with `.stderr-tail` sidecars and assert tee/captured stderr contains the fenced tail.

### FINDING_14: No test that `.stderr-tail` artifacts are published in design run logs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Without a publish harness case, regressions that re-exclude `*.stderr-tail` from cloned log trees would silently remove run-log recoverability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one publish harness case expecting `.stderr-tail` in the cloned log tree.

### FINDING_15: Published `*.stderr-tail` in `larch-logs/` without gitleaks backstop
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Publishable `.stderr-tail` artifacts can land in `larch-logs/` where gitleaks does not scan; `redact-secrets` has known non-coverage, so opaque secrets in stderr could be committed in public run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Exclude *.stderr-tail from publish or add publish-time re-redaction; treat larch-logs as sensitive regardless of redaction.

### FINDING_16: Success-path collector stderr replay/fanout skips `redact-secrets.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: On `collector_rc=0`, `replay_collector_failed_stderr_tails` / fanout may replay already-written `.stderr-tail` files using only `sanitize_diagnostic_line`, not `redact-secrets.sh` / `redact-tmpdir-paths.sh`, so tampered or stale unredacted tails in `REVIEW_TMPDIR` could reach FD 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pipe replay/fanout through redact-tmpdir-paths.sh and redact-secrets.sh for defense in depth.

### FINDING_17: `/review` execution-issues bundles omit `.stderr-tail` and `.launch-stderr`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `append_non_ok_collector_results_from_file` does not include stderr-tail or launch-stderr sections in persisted `execution-issues.md`, so inline failures may surface tails to FD 2 while published/review artifacts still lack them (repeat of #3119-style gap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reuse compose-collector-failure-log.sh or append the same tail/launcher sections when building review failure artifacts.

### FINDING_18: Claude launcher path does not clear stale `${OUTPUT}.stderr-tail` on success/relaunch
- **Reviewer(s)**: dyn-sidecar-lifecycle-output.txt
- **Severity**: important
- **Concern**: `launch-claude-subprocess.sh` / `launch-claude-review.sh` do not remove `.stderr-tail` before run or after successful exit unlike `run-external-agent.sh`. Reusing the same output after a prior failure can leave a stale sidecar while sentinel/collector show `STATUS=OK`; replay and `design-log-publish.sh` can still pick up the stale artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sidecar-lifecycle-output.txt: Mirror `run-external-agent.sh`: `rm -f "${OUTPUT_CANON}.stderr-tail"` at subprocess entry and on exit 0 (or call `write_failed_agent_stderr_tail` with an empty/disabled source so the library removes the sidecar).

### FINDING_19: NS-retry success leaves `${ORIG}-ns-retry.txt.stderr-tail` on disk
- **Reviewer(s)**: dyn-sidecar-lifecycle-output.txt
- **Severity**: important
- **Concern**: On NS-retry OK, cleanup only removes `${ORIG_OUTPUT}.stderr-tail` while tails were written against `NS_RETRY_OUTPUT`; recovered slots can retain misleading failure sidecars beside `STATUS=OK`, including under `larch-logs/` publish paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sidecar-lifecycle-output.txt: On every NS-retry OK path, also `rm -f "${NS_RETRY_OUTPUT}.stderr-tail"` (and any `*-retry.txt.stderr-tail` tied to that slot if present).

### FINDING_20: Stale phase-level `.launch-stderr` surfaced by collector resolution
- **Reviewer(s)**: dyn-sidecar-lifecycle-output.txt
- **Severity**: important
- **Concern**: `.launch-stderr` sidecars persist across waterfall phases without explicit lifecycle cleanup; `_resolve_collector_stderr_tail_file` can walk ancestors and show superseded launcher errors when the failing phase has no current tail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sidecar-lifecycle-output.txt: Either limit on-demand `.launch-stderr` resolution to the primary `REVIEWER_FILE` only (keep phase fallback for `.stderr-tail` if desired), or `rm -f` prior-phase `*.launch-stderr` when advancing the waterfall / at `launch_slot` for non-first phases so only the active phase stem can contribute launcher stderr.

### FINDING_21: `hook-anti-read-poll.sh` shared `nosession` bucket cross-session bleed
- **Reviewer(s)**: dyn-bash-hook-correctness-output.txt
- **Severity**: important
- **Concern**: When `session_id` / `conversation_id` are absent, all callers share the literal `nosession` state bucket; concurrent sessions polling the same `tasks/<id>.output` under the same `cwd` can false-trigger or suppress reminders.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-hook-correctness-output.txt: Fold a per-process discriminator into the fallback key when metadata is missing (e.g. `PPID`, a hook-supplied env var, or a small nonce written once per hook parent), and add a harness case that two synthetic “nosession” streams with different discriminators do not share `state-taskout-*` files.

### FINDING_22: `hook-anti-read-poll.sh` non-atomic state read-modify-write
- **Reviewer(s)**: dyn-bash-hook-correctness-output.txt
- **Severity**: important
- **Concern**: PostToolUse state updates use non-atomic TSV read/increment/overwrite without `flock`; concurrent hook invocations can drop counts or corrupt path/offset fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-hook-correctness-output.txt: Wrap each update in `flock -x "$state_file"` (or write via a temp file + `mv` after `flock` on a per-bucket lock file); extend `scripts/test-hook-anti-read-poll.sh` with a simulated concurrent double-invoke if feasible.

### FINDING_23: `hook-anti-read-poll.sh` quote stripping misses Bash `'\''` encoding
- **Reviewer(s)**: dyn-bash-hook-correctness-output.txt
- **Severity**: important
- **Concern**: `bash_strip_quoted_for_read_verb` uses `sed` that does not handle Bash single-quote escapes, so poll detection can false-positive/negative on split quoted paths; harness only covers simple quoted paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-hook-correctness-output.txt: Either document and test the limitation explicitly, or replace the sed stripper with a small character-wise state machine (or only extract tokens from segments already known to contain a read verb after a dedicated quote-aware scan).

### FINDING_24: `hook-anti-read-poll.sh` `||`/`&&` segment splitting ignores shell precedence
- **Reviewer(s)**: dyn-bash-hook-correctness-output.txt
- **Severity**: important
- **Concern**: Heuristic splitting on `;`, `&&`, `||` left-to-right without Bash precedence can attach poll detection to the wrong segment or miss `tasks/…output` reads in compound one-liners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-hook-correctness-output.txt: Prefer detecting poll only on segments that both contain a read verb and a `tasks/<id>.output` token after strip (already mostly true), and add harness cases for mixed `||`/`&&` chains that match real orchestrator patterns; long term, only split on `;` (statement boundaries) unless you implement precedence-aware parsing.

### FINDING_25: [OUT_OF_SCOPE] Unrelated hook / AGENTS expansion increases #3202 PR scope
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Large `hook-anti-read-poll.sh` (and related) changes beyond stderr-tail surfacing are bundled on the branch, increasing review scope and coupling beyond the #3202 plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Split to a separate PR or document explicit bundling rationale.
  - From cursor-specialist-plan-fidelity-output.txt: Split to separate PR or document intentional bundle

### FINDING_26: [OUT_OF_SCOPE] `compose-collector-failure-log.sh` stderr-tail extension not in plan file list
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Collector failure log was extended for stderr-tail and launch-stderr sections; acceptable bonus work but not listed in the plan file list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Note in PR body or add to plan if intentional

### FINDING_27: [OUT_OF_SCOPE] Design plan-review collector stderr tee added outside plan file list
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `plan-review-loop.sh` collector stderr tee supports design-path visibility but was not in the plan file list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document as follow-on to #3202 design-path parity

### FINDING_28: [OUT_OF_SCOPE] Generic Read polling still keys only on `cwd_hash` (pre-existing)
- **Reviewer(s)**: dyn-bash-hook-correctness-output.txt
- **Severity**: latent
- **Concern**: Generic Read polling in `hook-anti-read-poll.sh` uses `state-<cwd_hash>.tsv` without `session_hash`, so unrelated sessions in the same project directory can cross-talk; predates this branch’s task-output work.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_29: [OUT_OF_SCOPE] No `.gitignore` pattern for `.tmp-debug-*` scratch scripts
- **Reviewer(s)**: dyn-debug-artifact-leak-output.txt
- **Severity**: latent
- **Concern**: Pre-existing gap amplified by this branch: repo lacks ignore rules for `.tmp-debug-*` or generic repo-root `.tmp-*` scratch scripts, so local debug files can be committed again after removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-debug-artifact-leak-output.txt: Adding an ignore rule after removing the committed files would close the gap for future local debugging.

---

**Notes (aggregator only, not findings):** Positive scout / “looks sound” `[OUT_OF_SCOPE]` inputs (dyn-sidecar lifecycle 42–44; dyn-bash 52–54, 57) were not promoted to finding blocks because they assert no defect or acceptable behavior rather than a fixable risk. Input slots that only said “Address the concern above” for merged topics are omitted where a sibling slot supplied verbatim fix text for the same merged concern.
