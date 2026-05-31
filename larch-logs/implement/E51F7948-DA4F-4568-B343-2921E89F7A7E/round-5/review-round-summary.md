# Review Round 5

- Mode: `diff`
- 11 accepted, 1 rejected (1 exonerated)

## Accepted Findings

### FINDING_1: Both-absent generic Claude marks dispatch OK without validated TSV sidecar
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: When Codex and Cursor are both absent, `dispatch-plan-review-panel.sh` generic Claude floor can set `DISPATCH_OK=true` and collect a path in `PANEL_PATHS_FILE` even if the first-line `schema_version`/JSONL pattern fails, `validate-research-output.sh` fails, or only prose is returned—so long as output is non-empty. The loop treats dispatch as OK while tally/voters lack a parseable structured `.tsv` sidecar and may degrade silently with weak findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_13: STATIC/DYNAMIC_DISPATCH_OK not cleared for phase-1 drops under --no-fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Under `--no-fallback`, `dispatch-with-waterfall.sh` does not set `STATIC_DISPATCH_OK`/`DYNAMIC_DISPATCH_OK` false for phase-1 failed slots. Callers may read `STATIC_DISPATCH_OK=true` while half the manifest failed and skip degraded handling that path-file ratio would imply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After no-fallback phase-1 collect, set static/dynamic flags false for failed/absent slot indices.


### FINDING_14: Inconsistent both-absent generic success semantics (plan-review vs decompose)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Same degraded Step 0 matrix: plan-review can proceed with `DISPATCH_OK=true` on bad structure while decompose marks panel-failed. Generic-floor validation and `DISPATCH_OK` rules should be unified across `dispatch-plan-review-panel.sh` and `decompose-panel-dispatch.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Unify generic-floor validation and DISPATCH_OK rules across both scripts.


### FINDING_15: Plan voters ignore waterfall retry sidecar paths (regression)
- **Reviewer(s)**: dyn-voter-dispatch-data-flow-output.txt
- **Severity**: important
- **Concern**: `dispatch-plan-voters.sh` no longer parses `ALL_OUTPUT_FILES`/`ALL_OUTPUT_TOOLS` and always uses fixed manifest paths. `collect_phase` can leave substantive output only at `<manifest>-retry.txt` while the slot is OK; pre-parse-rate `[[ -s "$VOTER_2_PATH" ]]` / `[[ -s "$VOTER_3_PATH" ]]` then marks failed and skips parse-rate retry—dropping a valid external judge vs `dispatch-code-voters.sh`, which still binds from `ALL_OUTPUT_FILES`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-dispatch-data-flow-output.txt: After the waterfall call, parse `ALL_OUTPUT_FILES` paired with `ALL_OUTPUT_TOOLS` and map by tool (`codex` → `VOTER_2_PATH`, `cursor` → `VOTER_3_PATH`), not by positional index; use the manifest paths only as defaults when a tool has no waterfall entry. Keep the availability-gated manifest emission and run the `-s` / parse-rate checks on the resolved final path.


### FINDING_2: Duplicate ALL_OUTPUT_FILES branches in dispatch-with-waterfall
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/dispatch-with-waterfall.sh` (~445–453) builds `ALL_OUTPUT_FILES` with identical if/else branches; only `--no-fallback` differs by skipping empty entries. Maintainers may assume the paths diverge and edit one branch only, inviting regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_20: Missing partial two-slot --no-fallback harness case
- **Reviewer(s)**: dyn-no-fallback-sentinel-timing-output.txt
- **Severity**: latent
- **Concern**: `test-dispatch-with-waterfall.sh` covers all-fail, all-ok single-slot, and tool-absent empty paths-file, but not multiple manifest slots with one phase-1 success and one phase-1 failure under `--no-fallback`. Writing every manifest `output` into `.output-files` (including failed slots without `.done`) could reintroduce ~timeout-per-slot stalls; only a partial case catches that.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-no-fallback-sentinel-timing-output.txt: Add a two-slot manifest where one stub succeeds and one fails, assert the paths-file has exactly one line (the OK path), run real `collect-agent-results.sh --paths-file` with a short `--timeout`, and assert no `STATUS=SENTINEL_TIMEOUT`.


### FINDING_4: Decompose both-absent generic launch omits Opus model flag
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `decompose-panel-dispatch.sh` generic `launch-claude-review.sh` when both vendors are absent does not pass `--model claude-opus-4-7`, unlike the plan-review generic floor—uneven model/cost/quality on the same matrix row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Pass `--model claude-opus-4-7` on `launch-claude-review.sh` to match `dispatch-plan-review-panel.sh`.


### FINDING_5: No end-to-end plan-review-loop test for both externals absent
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-plan-review-loop.sh` lacks an e2e case for Codex/Cursor both absent (generic Claude floor). Regressions in loop collect/tally/voter wiring on that path would not fail CI while panel-level both-absent tests could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a `run_loop` fixture with `--codex-present false --cursor-present false`, stub `launch-claude-review.sh` with `.done` and structured sidecar; assert no `SENTINEL_TIMEOUT`, non-panel-failed status, and expected tally outcome.


### FINDING_6: Empty-path dispatch stub omits ALL_SLOTS_DROPPED=true
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The empty-path dispatch stub does not emit `ALL_SLOTS_DROPPED=true` as real `--no-fallback` waterfall does. `plan-review-loop.sh` treats `ALL_SLOTS_DROPPED` distinctly from `DEGRADED_ROUND`; a KV-handling regression could pass the stub only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Emit `ALL_SLOTS_DROPPED=true` in a dedicated stub case and assert loop proceeds to skipped-empty-findings without panel-failed.


### FINDING_7: Hard <4s wall-clock timing assertions in test-dispatch-with-waterfall
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-no-fallback-sentinel-timing-output.txt
- **Severity**: latent
- **Concern**: New `--no-fallback` tests use `date +%s` deltas with a hard `< 4` second ceiling while `--timeout` is 5. Loaded CI or slow collect/retry paths can flake above 4s on correct runs; a near-5s regression might still pass. Structural checks already assert absence of `SENTINEL_TIMEOUT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert no `SENTINEL_TIMEOUT` without tight elapsed bounds, or stub poll intervals and use a generous margin.
  - From dyn-no-fallback-sentinel-timing-output.txt: Drop the `_elapsed` / `_collect_*_elapsed` comparisons and rely on structural assertions (no `SENTINEL_TIMEOUT`, empty vs non-empty paths-file, expected paths-file lines). If a duration guard is still desired, gate on `WAIT_FOR_REVIEWERS_POLL_INTERVAL` being unset or use a much looser bound, or stub/instrument `wait-for-reviewers.sh` to fail if invoked when the paths-file is empty.


### FINDING_8: No test for codex/cursor binary-found exports in write-design-current-env
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-write-design-current-env.sh` does not cover new `--codex-binary-found` / `--cursor-binary-found` exports; session rehydration could drop flags without failing the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend `test-write-design-current-env` to pass and source-assert `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND`.


