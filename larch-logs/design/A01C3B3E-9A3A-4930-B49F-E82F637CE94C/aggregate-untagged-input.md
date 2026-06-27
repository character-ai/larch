### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1939-2024
- **Concern**: Pure `claude_fallback` prelaunch capture in `run_dispatch_main` omits filesystem `repo_root` acquisition. Scenario: `step2_dispatch_main` returns `STATUS=claude_fallback` on `coder=claude` and missing-binary paths before `git rev-parse --show-toplevel` (~2638-2664). The plan moves prelaunch capture into `run_dispatch_main` (~52) via `_capture_prelaunch_porcelain(*, repo_root, ...)`, but only `_run_step4_recovery_recompute` pins worktree resolution (~88). A literal port can call the helper with no root, fail closed, or use the wrong directory, so `step2-prelaunch-porcelain.nul` / digests stay missing and ordinary-fallback pathspec derivation still includes pre-existing dirt.
- **Proposed resolution**: In `run_dispatch_main`, after the child exits and before relaying stdout: parse captured child stdout for `STATUS=claude_fallback` plus `ORCHESTRATOR_EDIT_AUTHORITY=allowed`; resolve `repo_root` with the same `git rev-parse --show-toplevel` contract as `step2_dispatch_main`; call `_capture_prelaunch_porcelain` only when prelaunch artifacts are absent; fail closed (non-zero) when git root resolution fails.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:147-152
- **Concern**: Orchestrator `$REPO_ROOT` for foreground `recovery-paths` wires is not pinned. Scenario: The plan adds orchestrator-side `implement recovery-paths` (~150-152) and keeps recovery-sub-branch prose that already uses `$REPO_ROOT`, but only says "orchestrator resolves REPO_ROOT from git." Session `REPO` is the GitHub slug, not the filesystem root `recovery_paths_main` requires (`--repo-root` is required). Without an explicit bind/fail-closed step, the orchestrator can pass an empty or wrong root and argparse fails or mis-filters tmpdir paths before the Step 3 composite runs.
- **Proposed resolution**: In `skills/implement/SKILL.md` Step 2.4 (ordinary fallback and retained recovery prose), pin one bind immediately before any orchestrator `recovery-paths` call, e.g. `REPO_ROOT="$(git rev-parse --show-toplevel)"` with fail-closed abort when empty/non-zero; state explicitly that `REPO` must not substitute for `REPO_ROOT`.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:2638-2657
- **Concern**: Pure Claude fallback still returns before any prelaunch capture hook can run. Scenario: The new Step 2.4 recovery path depends on `step2-prelaunch-porcelain.nul` and digests existing before edits, but the `coder=claude`, missing-binary, and `--force` branches exit immediately. That leaves the ordinary fallback path with no baseline, so recovery pathspec derivation can fail closed or include unrelated dirt.
- **Proposed resolution**: Move `_capture_prelaunch_porcelain` into each early fallback branch before the `return 0`, not only after the launcher-backed path.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1067-1069
- **Concern**: `commit_route_main` still treats `noop` as a non-success exit. Scenario: The new `noop` outcome is required for the Step 4 external no-op path, but the direct `commit-route` CLI still returns 1 unless the outcome is `continue` or `seeded-stall`. `_step5_resume_commit_phase` and any direct caller will treat a valid no-op commit route as a failure and stop the fold.
- **Proposed resolution**: Include `noop` in the zero-exit branch of `commit_route_main` so the subprocess exit code matches the widened outcome contract.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:343-344
- **Concern**: Step 3 composite timeout bump omits retiring the positive 10800000 SKILL assertion. Scenario: The plan moves Step 3 to `checks-commit-route` with `timeout: 15600000` and updates launcher timeout pins, but `test-implement-structure.sh` still requires `skill_text.count('timeout: 10800000') >= 1` with error "SKILL.md must keep the 10800000 timeout tier for Step 3". After the fold SKILL will have zero `10800000` literals, so `make test-implement-structure` fails even when runtime routing is correct.
- **Proposed resolution**: Replace lines 343-344 with a Step 3 composite pin matching Step 6 (require `timeout: 15600000` on the `checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r` fence) or delete the 10800000 tier check entirely; add the Step 3 composite entry to the timeout `for script, timeout in [...]` loop at lines 229-236.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:415-417
- **Concern**: Post-dispatch fence argv change is prose-only; plan lacks an explicit fenced bash example with `--expected-branch`. Scenario: The plan includes a fenced composite launcher for Step 3/4/4.r but only prose ("Change the post-dispatch fence to pass `--expected-branch "$BRANCH_NAME"`") for post-dispatch. The current SKILL fence is still `step-2-post-dispatch.sh` with no args. A literal edit from fenced examples alone can ship token routing prose while omitting the required flag, weakening the branch assertion the issue keeps in orchestrator routing.
- **Proposed resolution**: Add an explicit SKILL fenced bash block in the plan showing `bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-2-post-dispatch.sh --expected-branch "$BRANCH_NAME"` and require removing the old exit-code-first branch-compare cascade in the same edit.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/agents.py:5355-5487
- **Concern**: Launcher-side Step 2 token mark still runs on every external-implementer launch. Scenario: run_dispatch_main is adding the first-dispatch Step 2 token row, but the Codex and Cursor launchers still mark the same token on every external run and Q/A redispatch, so the telemetry contract will double-count Step 2 instead of becoming once-only.
- **Proposed resolution**: Remove or gate the launcher token mark behind the same once-only sentinel, or move the Step 2 token mark entirely into run_dispatch_main and update the launcher contract.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1939-2665
- **Concern**: Pure claude_fallback prelaunch capture has no repo-root source. Scenario: The plan adds `_capture_prelaunch_porcelain(repo_root=...)` for pure Claude fallback, but the only branch that knows the worktree root currently returns before `step2_dispatch_main` resolves it, and run_dispatch_main is not given an earlier repo-root probe, so the helper cannot run on the exact missing-binary / `claude` paths it is meant to fix.
- **Proposed resolution**: Derive the git toplevel in run_dispatch_main before spawning step2-dispatch, or thread the root through the fallback branch before returning, then call `_capture_prelaunch_porcelain` with that path.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1972-1977; python/test_implement_dispatch.py:828-833
- **Concern**: run_dispatch_main still hard-fails on missing Cursor/Codex binaries, so the plan never reaches the intended `STATUS=claude_fallback` path for the explicit missing-binary case.. Scenario: The planned prelaunch capture and Step 2.4 fallback path stay unreachable whenever the selected external tool is absent, which is one of the feature’s stated inputs.
- **Proposed resolution**: Remove or convert the early binary checks in `run_dispatch_main` so missing `cursor`/`codex` binaries flow through `step2_dispatch_main`’s fallback, and replace the cursor-missing test with fallback coverage for both binaries.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/checks-repair-loop.md
- **Concern**: Step 3 repair-loop refresh omits required `--repo-root` for `implement recovery-paths`. Scenario: The plan folds Step 3 into the composite and pins a repair-loop refresh that re-runs `implement recovery-paths` with only `--tmpdir "$IMPLEMENT_TMPDIR"` and absolute porcelain/out paths. `recovery_paths_main` requires `--repo-root` plus prelaunch/postlaunch/digest inputs. After checks-repair-loop main-agent edits, a literal follow hits argparse failure or uses an empty repo root, so `implementation-commit-paths.nul` stays stale and the folded Step 3/4/4.r composite commits the wrong pathspec or seeds `seed-failed`.
- **Proposed resolution**: Add `--repo-root "$REPO_ROOT"` to the section 4 repair-refresh pin (bind `REPO_ROOT` via `git rev-parse --show-toplevel` in SKILL prose) and mirror the full absolute argv from the Step 2.4 ordinary-fallback wire: prelaunch porcelain, fresh postlaunch porcelain, prelaunch digests, and `implementation-commit-paths.nul` out-file.

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1939-2010
- **Concern**: run_dispatch_main has no repo_root source for the new prelaunch-capture hook. Scenario: The plan adds `_capture_prelaunch_porcelain(*, repo_root, implement_tmpdir)` and says `run_dispatch_main` should call it on `STATUS=claude_fallback`, but it never derives or threads `repo_root` into that path. Pure claude-fallback runs would still return without writing `step2-prelaunch-porcelain.nul` or digests, so later `recovery-paths` derivation and recovery recompute stay broken.
- **Proposed resolution**: Derive `repo_root` in `run_dispatch_main` before the lock, or thread it through from the child, and pass it into `_capture_prelaunch_porcelain` before returning on `claude_fallback`.
