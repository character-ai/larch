### FINDING_1: Thread canonical_tmp through the inner pin-phase helper
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan threads `canonical_tmp` into `_run_contains_pin_phase` at the outer level, but the inner helper that actually makes the calls never receives it. That leaves the pin-phase path either ambient or signature-broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add canonical_tmp: Path to _run_relevant_checks_inner, pass it from _run_relevant_checks_impl at the sole call site, then forward it to both _run_contains_pin_phase invocations
  - From Cursor-Pragmatic: Add canonical_tmp: Path to _run_relevant_checks_inner and pass it from _run_relevant_checks_impl before forwarding to _run_contains_pin_phase at lines 1061 and 1092
  - From Codex-Pragmatic: Add `canonical_tmp` to `_run_relevant_checks_inner`, pass it from `_run_relevant_checks_impl`, and forward it to both `_run_contains_pin_phase` calls.
  - From Cursor-Requirements: Add `canonical_tmp: Path` to `_run_relevant_checks_inner`, pass it from `_run_relevant_checks_impl`, then forward to both `_run_contains_pin_phase` calls


### FINDING_2: Thread review_tmpdir through the plan-parity validator
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Tmpdir Ratchet Reviewer, Codex-Requirements, Codex-dyn-Tmpdir Ratchet Reviewer
- **Severity**: major
- **Concern**: The review aggregation plan only routes `review_tmpdir` into one scope-splitting path, but the parity-check helper still calls `_run_scope_marker` directly. That leaves a validation path ambient or makes the new signature incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add review_tmpdir: Path to _plan_scope_reduction_parity_ok, pass review_tmpdir from its caller, and forward it to every _run_scope_marker call in that helper
  - From Codex-Pragmatic: Thread `review_tmpdir` through `_plan_scope_reduction_parity_ok` and its caller, then pass it to every `_run_scope_marker` call.
  - From Cursor-Requirements: Add `review_tmpdir: Path` to `_plan_scope_reduction_parity_ok`, pass it from `_apply_aggregate_candidate`, and forward to `_run_scope_marker`
  - From Cursor-dyn-Tmpdir Ratchet Reviewer: Add review_tmpdir to _plan_scope_reduction_parity_ok and pass it from the review_aggregate.py:736 caller
  - From Codex-Requirements: Thread review_tmpdir through _plan_scope_reduction_parity_ok and pass it at both _run_scope_marker calls.
  - From Codex-dyn-Tmpdir Ratchet Reviewer: Thread review_tmpdir through _plan_scope_reduction_parity_ok and pass it at both _run_scope_marker calls.


### FINDING_3: Update transcript-capture tests for run-owned scratch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-Tmpdir Ratchet Reviewer, Codex-Requirements
- **Severity**: major
- **Concern**: The testing plan still points at stale/nonexistent test files and keeps a regression that expects transcript scratch to stay under system TMPDIR. That contract will fail once production moves scratch under the run-owned tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace stale test paths with python/tests/report/test_run_logs.py, python/tests/report/test_run_log_flush.py, python/tests/implement/test_checks.py, and python/tests/design/test_design_lifecycle.py; rewrite or delete test_capture_transcript_main_preserves_system_tmp_render_path to expect run-owned scratch under log_root.parent or explicit --tmpdir
  - From Cursor-Pragmatic: Rewrite or replace that test to expect scratch under log_root.parent or explicit --tmpdir; add python/tests/report/test_run_logs.py to the plan Testing strategy instead of the nonexistent python/test_capture_session_transcript.py
  - From Cursor-dyn-Tmpdir Ratchet Reviewer: Update the testing strategy to python/tests/report/test_run_logs.py and rewrite the preserves_system_tmp test to expect scratch under log_root.parent (or explicit --tmpdir)
  - From Codex-Requirements: Update the testing strategy to python/tests/report/test_run_logs.py and rewrite the preserves_system_tmp test to expect scratch under log_root.parent (or explicit --tmpdir)


### FINDING_4: Bootstrap parse-flags needs a session-owned scratch dir
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Tmpdir Ratchet Reviewer, Codex-dyn-Tmpdir Ratchet Reviewer
- **Severity**: major
- **Concern**: `step0_parse_main` / `_run_parse_argv` runs before `DESIGN_TMPDIR` exists, so the planned `plugin_root.parent` fallback is not a safe run-owned scratch location. Pre-session `larch-argv.*` can land beside the install tree or fail under a bad parent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Thread claude_pid into _run_parse_argv, stage with dir=_parsed_cache_path(claude_pid).parent (mkdir if needed), and drop plugin_root.parent as the primary fallback
  - From Codex-Arch: Use the existing step-0 cache directory, or add a validated bootstrap scratch dir or `$TMPDIR` repair helper, instead of `plugin_root.parent`.
  - From Cursor-Pragmatic: Use dir=_parsed_cache_path(claude_pid).parent or an explicit mkdir of ~/.cache/larch/sessions in _run_parse_argv; document that Step 0-pre cannot use design_tmpdir
  - From Cursor-Requirements: Pin `dir=` to the existing session cache parent (`Path.home() / ".cache" / "larch" / "sessions"`, same family as `_parsed_cache_path`), mkdir it, and drop the `plugin_root.parent` fallback
  - From Codex-Requirements: Add claude_pid to _run_parse_argv and use dir=_parsed_cache_path(claude_pid).parent (mkdir parents); drop plugin_root.parent as the primary fallback
  - From Cursor-dyn-Tmpdir Ratchet Reviewer: Restrict pre-setup scratch to _parsed_cache_path(claude_pid).parent (or another fixed session-cache path), not plugin_root.parent
  - From Codex-dyn-Tmpdir Ratchet Reviewer: Thread a real owned scratch dir into _run_parse_argv, or derive one from the session cache; do not use plugin_root.parent.


### FINDING_8: OOS security-text parsing needs scratch_dir threading
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The plan covers the Gate B branch, but the code-review OOS path also calls `_is_security_text` from `_parse_artifact`. That leaves an ambient TMPDIR staging path in the OOS parsing flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Thread scratch_dir through _parse_artifact into _is_security_text(body scratch_dir=...) not only the Gate B branch at line 335


### FINDING_9: Tempfile-dir baseline needs a stable path convention
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The new lint’s baseline identity convention is unclear for a `python/larch/` scan root. If the stored path prefix does not match the repo-relative convention, suppression and `--write` regeneration will churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Mirror `lint_layering.py`: scan `python/larch/**` but store baseline `file` paths relative to `python/` with the `larch/` prefix


### FINDING_11: Tempfile-dir baseline should not key on reason text
- **Reviewer(s)**: Codex-dyn-Tmpdir Ratchet Reviewer
- **Severity**: major
- **Concern**: The baseline identity currently bakes in the reason string, so reason-only edits churn the identity key and make clean `--write` updates difficult.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Tmpdir Ratchet Reviewer: Keep reason as a required field, but exclude it from the identity key.


### FINDING_1: Empty compose-findings needs conditional scratch-dir handling
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The compose-findings path appears to require a scratch directory too early, which could break the empty-input contract. If no design or implement inputs are present, the command should still be able to emit an empty JSONL output without needing a tempfile or ambient scratch state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Resolve scratch_dir as optional and fail only before branches that actually call _is_security_text or create the Gate B filtered tempfile; keep the no-input path writing an empty output


### FINDING_4: Published design log worktree can be copied into itself
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The disposable publish worktree is placed under the directory that is later iterated and copied into the final design log tree. That makes it possible for the publish step to accidentally include the worktree or repo contents inside the committed output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Do not place the publish worktree directly under the published `design_tmpdir`, or add an explicit exclusion before the copy loop. Use an excluded scratch directory or a run-owned sibling outside the tree being copied.


### FINDING_5: Run-log scratch path can pollute the repo root
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: The run-log scratch directory is routed to `log_root.parent`, which can be the repository root for direct callers. That can create transient files in the working tree and trip clean-tree guards or interrupted-write cleanup paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use `log_root.parent` only when it is an existing session/run tmpdir; otherwise use a larch-owned cache scratch directory such as ~/.cache/larch/sessions after mkdir, and keep the no-ambient-TMPDIR rule

