### FINDING_1: Design round timing guard is set before validation/write succeeds
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-bash32-compat-output.txt, dyn-interval-attachment-output.txt, dyn-handoff-telemetry-output.txt
- **Severity**: important
- **Concern**: `_emit_plan_round_timing_row` sets its one-shot guard before timestamp validation and before `record-plan-review-round-timing.sh` is confirmed to write a ledger row. A transient invalid timestamp or helper/ledger failure can permanently suppress retry for that round, silently dropping design round timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-bash32-compat-output.txt, dyn-interval-attachment-output.txt, dyn-handoff-telemetry-output.txt: Address the concern above.

### FINDING_2: Implement in-loop round timing bypasses deferred helper count/idempotency path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_emit_implement_round_timing_row` writes directly via `timing-ledger.sh record-round` using `IRF_LAST_*` counts, while deferred MAV paths use `record-implement-review-round-timing.sh` and re-tally into `review-tally.env`. Counts and idempotency behavior can diverge for the same round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Step 5 loop timing harness is referenced but untracked and not wired into CI
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-compat-output.txt
- **Severity**: important
- **Concern**: `test-review-implement-step5-loop-timing.sh` is referenced as contract coverage but is untracked/not committed and has no Makefile target or harness-shard registration. CI will not exercise Step 5 loop timing behavior despite the SKILL.md reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-compat-output.txt: Address the concern above.

### FINDING_4: Implement loop has many scattered timing emit call sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Numerous branches duplicate `_emit_implement_round_timing_row` calls. A future terminal/stall/continue branch can omit the emit call and silently drop per-round timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Deferred round-timing helper plumbing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Design and implement deferred timing helpers duplicate tmpdir, ledger, and idempotency plumbing, so future fixes may drift between the two paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: timing-report round sorting uses ad hoc O(n²) bubble sort
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `emit_round_array` uses a bubble sort for matched rounds, inconsistent with other renderer sorting patterns. This is not currently breaking but is avoidable maintenance debt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] run-log docs omit the new per-step rounds array
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `docs/run-logs.md` documents `timing-report.json` but does not describe the optional per-step `rounds` sub-array, so operators may not know committed timing JSON includes round-level detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Implement deferred-helper stall scenario lacks required test coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The committed deferred-helper tests do not cover a terminal stall where Step 5 is not re-invoked but still needs a deferred round row. A MAV/coder handoff stall after prompt-side work could miss timing without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: MAV/coder terminal-stall handoff timing prose is mechanically ambiguous
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-handoff-telemetry-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` tells the main agent to record deferred timing on terminal lint/check stalls, but the nearby executable block is primarily success-path and includes commit commands. An orchestrator could either skip timing on stall or execute a phantom commit before Step 16.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-handoff-telemetry-output.txt: Address the concern above.

### FINDING_10: Design converged terminal timing path lacks test assertion
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Zero-findings converged terminal exit uses the terminal snapshot path, but the test does not assert a plan round timing row. A regression removing this common terminal emission path would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Design pause publish path can publish stale or missing final timing JSON
- **Reviewer(s)**: dyn-artifact-publish-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` renders fresh `timing-report-final.json` before publishing, but `design-pause-save.sh` still calls `design-log-publish.sh` directly. A pause can therefore publish no final timing JSON or a stale pre-round artifact while the ledger already contains round rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-publish-output.txt: Address the concern above.

### FINDING_12: design-log-publish sidecar exclusions lack regression coverage
- **Reviewer(s)**: dyn-artifact-publish-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design_artifact_excluded` excludes `timing-report-final.stderr.log` and `.failure.log`, but `scripts/test-design-log-publish.sh` does not assert those sidecars are kept out of published run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-publish-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] design-publish mktemp failure artifact is self-deleted
- **Reviewer(s)**: dyn-artifact-publish-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The mktemp-failure path writes `timing-report-final.failure.log`, passes it to `append-tool-failure.sh`, then removes all `timing-report-final.*`. Publishing remains safe, but the create-use-delete pattern is fragile and leaves no artifact for later inspection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-publish-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Design per-round counts may use cumulative tally files
- **Reviewer(s)**: dyn-artifact-publish-output.txt
- **Severity**: latent
- **Concern**: `record-plan-review-round-timing.sh` derives accepted/rejected counts from session-root tally files rather than round-local snapshots, so multi-round JSON can attribute cumulative counts to individual rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-publish-output.txt: Address the concern above.

### FINDING_15: Implement grep-n fallback test does not assert accepted/rejected counts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The fallback-count test only asserts duration and does not verify the expected accepted/rejected fields. A broken grep-n fallback pattern could pass while producing wrong counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_16: MAV re-tally env key convention is assumed but not verified
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The deferred implement helper expects `ACCEPTED_COUNT`/`REJECTED_COUNT` keys in `review-tally.env`, but there is no direct test that `tally-code-votes.sh --review-tmpdir` writes those exact keys for MAV re-tally handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_17: Design round-start no-clobber behavior can preserve stale timestamps
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `_persist_plan_round_start` intentionally uses no-clobber semantics, but if a prior re-entry left a `round-start-s` for the same round number, duration can be inflated by preserving the stale start timestamp.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] timing-report emit_round_array relies on fragile global awk array cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-bash32-compat-output.txt, dyn-interval-attachment-output.txt
- **Severity**: latent
- **Concern**: `emit_round_array` uses global awk arrays for match/dedup state and depends on manual cleanup. Current behavior appears correct, but stale global state or future cleanup changes could corrupt per-step round attachment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-bash32-compat-output.txt, dyn-interval-attachment-output.txt: Address the concern above.

### FINDING_19: render-final-summary post-publish timing reuse branch lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `_SKIP_TIMING_REGATHER` branch for `--post-publish-only` with existing valid `timing-report-final.json` is untested, so regressions could silently omit timing duration or suppress failure reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_20: Implement in-loop guard verification can miss a written row and allow duplicates
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-handoff-telemetry-output.txt
- **Severity**: latent
- **Concern**: `_emit_implement_round_timing_row` only sets its guard after an awk probe matches the just-written row. If the row is written but the probe misses it due to visibility, path, sanitization, or exact timestamp matching, the guard remains unset and a later call can write a duplicate row with a different duration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-handoff-telemetry-output.txt: Address the concern above.

### FINDING_21: design-publish failed-render test does not assert failure.log cleanup
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The failed-render test checks that `.json` and `.stderr.log` are absent, but not `timing-report-final.failure.log`, despite the requirement to leave no top-level `timing-report-final.*` sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] record-plan OOS tally falls back to $NF for result
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `record-plan-review-round-timing.sh` falls back to `$NF` when the expected Result column is empty or dashed. If a generated table ever has extra trailing fields, OOS accepted/rejected counts could be wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] timing-report sidecar exclusions may look dead without context
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The design-publish/render-final-summary ordering means sidecar exclusions are defense-in-depth for pre-publish render paths, not always exercised by post-publish failure flow. Future reviewers might remove them as apparently dead without this context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] record-plan helper can resolve the implement ledger if IMPLEMENT_TMPDIR leaks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `record-plan-review-round-timing.sh` reportedly does not clear `IMPLEMENT_TMPDIR` before invoking `timing-ledger.sh`. If `LARCH_TIMING_LEDGER` is absent, ledger resolution may fall through to an implement ledger path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: record-plan OOS tally uses less-portable awk trim pattern
- **Reviewer(s)**: dyn-bash32-compat-output.txt
- **Severity**: latent
- **Concern**: The AWK trim uses alternation in a single `gsub` pattern. Although POSIX-compliant, reviewers flagged potential macOS awk edge cases that could leave whitespace and cause OOS counts to read as zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-compat-output.txt: Address the concern above.

### FINDING_26: timing-report interval test lacks negative assertion for orphan rounds
- **Reviewer(s)**: dyn-interval-attachment-output.txt
- **Severity**: nit
- **Concern**: The fixture verifies expected Step 5 round arrays but does not assert that an orphaned round attaches nowhere else. A future interval-only refactor could attach it to an unexpected step without failing the current assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-interval-attachment-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Design snapshot timing silently no-ops when round_start is empty
- **Reviewer(s)**: dyn-interval-attachment-output.txt
- **Severity**: latent
- **Concern**: `_emit_plan_round_timing_row` silently returns when `_round_start` is empty. The reviewer characterized this as a pre-existing structural risk inherited by new emission points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-interval-attachment-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] design publish render failure can log exit code 0 for invalid JSON
- **Reviewer(s)**: dyn-handoff-telemetry-output.txt
- **Severity**: latent
- **Concern**: If timing render succeeds but JSON validation fails, the failure path may log an effective exit code of `0` to `execution-issues.md`, making a render failure appear successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-telemetry-output.txt: Address the concern above.
