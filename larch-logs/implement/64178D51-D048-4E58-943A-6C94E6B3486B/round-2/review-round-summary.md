# Review Round 2

- Mode: `diff`
- 8 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: plan-review domain still runs via gzip-embedded legacy bash shim
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-plan-cli-contracts-output.txt, dyn-retired-path-sweep-output.txt, dyn-artifact-security-output.txt
- **Severity**: important
- **Concern**: C3a1 advertises a true Python port with no shims, but `python/plan_review.py` and `python/plan_review_panel.py` still embed deleted bash as gzip assets, materialize them into a synthetic temp plugin root via `_materialize_legacy_root()` / `_run_legacy()`, and shell out for loop, panel, voter dispatch, tally, emit/finalize/preview, and most other verbs. Runtime behavior is therefore hidden from normal review, grep, and `make lint-retired-scripts` (retired path literals in `_LEGACY_ASSETS` fail the sweep). Frozen embedded copies can drift from live helpers they symlink against. Publication-boundary logic moved to Python (`round_artifact_*`), but snapshot/tally/evidence staging still runs in embedded shell, so snapshot vs publish allowlists can diverge without repo-visible changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement loop/tally/panel/voter logic in Python per plan, or re-scope the migration if embedded bash is intentional.
  - From cursor-specialist-edge-cases-output.txt: Complete the in-process port or document delegation like C1b and keep inspectable shell under python/legacy_design_shell/ instead of embedded blobs
  - From codex-generic-output.txt: Replace the embedded assets and `_run_legacy` wrappers with real Python implementations, or keep the Bash scripts tracked and do not mark them retired.
  - From dyn-plan-cli-contracts-output.txt: Either finish the native port (so `run_step3_review`, tally, persist/rollback, and Gate B dedup are real Python with tests), or add an explicit regression layer that exercises `plan-review run --mode loop` for cap persist/rollback, `tally-error`, `degraded-empty-collector`, `main-agent-vote-required`, `postplan-operator-required`, and `gate-b-dedup` restore against the live CLI path.
  - From dyn-retired-path-sweep-output.txt: Complete the native Python implementations (or add an explicit, narrowly scoped lint exemption with a tracked follow-up), then remove `_LEGACY_ASSETS` / `_run_legacy` and the retired-path string literals so `lint retired-scripts` passes cleanly.
  - From dyn-retired-path-sweep-output.txt: Port loop, panel dispatch, voter dispatch, tally, emit/finalize/preview, and step3-state into native Python (calling migrated surfaces in-process), then delete `_LEGACY_ASSETS` and `run_legacy_script`.
  - From dyn-artifact-security-output.txt: Finish the native port and delete `_materialize_legacy_root`; until then, route snapshot allowlist checks through the same Python functions as publish (or add CI that decodes embedded assets and asserts byte parity with `round_artifact_*` tests).


### FINDING_10: Step 3 escalation capture logs may be published to committed run logs
- **Reviewer(s)**: dyn-artifact-security-output.txt
- **Severity**: important
- **Concern**: `step3_record_report_evidence()` correctly validates `design-tmpdir` and rejects symlinked tmpdirs, but still writes `step3-record-escalation-${status}.stdout.log` / `.stderr.log` at the session tmpdir root. Those basenames are not listed in `design_artifact_excluded()` in `scripts/design-log-publish.sh`, so verbose or failed `stall-recovery-report.sh` captures can be staged into committed `larch-logs/design/<RUN_ID>/` on publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-security-output.txt: Add `step3-record-escalation-*.stdout.log` / `step3-record-escalation-*.stderr.log` (and optionally `design-failure-escalation-*.tsv`) to `design_artifact_excluded()`, or relocate captures under an already-excluded prefix.


### FINDING_2: Deleted shell harnesses replaced by thin pytest with major behavioral gaps
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-plan-cli-contracts-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Large deleted shell harnesses (`test-plan-review-loop.sh`, `test-run-step3-review.sh`, `test-dispatch-plan-voters.sh`, etc.) were retargeted in the Makefile to `python/test_plan_review.py` (and a thin `python/test_plan_review_panel.py`), but those modules mostly smoke-test CLI usage. Plan-required scenarios are missing: cap behavior, `review-round-count.txt` persist-before-launch/rollback, terminal `LOOP_STATUS` / `STEP3_REVIEW_LOOP_STATUS` matrix, Gate B dedup restore, panel vendor matrix, parse-rate retry, retally env refresh, and round snapshot/timing idempotency. CI can pass while regressions in embedded bash logic go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port high-risk harness scenarios into pytest with injectable subprocess seams or retain focused shell harnesses until parity exists
  - From cursor-specialist-testing-output.txt: Port plan-listed cases from deleted harnesses into pytest with injectable subprocess seams, or retain bash harnesses until parity exists
  - From dyn-plan-cli-contracts-output.txt: Port the retired harness scenarios into `python/test_plan_review.py` (or a dedicated integration module) before deleting the last behavioral references, so CI still pins the env/KV contracts the wrappers parse.
  - From dyn-retired-path-sweep-output.txt: Port the high-value harness scenarios into `python/test_plan_review.py` and `python/test_plan_review_panel.py` (stub subprocess seams where needed) before relying on the thin pytest layer as the sole regression gate.


### FINDING_3: No automated test for degraded-empty-collector review-round-count rollback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-step3-review-cap.sh` tests `tally-error` rollback but has no case for `LOOP_STATUS=degraded-empty-collector`. A regression that only breaks degraded-empty rollback lets the counter advance and can violate Step 3 cap semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a cap-harness or pytest case with LOOP_STATUS=degraded-empty-collector asserting the prior round count is restored


### FINDING_6: Step 3 preview wrapper validates `DESIGN_TMPDIR` after sentinel touch
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step3-entry-preview.sh` checks and writes `.step3-entry-plan-printed` before validating `DESIGN_TMPDIR`. A disallowed existing directory with that sentinel can exit 0 silently instead of emitting the allowlist warning described in `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Validate and canonicalize `DESIGN_TMPDIR` before any sentinel read or touch, or move sentinel ownership into `plan-review preview --variant step3` using `validate_design_tmpdir`.


### FINDING_7: `test-step3-orchestrator-fence.sh` no longer exercises real Step 3 launcher
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: The harness stubs `run-step3-review.sh` under a fake `CLAUDE_PLUGIN_ROOT`, but `design-step3-review.sh` now launches `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run`. The fake plugin tree has no `python/cli.py`, so the wrapper exits 2 and handoff tests never exercise the real launcher path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Update `invoke_step3_review_wrapper` to point `CLAUDE_PLUGIN_ROOT` at the real repo (or symlink/copy `python/cli.py` into the fake plugin) and stub the loop via the existing `LARCH_PLAN_REVIEW_*` / subprocess override hooks used by `scripts/test-design-multi-round-integration.sh`, instead of stubbing the deleted `run-step3-review.sh`.


### FINDING_8: Drift-baseline has divergent strict vs loose write paths
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: `plan-review drift-baseline write-once` uses `validate_design_tmpdir`, rejects non-numeric line counts, and refuses symlinked baseline files, while `plan_quality._drift_baseline_write_once` seeds the same `drift-baseline.env` without those checks. `design-postplan-emit.sh` calls the stricter CLI path with `|| true`, so a failed CLI write can be silently ignored while `plan check-size` may still seed via the looser internal writer, weakening drift detection on Step 2b post-plan emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Route both call sites through one shared writer (either move allowlist/validation into `plan_quality._drift_baseline_write_once` and call it from the CLI, or have `plan check-size` invoke `plan-review drift-baseline write-once`), and fail loudly in `design-postplan-emit.sh` when snapshot-original cannot write the baseline.


### FINDING_9: Multiple operator docs still reference retired plan-review shell scripts
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Post-cutover runtime goes through `python/cli.py plan-review` and design wrappers, but several normative docs still name deleted scripts (`run-step3-review.sh`, `plan-review-loop.sh`, `dispatch-plan-voters.sh`, `emit-design-plan-preview.sh`, `lib-design-round-artifacts.sh`). Operators, security reviewers, and agents following these docs will invoke missing paths or wrong relay surfaces. Affected surfaces include `SECURITY.md`, `docs/configuration-and-permissions.md`, `skills/design/SKILL.md`, `skills/design/references/approval-gates.md`, `skills/shared/voting-protocol.md`, and `scripts/design-log-publish.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Update the relay-surface list to `python/plan_review.py` / `python/cli.py plan-review run`, `.step3-review-result.env`, and `design-step3-review.sh` stdout, matching the post-cutover wiring.
  - From dyn-retired-path-sweep-output.txt: Replace line 316 with the actual fence sequence (`design-step3-entry-preview.sh` / `design-step4b-preview.sh` → `plan-review preview --variant step3|gatec`) and drop retired script names.
  - From dyn-retired-path-sweep-output.txt: Retarget contract references to `python/plan_review.py`, `python/test_plan_review.py`, `skills/design/scripts/test-design-step3-review.sh`, and `plan-review preview --variant gatec`; remove retired `.md`/`.sh` names from the agent-lint pin block.
  - From dyn-retired-path-sweep-output.txt: Change the mandatory block to `plan-review preview --variant gatec` (via `design-step4b-preview.sh`) and align wording with `design-step4b-preview.sh`.
  - From dyn-retired-path-sweep-output.txt: Update `/design` plan-review voter sections to `python/cli.py plan-review voter-dispatch` and `python/plan_review_panel.py`, keeping `dispatch-code-voters.sh` references only for `/review`.
  - From dyn-retired-path-sweep-output.txt: Replace the sync list with `python/plan_review.py`, `python/test_plan_review.py`, `scripts/design-log-publish.sh`, and this doc; drop retired script names.


