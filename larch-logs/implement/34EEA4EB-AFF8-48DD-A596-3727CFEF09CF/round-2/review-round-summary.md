# Review Round 2

- Mode: `diff`
- 7 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Retired live-discovery and mid-run report code still ships
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: The live-discovery module, mid-run renderers, and legacy report tests are still present, so the plan’s acceptance target to fully retire live discovery and mid-run machinery is not met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Delete _progress_report_live.py, strip mid-run paths from progress_report.py, and remove _report/_discover_live_run tests.
  - From codex-specialist-correctness: Delete _progress_report_live.py, remove re-exports and mid-run renderers, and keep only phase-detail and round-meta surfaces.
  - From cursor-specialist-edge-cases: Delete _progress_report_live.py, mid-run renderers, and legacy _report tests; keep only render-phase-detail and round-meta surfaces.
  - From codex-specialist-edge-cases: Finish the consumer audit, delete _progress_report_live.py and the remaining legacy tests, and keep only render-phase-detail plus the round-meta verbs.
  - From codex-specialist-testing: delete _progress_report_live.py, remove the live-report re-exports and _report/mid-run renderers from progress_report.py, and move any surviving phase-detail coverage into the dedicated review-phase-detail test file.
  - From cursor-specialist-plan-fidelity-auto: Delete _progress_report_live.py after consumer audit; strip mid-run code from progress_report.py; remove live-discovery tests from test_progress_report.py; keep render_phase_detail and round-meta writers.


### FINDING_2: Tier-2 progress breadcrumbs are still too coarse
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: Long-running review, implement, ship, and design phases can still sit on generic round-start or phase-start lines without the plan-required reviewer, voter, CI-fix, and design Step 3 progress updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add append_breadcrumb calls at round launch, reviewer M/N completion, aggregator/voter launch, voting, and apply transitions.
  - From cursor-specialist-correctness: Emit launching N reviewers, reviewers M/N done, and voting done X/Y accepted breadcrumbs from collector and tally hooks.
  - From cursor-specialist-correctness: Add breadcrumbs when CI-fix rounds start with failing job names and when named check shards run.
  - From codex-specialist-correctness: Emit count-bearing collector/voter breadcrumbs and ship breadcrumbs for named checks, CI-fix rounds, failing jobs, rebase, and merge.
  - From cursor-specialist-edge-cases: Emit plan-listed events at dispatch/collect/vote/apply boundaries in plan_review_panel.py and review_core_body.py.
  - From cursor-specialist-plan-fidelity-auto: Insert curated append_breadcrumb calls at existing driver hooks with the plan’s single-line event grammar.


### FINDING_3: Breadcrumb validation still allows terminal control bytes
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, cursor-specialist-plan-fidelity-auto, dyn-dyn-statusline-security
- **Severity**: major
- **Concern**: Breadcrumb text can still carry ANSI, OSC, and other control bytes, and the statusline prints those bytes back to the terminal, which can corrupt or spoof the UI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Reject C0/C1 control characters and OSC sequences in _reject_line_part; test ANSI without URLs.
  - From cursor-specialist-edge-cases: Reject or strip C0/C1 controls in _reject_line_part and test bare ANSI without URLs.
  - From codex-specialist-edge-cases: Reject all C0/C1 controls and DEL in `skill`, `step`, and `text`, and add a defensive strip/reject check in the statusline reader before rendering cached rows.
  - From codex-specialist-testing: reject all control characters in append_breadcrumb, and add a regression test for raw ESC and OSC payloads.
  - From cursor-specialist-plan-fidelity-auto: Reject or strip control characters in _reject_line_part and add tests for pure-escape payloads without URLs.
  - From dyn-dyn-statusline-security: Reject or strip `\x00-\x1f`, `\x7f`, and `\x1b` in `_reject_line_part` (and defensively in the reader before print); add regression tests for pure-ANSI payloads without URLs.


### FINDING_4: Chained user-scope statusline commands need a timeout
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-plan-fidelity-auto, dyn-dyn-statusline-security
- **Severity**: major
- **Concern**: The generated launcher still runs the chained user statusline without a short timeout, so a hung user command can block larch progress on every refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Wrap the chained user command with a short timeout before appending progress statusline output.
  - From codex-specialist-correctness: Wrap the user command in a short timeout and always run larch afterward; add a regression test.
  - From cursor-specialist-edge-cases: Wrap the user branch with a short timeout and fail silent on expiry.
  - From codex-specialist-edge-cases: Run the user statusline through a bounded helper, or generate a wrapper that enforces a short timeout and always continues to the larch statusline path.
  - From cursor-specialist-plan-fidelity-auto: Wrap the chained user command with a bounded timeout in the launcher script; add a hang regression test.
  - From dyn-dyn-statusline-security: Wrap the chained command with `timeout`, prefer direct `exec` when the setting is a single executable token, and keep `sh -c` only when shell features are required.


### FINDING_5: Design Step 0 statusline bootstrap is incomplete
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: /design Step 0 still does not reliably install the statusline and can suppress the first-install notice, so a clean session may start without the expected operator feedback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add best-effort statusline install to design Step 0 or shared session setup.
  - From codex-specialist-testing: capture and forward stdout for the --notice call, or route /design Step 0 through the same notice-preserving helper used by bootstrap.


### FINDING_8: Statusline reader lacks ancestor symlink checks
- **Reviewer(s)**: dyn-dyn-statusline-security
- **Severity**: major
- **Concern**: The reader only checks the leaf path and can still follow symlinked ancestors, which breaks the containment contract for progress-log reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-statusline-security: Call larch_io.assert_no_symlink_path_or_ancestors(path) before reading; on refusal, return empty stdout (fail-silent) like other error paths.


### FINDING_9: Progress-file append needs a post-mkdir symlink recheck
- **Reviewer(s)**: dyn-dyn-statusline-security
- **Severity**: major
- **Concern**: The append path validates containment before mkdir but not again immediately before os.open, so a same-UID parent-symlink swap can redirect the log outside the intended cache tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-statusline-security: Re-run assert_no_symlink_path_or_ancestors(path) immediately before os.open, or open through a validated directory file descriptor so parent symlinks cannot redirect the append target.


