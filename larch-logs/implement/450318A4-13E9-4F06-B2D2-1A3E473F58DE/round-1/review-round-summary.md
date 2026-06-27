# Review Round 1

- Mode: `diff`
- 4 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Phase-3 prompt-missing slots get synthetic Claude outputs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generalist-output.txt
- **Severity**: important
- **Concern**: Indices dropped for missing `prompt_files[claude]` are merged into `phase3_failed`, but the terminal cleanup loop still assigns phase-3 Claude `final_outputs` / `final_tools` and may list never-launched paths in `ALL_OUTPUT_FILES` while `_write_drops` skips slots with non-empty `final_outputs`. Callers can bind a missing `*-phase3.txt` as a real Claude voter result instead of recording a `prompt-missing` drop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Exclude prompt-missing indices from phase3_failed or skip them in the phase-3 failure cleanup so final_outputs stays empty and drops are recorded.
  - From cursor-specialist-edge-cases-output.txt: Exclude prompt-missing indices from the phase-3 failure loop; keep final_outputs empty and record the drop in dropped-slots; do not call collect-results for those indices.
  - From codex-generalist-output.txt: Track `phase3_missing_prompt` separately from launched phase-3 failures. Preserve the drop reason, but do not populate `final_outputs` / `final_tools` or include those paths in `ALL_OUTPUT_FILES` / paths files.


### FINDING_2: Design tmpdir log-root resolver can read plugin larch-logs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-calibration-corpus-output.txt, dyn-dyn-prompt-feedback-output.txt
- **Severity**: important
- **Concern**: The inlined `design_tmpdir` branch in `_resolve_voter_calibration_log_root` does not match `design_lifecycle._resolve_working_tree_root`: it omits `REPO_ROOT` from the environment, `session write-design-env` does not persist a filesystem repo root into `source-env.sh`, and when `LARCH_CONSUMER_REPO` / `CLAUDE_PROJECT_DIR` are unset the resolver falls back to `git rev-parse --show-toplevel` from the plugin subprocess cwd. Plan-review snapshot dispatch can therefore read the plugin checkout’s `larch-logs` instead of the consumer repo corpus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Match design_lifecycle._resolve_working_tree_root precedence including env REPO_ROOT or share one helper.
  - From codex-specialist-correctness-output.txt: Call design_lifecycle._resolve_working_tree_root(design_tmpdir) or honor REPO_ROOT before any git fallback.
  - From cursor-specialist-edge-cases-output.txt: Reuse the full design_lifecycle resolver (including REPO_ROOT env) via a shared helper without cyclic imports.
  - From codex-specialist-edge-cases-output.txt: Delegate the design-tmpdir branch to design_lifecycle._resolve_working_tree_root or add REPO_ROOT handling before cwd-based fallback, and skip calibration if no consumer repo root is resolvable
  - From dyn-dyn-calibration-corpus-output.txt: Restore full `design_lifecycle._resolve_working_tree_root` semantics in the inlined block (including `REPO_ROOT` env), or break the import cycle and call the shared helper; also persist a filesystem repo root into design `source-env.sh` (e.g. `REPO_ROOT` or `CLAUDE_PROJECT_DIR`) during Step 0 so design dispatch does not depend on plugin-cwd `git rev-parse`.
  - From dyn-dyn-prompt-feedback-output.txt: Drop the cwd/git fallback for the `design_tmpdir` branch; resolve only from `source-env.sh` `REPO_ROOT` (and other design-session anchors), then continue to later precedence steps or return no snapshot rather than using plugin cwd.


### FINDING_3: Plan-mandated integration test coverage is largely absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dyn-calibration-corpus-output.txt, dyn-dyn-waterfall-prompts-output.txt, dyn-dyn-prompt-feedback-output.txt
- **Severity**: important
- **Concern**: The plan’s harness cases for snapshot dispatch, consumer log-root resolution, `prompt_files` manifests, waterfall relaunch per-tool prompt selection, replay feedback disable, and render/snapshot failure paths are mostly missing across `test_plan_review_panel.py`, `test_calibration_replay.py`, `test_voting.py`, `test_agent_waterfall.py`, `test_agent_voters.py`, and `test_rendering.py`. Consumer corpus mis-resolution, wrong per-tool prompts, or silent calibration injection during replay can ship without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the plan’s harness cases to the listed test modules.
  - From cursor-specialist-testing-output.txt: Extend test_plan_review_panel.py dispatch_voters integration tests per the plan checklist.
  - From cursor-specialist-testing-output.txt: Add a test asserting dispatch env pins feedback off and does not call voter-calibration snapshot.
  - From cursor-specialist-testing-output.txt: Add tests for _resolve_voter_calibration_log_root precedence implement keepalive/session-env paths env window and voter-calibration snapshot CLI output.
  - From cursor-specialist-testing-output.txt: Add dispatch_waterfall integration tests for per-phase prompt selection and prompt-missing slot drops.
  - From cursor-specialist-testing-output.txt: Extend test_agent_voters harness to assert snapshot invocation consumer log-root prompt_files NDJSON and failure paths.
  - From codex-specialist-testing-output.txt: Prefer the implement tmpdir anchor chain first, ideally by delegating to final_report._implement_repo_root(implement_tmpdir), and only fall back to the review tmpdir keepalive if that fails.
  - From dyn-dyn-calibration-corpus-output.txt: Add the planned `test_voting.py` cases (and dispatch integration tests in `test_agent_voters.py` / `test_plan_review_panel.py`) that assert `_resolve_voter_calibration_log_root` and snapshot argv `--log-root` target the consumer tree when the plugin subprocess cwd is the plugin checkout.
  - From dyn-dyn-waterfall-prompts-output.txt: Add harness tests that build `prompt_files` manifests with distinct per-tool prompt paths (e.g. codex vs cursor vs claude content markers), force phase-1 failure, and assert the stub launch argv’s `--prompt-file` matches the executing tool; add a case where a missing map entry yields `prompt-missing` drop, not launch without a prompt.
  - From dyn-dyn-prompt-feedback-output.txt: Add the planned waterfall relaunch test (phase-2 Cursor launch must use the cursor-specific prompt file) and consider aligning `_launch_slot` with drop semantics instead of raise when `prompt_files` is present but the launch-tool entry is missing.
  - From dyn-dyn-prompt-feedback-output.txt: Add the missing `render voter` cases from the plan (missing file exits 0 with unchanged output; bad header omits block; zero valid severities omits block).
  - From dyn-dyn-prompt-feedback-output.txt: Add the harness cases from the plan asserting resolved `--log-root` points at consumer `larch-logs` when plugin cwd differs and env anchors are unset.


### FINDING_8: Review-session corpus resolution prefers nested review keepalive over implement anchor
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_implement_repo_root_from_review_tmpdir` checks the review tmpdir `.larch-keepalive` before the implement tmpdir anchor chain. A nested review tmpdir with its own keepalive can steer the calibration snapshot to the wrong `larch-logs` corpus, so voter feedback comes from an unrelated consumer repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Prefer the implement tmpdir anchor chain first, ideally by delegating to final_report._implement_repo_root(implement_tmpdir), and only fall back to the review tmpdir keepalive if that fails.


