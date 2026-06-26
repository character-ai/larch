### FINDING_1: Code-review log-root resolver omits review/implement tmpdir consumer anchors
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_resolve_voter_calibration_log_root` (used by code-review `agent_voters` dispatch) does not accept `review_tmpdir` / `session_env_path` or read implement-session anchors (`REPO_CWD`, `session-env.sh`, `IMPLEMENT_TMPDIR` / `review_tmpdir/.larch-keepalive` `CLONE_PATH`) that `final_report._implement_repo_root` and `agents._resolve_review_codex_workdir` already use. Dispatch calls `_default_voter_calibration_log_root()` with `design_tmpdir=None` only. When `LARCH_CONSUMER_REPO` and `CLAUDE_PROJECT_DIR` are unset and the plugin subprocess `cwd` is the plugin checkout, resolution falls through to `consumer_repo_root()` from plugin cwd and reads the plugin `larch-logs` tree (or empty) instead of the operator consumer repo, yielding wrong or empty calibration feedback on normal `/implement` Step 5 runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `_resolve_voter_calibration_log_root` with optional `review_tmpdir` (and use `opts.review_tmpdir` from `agent_voters`): after env vars, resolve via `session-env.sh` keys `CLAUDE_PROJECT_DIR` / `REPO_CWD`, then `review_tmpdir/.larch-keepalive` `CLONE_PATH`, mirroring `final_report._implement_repo_root`; pass explicit `--log-root` from that helper. Add a `test_agent_voters.py` or `test_voting.py` case with plugin cwd plus keepalive pointing at a consumer tree with `larch-logs`.
  - From Cursor-Pragmatic: The plan adds `_resolve_voter_calibration_log_root(design_tmpdir=None)` for `agent dispatch-voters`, with precedence ending in `consumer_repo_root()` from plugin subprocess cwd. It never accepts `review_tmpdir` / `session_env_path`, and never reads `IMPLEMENT_TMPDIR/.larch-keepalive` `CLONE_PATH` (the anchor `final_report._implement_repo_root` already uses). When `LARCH_CONSUMER_REPO` and `CLAUDE_PROJECT_DIR` are unset in the child process, `/implement` Step 5 can still snapshot from the plugin checkout `larch-logs` (or empty) instead of the consumer repo, injecting wrong or empty calibration on the main code-review path. Extend `_resolve_voter_calibration_log_root` with an optional `implement_tmpdir` (derive from `Path(review_tmpdir).parent` when it holds `session-env.sh` or `.larch-keepalive`). Insert keepalive `CLONE_PATH` (and optionally reuse `final_report._implement_repo_root`) before bare `consumer_repo_root()`. Pass that tmpdir from `agent_voters.dispatch_voters` into snapshot creation; add a harness where env anchors are unset but keepalive points at the consumer tree.

### FINDING_2: Prompt-missing relaunches are not wired into waterfall control flow
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: The plan says `_prompt_file_for_tool` may return `None` and the slot must be dropped, but phase1/phase2/phase3 loops still unconditionally append `_launch_slot(...)` results. Missing `prompt_files[tool]` cases would still try to launch or break collection instead of using existing drop semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the waterfall phase loops to handle a nullable launch result or explicit drop sentinel, and record the slot as dropped before collection when the resolved prompt is absent.

### FINDING_3: Code-review dispatch never pins `no_fallback=False` for launch-tool enumeration
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds `_launchable_base_tools_for_slot(..., no_fallback: bool)` and `_first_launch_base_tool_for_slot` but only plan-review semantics are discussed. `review.voters` omits `--no-fallback` on waterfall dispatch today. If the helper defaults to plan-review `no_fallback=True`, or copies plan-review call sites, code-review can omit phase-2/phase-3 tools from calibration renders and `prompt_files` maps while waterfall still substitutes Cursor/Claude, recreating mis-attribution and missing feedback on fallback launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `dispatch_voters`, call both helpers with `no_fallback=False` for `review.voters`. Add an explicit test in `python/test_agent_voters.py` that codex-absent voter 2/3 paths still render cursor-calibrated prompts and manifest `prompt_files["cursor"]`.

### FINDING_4: `_make_voter_prompt` extension omits slot-aware output paths required by `prompt_files` manifests
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan names per-slot files such as `codex-plan-voter-prompt-codex.txt` / `codex-plan-voter-prompt-claude.txt` and `cursor-plan-voter-prompt-cursor.txt`, but only extends `_make_voter_prompt` with `calibration_stats_file` and `voter_tool`. The current helper always writes `{tool}-plan-voter-prompt.txt`. Implementing literally still yields one shared `codex-plan-voter-prompt.txt`, so voter-2 `prompt_files` cannot point at distinct per-launch-tool prompts with distinct calibration blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend `_make_voter_prompt` with a slot or `prompt_stem` plus explicit output basename (or derive `{stem}-plan-voter-prompt-{voter_tool}.txt`), pass `--voter-tool` and stats into `render voter`, and build voter-2/3 `prompt_files` from those paths. Assert the exact paths in `python/test_plan_review_panel.py`.

### FINDING_5: Snapshot run-dir helper risks circular import and logic drift from `/voter-calibration`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Run-directory derivation is specified as duplicated logic or a direct call to `analyze_issues._ground_truth_run_dir`, but `analyze_issues` already imports `voting` at module load, so a top-level `voting -> analyze_issues` import creates a circular-import trap. A copy-paste in `voting.py` can also drift from `/voter-calibration` and ground-truth windowing, skewing recency ordering and rollups.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extract `_ground_truth_run_dir` (and timestamp reader if needed) into a small shared module imported by both `analyze_issues` and `voting`, or move the helper into `voting.py` and repoint `analyze_issues` to import it. State the chosen ownership explicitly in the plan.
  - From Cursor-Pragmatic: The plan tells `voting.py` to call `analyze_issues._ground_truth_run_dir` / `_ground_truth_run_started_at`, but `analyze_issues` already imports `voting` at module load. A top-level import in `voting.py` creates a circular import and can break snapshot CLI or dispatch. Move `_ground_truth_run_dir` and the manifest timestamp reader into `voting.py` (or a small shared module both import). Keep thin wrappers in `analyze_issues` for ground-truth callers. Have the new snapshot discovery call the `voting` helpers directly; do not add `voting -> analyze_issues` imports.

### FINDING_6: `/voter-calibration` analyzer not wired through base-tool rollup helper
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds base-tool normalization in `python/voting.py`, but it never wires the existing `/voter-calibration` analyzer through that helper, so the report still splits codex-plan-fidelity, codex-pragmatism, and cursor-validity into separate rows instead of one base-tool rollup. That leaves the advertised per-voter-tool validation path fragmented, so the new incentive cannot be measured the way the feature description requires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update skills/voter-calibration/scripts/voter-calibration.py to reuse the new base-tool rollup helper for its global section, and refresh skills/voter-calibration/scripts/test-voter-calibration.sh to expect merged codex and cursor rows.

### FINDING_7: Test plan omits `design_tmpdir` fallback branch for log-root resolution
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The test plan covers consumer-root resolution only with env vars set, but it never exercises the `design_tmpdir` fallback branch of `_resolve_voter_calibration_log_root` that plan-review dispatch will use when `LARCH_CONSUMER_REPO` and `CLAUDE_PROJECT_DIR` are absent. A regression in that branch could still point plan-review at the plugin checkout's `larch-logs`, feeding prompt feedback from the wrong corpus on the main dispatch path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a focused integration test that unsets the consumer-repo env vars, supplies a design tmpdir rooted in a consumer worktree, and asserts the snapshot argv targets that worktree's larch-logs.
```

**Merge notes**

- **FINDING_1 + FINDING_6** → merged **FINDING_1** (same code-review log-root gap; different anchor wording).
- **FINDING_5 + FINDING_7** → merged **FINDING_5** (same circular-import / run-dir ownership risk).
- **FINDING_2, 3, 4, 8, 9** kept separate (distinct fixes or paths).
- No `[OUT_OF_SCOPE]` inputs; no empty merge attestation.
