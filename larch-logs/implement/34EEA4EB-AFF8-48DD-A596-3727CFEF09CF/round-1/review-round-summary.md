# Review Round 1

- Mode: `diff`
- 10 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Calm statusline churn
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: Calm rendering still refreshes the wall clock on every tick, so an unchanged breadcrumb tail can visibly flip at minute boundaries without any real progress change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_2: Tier-2 breadcrumbs across long phases
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: Tier-2 curated breadcrumbs are still too coarse across the long-running design, review, and ship drivers, so the statusline can sit on a coarse round-start line while reviewer/voter/CI-fix/rebase/merge work continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add _progress_note calls at existing ship phase transitions for checks, CI-fix rounds, rebase+merge, and merged.
  - From cursor-specialist-correctness: Append breadcrumbs from the design plan-review loop at the plan’s tier-2 transition points.
  - From cursor-specialist-correctness: Emit curated breadcrumbs from round_runner (or shared hooks) for reviewer M/N, aggregator, voters, and post-fix checks.
  - From codex-specialist-correctness: Add progress-note calls at the planned reviewer, aggregator, voter, apply, post-fix-check, CI-fix, rebase, and merge transitions.
  - From cursor-specialist-edge-cases: Emit plan-named events from plan_review, round_runner, review_and_fix, and ship at each transition.
  - From codex-specialist-edge-cases: Add append_breadcrumb calls at the plan-required review, plan-review, and ship transition points.
  - From cursor-specialist-testing: Wire progress_file.append_breadcrumb at launch/collector/voter/apply sites with skill design step 3 and add fake-writer unit tests.
  - From cursor-specialist-testing: Emit breadcrumbs at existing ship phase transitions per the plan and test with monkeypatched append_breadcrumb.
  - From cursor-specialist-testing: Add planned breadcrumb hooks in round_runner collector and voter paths and test emission with fakes.
  - From cursor-specialist-plan-fidelity-auto: Wire append_breadcrumb at plan-listed transitions in plan_review plan_review_loop round_runner review_and_fix and ship with required event phrasing


### FINDING_3: Repo-root resolution mismatch
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Writers, readers, and installer paths resolve clone identity from cwd inconsistently, so breadcrumbs can be written and tailed under different clone roots when Claude starts in a subdirectory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Resolve repo identity with consumer_repo_root() (or equivalent) on both write and read before progress_path().
  - From codex-specialist-correctness: Resolve the git or consumer repo root at cwd/workspace ingress and use that root consistently for install, read, and write paths.
  - From cursor-specialist-edge-cases: Pass repo_root/REPO_CWD into every append_breadcrumb call and test cwd mismatch.


### FINDING_5: Progress log symlink containment
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-statusline-security
- **Severity**: major
- **Concern**: append_breadcrumb follows symlinked progress files or ancestors and can chmod the followed target, so a same-user symlink under the cache can redirect breadcrumb writes outside the intended file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Check larch_io.assert_no_symlink_path_or_ancestors(path), require existing targets to be regular non-symlink files, and append with O_NOFOLLOW|O_APPEND|O_CREAT where available.
  - From codex-specialist-edge-cases: Reject symlinked ancestors before mkdir/open, or route the append through a nofollow-aware helper with the same containment rules as the installer.
  - From dyn-dyn-statusline-security: Before append, resolve progress_path(repo_root), run assert_no_symlink_path_or_ancestors on the file and its parents, refuse non-regular files, and open with O_NOFOLLOW (or use an larch.io helper that already enforces nofollow + post-open verification). Re-check the inode after open per G-Py-8.


### FINDING_6: Progress-report retirement incomplete
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: The public progress-report retirement is incomplete because live-discovery code, mid-run render paths, and old tests still ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Finish the import audit, delete the unused live-discovery and mid-run report code and tests, and keep only render-phase-detail plus round-meta verbs.
  - From cursor-specialist-edge-cases: Delete _progress_report_live.py, remove _report/_render_* paths, and update tests to phase-detail/round-meta only.
  - From codex-specialist-edge-cases: Split reusable end-of-run helpers, then delete the live discovery module, private report path, mid-run renderers, and old tests
  - From cursor-specialist-testing: Delete _progress_report_live and mid-run render paths per plan keeping render_phase_detail only.
  - From cursor-specialist-plan-fidelity-auto: Finish audit: delete _progress_report_live.py strip mid-run code from progress_report.py delete or migrate mid-run tests keep render_phase_detail and round-meta only


### FINDING_8: Breadcrumb control-char sanitization
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-statusline-security
- **Severity**: major
- **Concern**: Breadcrumb validation rejects newlines and URLs but still allows ANSI/OSC/C0 control bytes, which the statusline later prints back to the terminal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a shared sanitizer that strips or rejects all C0 controls except optional space, apply it in breadcrumb_line for skill, step, and text, and add a regression test with \x1b]8;;… and bell bytes to prove the statusline reader never emits them.
  - From dyn-dyn-statusline-security: Add a shared sanitizer that strips or rejects all C0 controls except optional space, apply it in breadcrumb_line for skill, step, and text, and add a regression test with \x1b]8;;… and bell bytes to prove the statusline reader never emits them.


### FINDING_9: Invalid statusline stdin falls back to PWD
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Empty or malformed statusline stdin falls back to the ambient PWD, which can render progress for the wrong clone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Resolve only workspace.current_dir or payload cwd and return empty output for invalid or empty payloads


### FINDING_10: Bootstrap notice delivery can hang
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: The bootstrap path can hang or suppress the one-time first-install notice because the installer is invoked through _cli while stdin is still being read/captured.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Relay only the bounded first-install notice from Step 0 or expose a machine flag that Step 0 prints once
  - From codex-specialist-testing: Skip stdin parsing when repo-root/plugin-root are already supplied, or run the installer with stdin=DEVNULL or a direct function call so the notice can surface.


### FINDING_13: Custom user statusLine should still run without python3
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Custom user statuslines disappear on hosts where python3 is absent or later unavailable, even though the larch tail could still be gated separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Run the user command unconditionally, then gate only the larch tail on python3 and cli.py availability.


### FINDING_14: Statusline-install symlink and shell safety
- **Reviewer(s)**: dyn-dyn-statusline-security
- **Severity**: major
- **Concern**: User-scope chaining reads ~/.claude/settings.json without a symlink guard, bakes the command into a cached script, and executes it through bash -lc on every refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-statusline-security: Call assert_no_symlink_path_or_ancestors on Path.home() / ".claude" / "settings.json" before read; if the check fails, skip chaining (install only the larch segment). Prefer invoking the user command through exec argv splitting or a fixed allowlisted wrapper instead of bash -lc when feasible.


