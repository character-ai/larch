# Review Round 3

- Mode: `diff`
- 28 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: flush_logs_pre omits write-final-report parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-flush-boundary-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` does not run the `write-final-report.sh` step that `refresh-run-logs.sh` performs between execution-issues and token/timing. Pre-push log commits can lack `run-statistics` / `final-summary` / `final-report` artifacts that bash always generates, so step9a1, tracking-issue upserts, and audits may see stale or missing inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Port write-final-report behavior into flush_logs_pre/post and test artifact creation
  - From cursor-specialist-correctness-output.txt: Invoke or port write-final-report in flush_logs_pre (and tmpdir-only pieces in post).
  - From cursor-specialist-plan-fidelity-output.txt: Invoke a Python port or controlled shell-out of write-final-report.sh in flush_logs_pre (and post-merge summary inputs in flush_logs_post if required)
  - From dyn-flush-boundary-output.txt: Add a `write_final_report` (or shell-out) hook in `flush_logs_pre` after the first execution-issues pass and before `_render_token_timing_batches`, matching bash ordering; mirror the post-merge re-render in `flush_logs_post` per `ship-pr.sh` postmerge (lines 3652–3657).


### FINDING_10: no test proving merge_pr flush pre/post order and no post-merge commit
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Nothing in `test_merge.py` proves `merge_pr` calls `flush_logs_pre` then `flush_logs_post` on success paths, or that post-flush never runs a git commit. Dropping `_post_flush` or reordering flushes could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monkeypatch flush entrypoints; assert call order; assert post path never calls git commit.
  - From cursor-specialist-edge-cases-output.txt: Add monkeypatched merge_pr test for pre/post flush invocation and no post-merge git commit.
  - From cursor-specialist-plan-fidelity-output.txt: Add spy/monkeypatch tests in test_merge.py asserting pre/post flush call order and no commit argv after post


### FINDING_11: _flush_recoverable missing P1 cap and N2a non-log-path tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests lack coverage for >5 flush commits (P1) and diffs outside `larch-logs/` (N2a). Those cases might be misclassified recoverable, leading to wrong force-push recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add unit tests for subject count cap and diff paths outside larch-logs/.
  - From cursor-specialist-plan-fidelity-output.txt: Add dedicated _flush_recoverable / merge_pr tests for >5 commits, non-larch-logs paths, and successful recovery


### FINDING_12: pre-flush happy-path test does not assert git commit
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_flush_logs_pre_happy_path_commits` does not assert that a log commit occurred. Removing `_larch_log_commit` could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert RecordingRunner.git_commits >= 1 on successful flush_logs_pre.


### FINDING_13: push_branch lacks detached-HEAD guard and test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `push_branch` does not port the detached-HEAD guard from `git-push.sh`. Detached HEAD after rebase could push the wrong ref or fail opaquely vs bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port symbolic-ref checks; add test_push_branch_refuses_detached_head.


### FINDING_15: tracking_issue upsert_token_report edge cases untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Missing tests for multi-state rename and 256-char truncation in `upsert_token_report`. Title/comment regressions on edge payloads may ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add tests for upsert_token_report rename matrix and truncation preserving prefix.


### FINDING_16: force_push_recovery success and lease-retry paths untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `force_push_recovery` success, `noop_same_ref`, and diverged lease-retry paths lack unit tests beyond dirty-tree. Merge/pr escalation regressions could fail open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add success noop_same_ref and diverged_retry_failed fixtures.


### FINDING_19: execution-issues NDJSON committed without redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Execution-issue NDJSON records embed raw `execution-issues.md` bodies without the fail-closed redaction applied to batch payloads. Tool failure text (API keys, PEM, session paths) can be committed under `larch-logs/implement/.../execution-issues.ndjson` and become public on merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact each record body with the same fail-closed contract as _redact_batch_payload before append; mirror bash larch_log_redact_file; add PEM/token regression test.


### FINDING_2: CLOSED PR treated as successful merge noop
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_merge_noop_if_pr_closed` treats `CLOSED` like `MERGED` and returns `merged` / `admin_merged`. A PR closed without merge can make a re-run report merge success and drive post-merge behavior incorrectly. No-op should apply only when the PR is actually merged (`MERGED` or `mergedAt`), with fail-closed handling for unmerged `CLOSED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: No-op only when state is MERGED (or mergedAt set); fail-closed for CLOSED unmerged.
  - From cursor-specialist-edge-cases-output.txt: Only noop on state MERGED; handle CLOSED explicitly (error or verify mergedAt).


### FINDING_20: copytree preserves symlinks that may escape run dir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `copytree(symlinks=True)` when publishing the tmpdir run tree can preserve symlinks pointing outside the run directory, so committed artifacts may reference sensitive host paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject symlinks whose targets escape the run dir or copy without preserving external symlinks; document trust boundary if intentional.


### FINDING_21: gh body-file paths do not fail-closed on redaction truncation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_body_file_args` and related `issue_comment_patch` / `pr_edit_body` paths do not abort when redaction emits truncation markers (`[content truncated ...]`). Partially redacted PR/issue bodies can still be written via `gh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add shared fail-closed redaction helper; abort before any gh write on truncation marker.
  - From cursor-specialist-edge-cases-output.txt: Raise ShipError when [content truncated appears, matching tracking_issue/pr_body.


### FINDING_23: ensure_pr returns status created after create-conflict recovery
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `ensure_pr` always returns `status=created` after `pr_create`, even when recovery finds an existing PR or `pr_for_branch` already had one. Idempotency and logging mis-route on the existing-PR path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Set status existing when pr_create recovers or pr_for_branch already existed.


### FINDING_24: _version_race_gate raises via git.log_subjects instead of MERGE_RESULT_ERROR
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_version_race_gate` uses raising `git.log_subjects`; when `git log origin/main..HEAD` fails, `merge_pr` raises `ShipError` instead of returning the `error` merge literal, diverging from bash skip-on-failure behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use try_log_subjects or catch ShipError; align with bash skip-on-failure or return error literal.


### FINDING_25: post-flush skipped on MERGED/CLOSED noop paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-flush-boundary-output.txt
- **Severity**: latent
- **Concern**: Idempotent paths after `flush_logs_pre` can return from `_merge_noop_if_pr_closed` without `_post_flush`, leaving tmpdir manifest partial and skipping post-merge token/timing refresh (including re-entry after pre-flush committed log batches). Bash finalizes manifest in postmerge only after successful merge outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Call flush_logs_post on noop when post-merge work not done, or require driver-only post-flush.
  - From dyn-flush-boundary-output.txt: Call `_post_flush(ctx)` before returning the terminal `MergeResult` from the post–`flush_logs_pre` noop check (or only when `pr.state` is `MERGED`/`CLOSED` and pre was not skipped).


### FINDING_27: oos _rejected_section counts markers past next non-rejected heading
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_rejected_section()` returns body from the first rejected heading through end-of-string, while bash `count_rejected_oos_markers_from_ndjson()` stops at the next `##` heading that is not itself a rejected heading. `OOS_<n>` tags in later sections can inflate `rejected_markers` and let Python `disposition_ok()` pass when bash `oos-disposition-gate.sh` would exit 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Port the awk slice (scan lines after the rejected heading, `print` only until a non-rejected `^## ` heading) into `_rejected_section()` or `_count_rejected_markers()`, and add a fixture with `## Rejected` followed by another `##` section containing `OOS_99` to lock parity with `skills/implement/scripts/test-oos-disposition-gate.sh`.


### FINDING_28: oos _count_non_security JSON/title heuristic diverges from bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_count_non_security()` counts `"title"` keys when `"phase": "implement"` or `"accepted"` appears for files without `^### OOS_` headers, while bash always runs `oos-non-security-block-count.awk` and returns 0 for such files. Python can require inline-triage coverage where bash would treat `non_security_oos == 0` and exit 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Drop the JSON/`"title"` heuristic and always use `_count_non_security_markdown()` (awk parity), or gate the JSON branch behind an explicit format flag not used by the disposition gate.


### FINDING_29: oos filed-URL regex allows non-GH_HOST hosts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `_GITHUB_ISSUE_URL` matches issue URLs on any host, while bash builds the ERE from `github.com` or `GH_HOST` only. Off-host or typo URLs can satisfy `filed > 0` in Python when bash would not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port GH_HOST-aware URL ERE from oos-disposition-shared.inc.bash.
  - From dyn-bash-parity-output.txt: Thread `GH_HOST` (default `github.com`) into `disposition_ok()` and restrict the loose URL regex to the same host alternation as `_oos_github_issue_url_ere()`.


### FINDING_3: session transcript not discovered on pre-push flush
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `capture_session_transcript` only copies an empty `session-transcript-refresh.txt` stub without bash-style discovery/redaction. Pre-push flush can commit an empty session transcript under `larch-logs` while live Claude JSONL exists on disk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port capture-session-transcript.sh discovery/redaction or invoke script via Runner.


### FINDING_30: pr_body flowchart pipe detection rejects quoted pipes bash accepts
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_PIPE_IN_BRACKETS` does not implement bash `sanitize-mermaid-fragment.sh` depth/quote-aware scanning. Bash accepts quoted node labels with pipes (e.g. `A["foo|bar"]`); Python rejects them. Phase 7 could drop Mermaid diagrams bash would embed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Port the awk `flowchart_reject()` character scanner (depth + quote/escape) or call the existing `.sh` sanitizer in parity tests and production until a faithful port exists; extend `python/test_pr_body_bash_parity.py` with the quoted-pipe `ok` fixtures from `scripts/test-mermaid-fragments.sh`.


### FINDING_31: flush_logs_post sets manifest status=done on failed merge outcomes
- **Reviewer(s)**: dyn-flush-boundary-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` always sets `manifest.status = "done"`, but `merge_pr` calls `_post_flush` after `flush_logs_pre` on every terminal path, including failures (`main_advanced`, `ci_not_ready`, `version_already_published`, `policy_denied`, `admin_failed`, `error`). Incomplete runs are marked finished in the tmpdir manifest, diverging from bash (`ship-pr.sh` only finalizes in postmerge after successful merge results).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-boundary-output.txt: Split “tmpdir token/timing refresh” from “finalize manifest to done”; only set `MANIFEST_STATUS_DONE` when `merge_outcome.result` is `merged` or `admin_merged` (or when the driver has set post-merge state). On non-success merge outcomes, re-render batches if needed but leave `status=partial`.


### FINDING_36: ensure_pr push vs force_push_recovery branch name mismatch
- **Reviewer(s)**: dyn-force-push-paths-output.txt
- **Severity**: important
- **Concern**: On the existing-OPEN-PR path, plain push uses `git push -u origin HEAD` (symbolic-ref branch) while `force_push_recovery(..., branch=ctx.branch)` pushes `refs/heads/{ctx.branch}`. If `RunContext.branch` diverges from checked-out HEAD, recovery can update a different remote ref than the failed push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-force-push-paths-output.txt: Resolve the branch once with `git.try_current_branch(runner)` (or pass `branch=None` into `force_push_recovery`), fail closed when it differs from `ctx.branch`, and use that name for recovery; mirror `create-pr.sh`’s fetch + `branch --set-upstream-to` only if you keep a bare `git push --force-with-lease` path.


### FINDING_37: force_push_recovery uses ctx.branch without HEAD reconciliation
- **Reviewer(s)**: dyn-force-push-paths-output.txt
- **Severity**: important
- **Concern**: When callers pass `branch=ctx.branch` (`merge.py`, `pr.py`), `force_push_recovery` does not reconcile with `try_current_branch` unlike `git-force-push.sh` (HEAD branch). Lease targets `refs/heads/{ctx.branch}` while objects come from HEAD; ctx/HEAD mismatch pushes the wrong ref.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-force-push-paths-output.txt: Always resolve the branch from HEAD inside `force_push_recovery`, treat an explicit `branch` only as a validation hint (error if it disagrees with HEAD), or drop the parameter and use HEAD only.


### FINDING_38: force_push_recovery maps git status failure to dirty_worktree
- **Reviewer(s)**: dyn-force-push-paths-output.txt
- **Severity**: important
- **Concern**: When `git status --porcelain` fails (`returncode != 0`), `force_push_recovery` returns `status="dirty_worktree"`. Bash `git-force-push.sh` exits 2 on inspection failure and 1 only for non-empty porcelain. Callers can mis-report tooling/repo failure as a dirty tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-force-push-paths-output.txt: Return a distinct status (e.g. `status_failed`) or propagate stderr; map that to `MERGE_RESULT_ERROR` / `ShipError` with the underlying message, not `dirty_worktree`.


### FINDING_4: flush_logs_post lacks tmpdir final-report re-render
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `flush_logs_post` does not re-render final-report/summary per plan. Post-merge tmpdir may lack updated final-summary material the bash post-merge path would produce before manifest finalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add tmpdir-only final-report pass before manifest status=done.


### FINDING_5: corrupt manifest resets instead of recovering from run dir
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Invalid/corrupt `manifest.json` with a valid `run_id` falls through to `init_run` instead of rebuilding from on-disk batches in the run directory. Mid-run truncation can drop `steps_ran`; a subsequent flush may overwrite with a fresh partial manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Recover from on-disk batches before init_run fallback.
  - From cursor-specialist-edge-cases-output.txt: Rebuild manifest from run-dir artifacts before init_run reset.
  - From cursor-specialist-testing-output.txt: Write invalid JSON manifest fixture; assert recovery/init without exception.
  - From cursor-specialist-plan-fidelity-output.txt: Add test with invalid JSON asserting load_or_recover_manifest rebuilds


### FINDING_6: merge_pr routing and MERGE_RESULT literals undertested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Unit/integration tests do not exhaustively cover all eight `MERGE_RESULT` literals or key admin/version/CI/policy paths. Regressions in admin-first merge, CI gate, or routing may pass CI until live cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add parametrized routing table tests and mock assertions on flush_logs_pre/post.
  - From cursor-specialist-testing-output.txt: Add scripted RecordingRunner tests that assert each merge_pr return literal and key stderr redaction.
  - From cursor-specialist-plan-fidelity-output.txt: Add table-driven merge_pr tests with scripted Runner responses per merge-pr.sh subtests


### FINDING_7: empty/non-numeric issue crashes ensure_pr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `int(ctx.issue)` on the existing-PR path raises `ValueError` when `RunContext.issue` is empty or non-numeric, instead of a fail-closed `ShipError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Validate issue number and raise ShipError fail-closed.


### FINDING_9: bash parity harness missing K1/P1/N1/N2a and full literal matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_merge_bash_parity.py` covers only a subset of `scripts/test-merge-pr.sh` (e.g. BEHIND→`main_advanced`), not K1/P1/N1/N2a and other merge/flush-recovery classifications. Python `merge.py` can diverge from `merge-pr.sh` while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port test-merge-pr.sh cases (K1 P1 N1 N2a minimum) asserting identical MERGE_RESULT from Python merge_pr and bash merge-pr.sh.
  - From cursor-specialist-plan-fidelity-output.txt: Extend parity tests to mirror scripts/test-merge-pr.sh cases K1, P1, N1, N2a (and ideally A–H/J)


