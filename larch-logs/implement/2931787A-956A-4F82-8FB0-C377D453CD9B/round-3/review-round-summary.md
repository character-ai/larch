# Review Round 3

- Mode: `diff`
- 4 accepted, 11 rejected (5 neutral)

## Accepted Findings

### FINDING_1: Step 2 telemetry marks after dispatch, not at Step 2 entry under lock
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dyn-dispatch-telemetry-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: `_maybe_mark_step2_telemetry` runs only after `step2-dispatch` returns `rc==0`, not immediately after `dispatch.lock` acquisition and before spawning the child. Timing rows therefore anchor at dispatch end (after external implementer wall time), diverging from plan/`step2-dispatch.md` Step-2-entry semantics. A first dispatch that bails (`STATUS=bailed`) or returns non-zero leaves no `.step2-telemetry-marked`, so retries can undercount or duplicate Step 2 budget/timing ledger rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Move _maybe_mark_step2_telemetry before subprocess.run(step2-dispatch); test call order
  - From cursor-specialist-edge-cases-output.txt: Restore pre-spawn marking under dispatch.lock per plan order (lock → mark → spawn) while keeping --answers and .step2-telemetry-marked guards
  - From codex-specialist-testing-output.txt: make the once-only telemetry path fire on the first lock-guarded dispatch regardless of child rc, and keep timing plus sentinel handling independent from best-effort token-mark failure.
  - From dyn-dyn-dispatch-telemetry-output.txt: Call `_maybe_mark_step2_telemetry` immediately after lock acquisition and validation, before `subprocess.run(step2-dispatch)`, keeping the once-only `.step2-telemetry-marked` guard and the `--answers` redispatch skip.
  - From dyn-dyn-skill-wires-output.txt: Either move once-only token/timing marks to immediately after lock acquisition and before spawning `step2-dispatch`, or update SKILL.md and `step2-dispatch.md` to state explicitly that marks run only after a successful first dispatch return.


### FINDING_2: Telemetry sentinel consumed before claude_fallback prelaunch capture succeeds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dyn-dispatch-telemetry-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: On `STATUS=claude_fallback` paths, `run_dispatch_main` writes `.step2-telemetry-marked` via `_maybe_mark_step2_telemetry` before `_resolve_repo_root()` and `_capture_prelaunch_porcelain()` complete. If repo-root resolution or prelaunch capture fails, the wrapper returns non-zero without relaying fallback stdout, but the once-only sentinel is already consumed. Retries skip telemetry and Step 2.4 lacks required prelaunch baseline artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Capture prelaunch before writing telemetry sentinel; mark only after both succeed
  - From codex-specialist-correctness-output.txt: Move the sentinel write until after fallback capture succeeds, or clear the sentinel on any hook failure.
  - From cursor-specialist-edge-cases-output.txt: Run prelaunch capture before writing .step2-telemetry-marked, or write the sentinel only after capture succeeds; add a regression test for capture failure after successful fallback dispatch
  - From codex-specialist-edge-cases-output.txt: move the sentinel write until after repo-root resolution and prelaunch capture succeed, or stage the marker in memory and commit it only on a fully successful fallback path.
  - From cursor-specialist-testing-output.txt: Defer telemetry (and sentinel write) until post-child hooks succeed; clear sentinel on capture failure; add pytest for capture-failure path.
  - From codex-specialist-testing-output.txt: defer writing `.step2-telemetry-marked` until after the fallback baseline capture succeeds, or clear the sentinel on capture failure before returning.
  - From dyn-dyn-dispatch-telemetry-output.txt: On the claude-fallback path, run repo-root resolution and prelaunch capture before telemetry marking, or write `.step2-telemetry-marked` only after prelaunch capture succeeds and stdout will be relayed.
  - From dyn-dyn-skill-wires-output.txt: Run prelaunch capture (and any fail-closed validation) before `_maybe_mark_step2_telemetry`, or write the sentinel only after both telemetry and post-child baseline capture succeed.


### FINDING_11: Stale session-scoped `MANIFEST_PATH` causes Step 4 external noop when implementation commit still needed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-step4-composite-output.txt
- **Severity**: important
- **Concern**: `_run_step4_commit_leg` treats any non-empty `MANIFEST_PATH` in `ship-seed-input.env` as proof the dispatcher already committed, without tying noop to the current dispatch outcome. `step2_post_dispatch_main` persists `MANIFEST_PATH` whenever branch read succeeds (including on `POST_DISPATCH_NEXT=bail`), and `_persist_ship_seed_context` never clears it on later `claude_fallback` retries in the same `$IMPLEMENT_TMPDIR`. A stall-recovery or redispatch can skip the implementation commit while `implementation-commit-message.txt` / pathspec artifacts are present, leaving Claude-fallback edits uncommitted before folded `4.r`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Require _path_readable_nonempty on MANIFEST_PATH before returning noop; fall through to implementation/recovery commit when unreadable
  - From dyn-dyn-step4-composite-output.txt: Gate the noop branch on a run-scoped marker tied to the current dispatch outcome (for example a `DISPATCHER_COMMITTED=true` KV written only from the `STATUS=complete` post-dispatch path, or clearing `MANIFEST_PATH` in `ship-seed-input.env` whenever `run_dispatch_main` relays `STATUS=claude_fallback`), and require the manifest path to be readable before noop. Add a composite test where post-dispatch seeds `MANIFEST_PATH`, a later `claude_fallback` run writes implementation commit artifacts, and the commit leg must not noop.


### FINDING_16: Repair-loop refresh omits `implementation-commit-message.txt` regeneration
- **Reviewer(s)**: dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: SKILL requires refreshing postlaunch porcelain, pathspec, and commit message before re-launching the Step 3 composite after repair edits. The repair-loop refresh fence only rebinds `REPO_ROOT` and reruns `recovery-paths`; it never rewrites `implementation-commit-message.txt`. After repair-loop edits, the composite can commit a stale message against a refreshed pathspec.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-wires-output.txt: Add an explicit repair-loop step (and matching fence) to regenerate `implementation-commit-message.txt` from the current plan/issue context before composite re-entry, mirroring the Step 2.4 wire.


