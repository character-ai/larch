### FINDING_1: Preserve REPO_ROOT across proceed-path refreshes
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Root Contract Reviewer
- **Severity**: blocking
- **Concern**: On the `ROUTE=proceed` / `--skip-approve` path, later `write-design-env` refreshes can rebuild `source-env.sh` without the authoritative `REPO_ROOT`, so Gate C and follow-on helpers can fall back to plugin-cache or ambient cwd and silently miss the guidelines artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add python/larch/design/design_router.py to Files to modify: thread the same resolved repo root into init_runparams write-design-env (read from existing source-env.sh or reuse the Step 0 helper), and add a lifecycle test that step0 route/init-runparams preserves export REPO_ROOT in source-env.sh.
  - From Cursor-Arch: Add a shared helper (e.g. python/larch/git/repo_roots.py next to consumer_repo_root) used by both step0_session_main and init_runparams_main.
  - From Cursor-Innovation: In session_env.py recover export REPO_ROOT from the existing source-env.sh when --repo-root is omitted (mirror CODEX_BINARY_FOUND recovery), or pass --repo-root into design_router.py init-runparams from the Step 0 capture; add a test that init-runparams preserves REPO_ROOT
  - From Codex-Innovation: Pass the captured repo root through every write-design-env caller or preserve an existing REPO_ROOT on rewrite
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/design/design_router.py: pass --repo-root to write-design-env in init_runparams_main (read REPO_ROOT from existing source-env.sh or resolve via consumer_repo_root() with the same cwd fallback). Add a lifecycle test that step0_session then init_runparams leaves export REPO_ROOT in source-env.sh.
  - From Cursor-Requirements: Add ### UPDATED: python/larch/design/design_router.py: pass --repo-root on the init refresh (read export REPO_ROOT from existing source-env.sh or call the shared Step 0 resolver) and add a regression in python/tests/design/test_design_lifecycle.py that init-runparams forwards it.
  - From Cursor-dyn-Root Contract Reviewer: In the same file the plan already touches, recover prior REPO_ROOT from the existing source-env when --repo-root is omitted (mirror CODEX_BINARY_FOUND recovery), or pass --repo-root into the init write-design-env call (parse from source-env or add --repo-root to init-runparams argv from design_step0.py)


### FINDING_2: Regression coverage misses init-runparams proceed path
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Root Contract Reviewer
- **Severity**: important
- **Concern**: The new tests cover explicit `--repo-root` on `step0_session_main`, but they do not exercise the folded `init_runparams_main` refresh on the dominant proceed path, so a REPO_ROOT-clobber regression can still ship green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend test_design_lifecycle.py to assert init_runparams_main (or folded step0 route) passes --repo-root on write-design-env and that source-env.sh still exports the git toplevel after init completes.
  - From Cursor-Innovation: Add a test that init-runparams preserves REPO_ROOT
  - From Cursor-Pragmatic: Extend test_design_lifecycle.py (or the architectural test) to assert source-env.sh still exports REPO_ROOT after init_runparams from a subdirectory cwd, and optionally drive guideline helpers via a shell that sources source-env.sh with $REPO_ROOT unset in the environment.
  - From Cursor-Requirements: Extend test_design_lifecycle coverage so init_runparams_main (or the folded Step 0b proceed path) is exercised with a pre-seeded source-env.sh REPO_ROOT and asserts the refresh write-design-env argv includes --repo-root with the git toplevel, not the subdirectory cwd.
  - From Cursor-dyn-Root Contract Reviewer: Add a lifecycle test: after step0_session_main plus init_runparams_main on a proceed path, assert source-env.sh still exports the git toplevel REPO_ROOT


### FINDING_4: Missing fail-closed Gate C regression
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The regression plan is success-only and does not force a non-zero `persist-design-assessment` path, so a future edit could still skip the warning append or fall through to Step 5 after persistence failure without a test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a negative Gate C regression that makes `persist-design-assessment` return non-zero, then assert the `**⚠ 4b: architectural-guideline assessment persistence failed**` message, the bounded `Warnings` line, and no Step 5 transition.


### FINDING_1: Bind `REPO_ROOT` before guideline helpers
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: Gate C and Step 1d.7 invoke guideline helpers from fresh Bash fences while relying on `$REPO_ROOT` that is not rebound in-fence, so `present-note` / `persist-design-assessment` can still resolve as if the repo were absent and silently skip the assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In each Presentation/persist helper Bash fence, read REPO_ROOT from $DESIGN_TMPDIR/source-env.sh (or source current-design-env-$PPID.sh) before the first present-note/persist call; keep the planned empty-root repair stop
  - From Cursor-Innovation: Before the first guideline helper in each gate, load the Step 0 capture: source `$DESIGN_TMPDIR/source-env.sh` in the same Bash fence, or emit `REPO_ROOT=` from `step0_session_main` stdout and require a repair stop when it is empty before any helper call. Do not rely on `session read-key` against `source-env.sh` as written today; lines use an `export` prefix.
  - From Cursor-Pragmatic: Add a binding step before every guideline helper call: read REPO_ROOT from $DESIGN_TMPDIR/source-env.sh via session read-key (or source that file once), then apply the existing repair-stop when empty; mirror the same pattern in design-outline.md.
  - From Cursor-Requirements: Require each guideline helper fence to source $DESIGN_TMPDIR/source-env.sh first (or inline-read REPO_ROOT from that file) before present-note / persist-design-assessment; keep the empty-REPO_ROOT repair stop after binding.


### FINDING_3: Gate C regression must cover the persistence contract
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The planned test only exercises helper return codes and can miss the skip-approve Gate C contract, so the flow could still omit the bounded warning or advance to auto-approval/Step 5 after a failed persist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise the planned regression to pin the Gate C branch itself. Exercise an available Gate C harness, or add a narrow markdown contract test if no executable harness exists, that verifies the skip-approve branch runs `present-note --repo-root "$REPO_ROOT"` and `persist-design-assessment --repo-root "$REPO_ROOT"`, writes the assessment artifact, and stops with the bounded warning on forced persist failure.
  - From Codex-Requirements: Add a focused regression or validation step that exercises the Gate C non-zero persistence branch and asserts the bounded warning is recorded and the flow does not prompt, auto-approve, or transition to Step 5


