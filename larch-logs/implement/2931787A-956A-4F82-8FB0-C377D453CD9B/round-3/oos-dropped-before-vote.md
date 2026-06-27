### OOS_1: [OUT_OF_SCOPE] `repo_root` resolved before external noop short-circuit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-step4-composite-output.txt, dyn-dyn-dispatch-telemetry-output.txt
- **Severity**: latent
- **Concern**: For `--commit-site step4`, `checks_commit_route_main` resolves `repo_root` (and may run recovery recompute) before `_run_step4_commit_leg` can noop on external `MANIFEST_PATH` runs. A `git rev-parse --show-toplevel` failure aborts the whole composite even when only checks, dispatcher-committed skip, and folded `4.r` are needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Short-circuit noop before repo_root-dependent legs if optimizing
  - From dyn-dyn-step4-composite-output.txt: Short-circuit to `_run_step4_commit_leg` first when `MANIFEST_PATH` is set and readable; defer `repo_root` resolution until recovery recompute or a non-noop commit is actually needed.

### OOS_2: [OUT_OF_SCOPE] Step 4 external noop accepts non-empty `MANIFEST_PATH` without readability check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-step4-composite-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: latent
- **Concern**: `_run_step4_commit_leg` treats any non-empty `MANIFEST_PATH` in `ship-seed-input.env` as proof the dispatcher committed, without verifying the path is a readable manifest file. A stale or placeholder value can skip `implement commit` while Claude-fallback work remains uncommitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Verify manifest path readable before noop
  - From dyn-dyn-step4-composite-output.txt: Require `Path(manifest_path).is_file()` and non-zero size before noop.
  - From dyn-dyn-skill-wires-output.txt: Step 4 external noop treats any non-empty `MANIFEST_PATH` in `ship-seed-input.env` as proof the dispatcher committed, without checking readability. Post-dispatch seeding is stricter (`is_file()`), so a stale placeholder can skip `implement commit` on a Claude-fallback run that still needs one.

### OOS_3: [OUT_OF_SCOPE] Duplicate routing sections; missing unified input-source note
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `rebase-checkpoint-routing.md` still has two near-duplicate routing sections (`absorbed 1.r` vs folded `4.r/7.r/7a.r`) and no dedicated input-source note. Plan acceptance called for one shared table; drift may reintroduce parse divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Merge to one table plus input-source note per plan acceptance
  - From cursor-specialist-edge-cases-output.txt: Promote one shared routing table with an input-source column/note per checkpoint prefix

### OOS_4: [OUT_OF_SCOPE] Recovery recompute `derive_pathspec` failure lacks dedicated bail token
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-step4-composite-output.txt, dyn-dyn-dispatch-telemetry-output.txt
- **Severity**: nit
- **Concern**: When `_derive_pathspec_via_recovery_paths` fails inside `_run_step4_recovery_recompute` (postlaunch capture or `recovery-paths` error), the composite returns bare exit 1 with no `BAIL_REASON` or `NEXT_ACTION`, giving weaker routing signal than the `recovery-out-of-scope` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit a dedicated BAIL_REASON (or NEXT_ACTION=stall) when _derive_pathspec_via_recovery_paths fails inside the composite
  - From dyn-dyn-step4-composite-output.txt: Emit a dedicated bail token (for example `BAIL_REASON=recovery-pathspec-failed`) before returning non-zero from the derive failure branch.
  - From dyn-dyn-dispatch-telemetry-output.txt: When `_run_step4_recovery_recompute` fails inside `_derive_pathspec_via_recovery_paths` (not the scope-check branch), the composite returns a bare non-zero exit with no `BAIL_REASON` or `NEXT_ACTION`, giving the orchestrator less routing signal than the `recovery-out-of-scope` path.

### OOS_5: [OUT_OF_SCOPE] Codex missing-binary path still labeled as selection drift
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: nit
- **Concern**: Step 2.4 labels every `coder=codex` + `STATUS=claude_fallback` as "selection drifted after Step 0", including the documented missing-binary path (`CODEX_BINARY_FOUND=false`, `ORCHESTRATOR_EDIT_AUTHORITY=allowed`). Cursor already has neutral missing-binary prose; Codex does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add missing-binary guard to Codex Step 2.4 messaging matching the Cursor branch
  - From dyn-dyn-skill-wires-output.txt: Step 2.4 still labels every `coder=codex` + `STATUS=claude_fallback` as "selection drifted after Step 0", including the documented missing-binary path (`CODEX_BINARY_FOUND=false`, `ORCHESTRATOR_EDIT_AUTHORITY=allowed`). Cursor already has neutral missing-binary prose at line 443; Codex does not.

### OOS_6: [OUT_OF_SCOPE] `_capture_prelaunch_porcelain` partial-artifact idempotency on claude_fallback path
- **Reviewer(s)**: dyn-dyn-dispatch-telemetry-output.txt
- **Severity**: latent
- **Concern**: `_capture_prelaunch_porcelain` treats existence of `step2-prelaunch-porcelain.nul` alone as complete; it does not verify `step2-prelaunch-content-digests.txt` or `step2-prelaunch-index.env`. An interrupted capture can skip re-capture and break `recovery-paths` on claude-fallback runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dispatch-telemetry-output.txt: `_capture_prelaunch_porcelain` treats existence of `step2-prelaunch-porcelain.nul` alone as complete; it does not verify `step2-prelaunch-content-digests.txt` or `step2-prelaunch-index.env`. An interrupted capture can skip re-capture and break `recovery-paths` on claude-fallback runs.

### OOS_7: [OUT_OF_SCOPE] Step 2.4 lacks explicit prelaunch baseline gate after wrapper capture
- **Reviewer(s)**: dyn-dyn-dispatch-telemetry-output.txt
- **Severity**: latent
- **Concern**: Step 2.4 proceeds to main-agent Edit/Write without an explicit fail-closed gate verifying `step2-prelaunch-porcelain.nul` and digests exist after wrapper-side capture. Wrapper failure or session retry can allow edits without a proven baseline for pathspec derivation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dispatch-telemetry-output.txt: Step 2.4 proceeds to main-agent Edit/Write without an explicit fail-closed gate verifying `step2-prelaunch-porcelain.nul` and digests exist after wrapper-side capture; wrapper failure or session retry can allow edits without a proven baseline for pathspec derivation.

### OOS_8: [OUT_OF_SCOPE] `phantom-probe.md` stale on post-dispatch routing
- **Reviewer(s)**: dyn-dyn-skill-wires-output.txt
- **Severity**: nit
- **Concern**: Post-dispatch routing moved to `POST_DISPATCH_NEXT` tokens in `step-2-post-dispatch`, but `phantom-probe.md` still says branch comparison stays in SKILL.md. Orchestrators following phantom-probe may ignore token routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-wires-output.txt: Post-dispatch routing moved to `POST_DISPATCH_NEXT` tokens in `step-2-post-dispatch`, but phantom-probe still says branch comparison stays in SKILL.md. Orchestrators following phantom-probe may ignore token routing.

