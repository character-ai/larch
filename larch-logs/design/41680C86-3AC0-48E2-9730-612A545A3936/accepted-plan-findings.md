### FINDING_1: Code-review log-root resolver omits review/implement tmpdir consumer anchors
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_resolve_voter_calibration_log_root` (used by code-review `agent_voters` dispatch) does not accept `review_tmpdir` / `session_env_path` or read implement-session anchors (`REPO_CWD`, `session-env.sh`, `IMPLEMENT_TMPDIR` / `review_tmpdir/.larch-keepalive` `CLONE_PATH`) that `final_report._implement_repo_root` and `agents._resolve_review_codex_workdir` already use. Dispatch calls `_default_voter_calibration_log_root()` with `design_tmpdir=None` only. When `LARCH_CONSUMER_REPO` and `CLAUDE_PROJECT_DIR` are unset and the plugin subprocess `cwd` is the plugin checkout, resolution falls through to `consumer_repo_root()` from plugin cwd and reads the plugin `larch-logs` tree (or empty) instead of the operator consumer repo, yielding wrong or empty calibration feedback on normal `/implement` Step 5 runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `_resolve_voter_calibration_log_root` with optional `review_tmpdir` (and use `opts.review_tmpdir` from `agent_voters`): after env vars, resolve via `session-env.sh` keys `CLAUDE_PROJECT_DIR` / `REPO_CWD`, then `review_tmpdir/.larch-keepalive` `CLONE_PATH`, mirroring `final_report._implement_repo_root`; pass explicit `--log-root` from that helper. Add a `test_agent_voters.py` or `test_voting.py` case with plugin cwd plus keepalive pointing at a consumer tree with `larch-logs`.
  - From Cursor-Pragmatic: The plan adds `_resolve_voter_calibration_log_root(design_tmpdir=None)` for `agent dispatch-voters`, with precedence ending in `consumer_repo_root()` from plugin subprocess cwd. It never accepts `review_tmpdir` / `session_env_path`, and never reads `IMPLEMENT_TMPDIR/.larch-keepalive` `CLONE_PATH` (the anchor `final_report._implement_repo_root` already uses). When `LARCH_CONSUMER_REPO` and `CLAUDE_PROJECT_DIR` are unset in the child process, `/implement` Step 5 can still snapshot from the plugin checkout `larch-logs` (or empty) instead of the consumer repo, injecting wrong or empty calibration on the main code-review path. Extend `_resolve_voter_calibration_log_root` with an optional `implement_tmpdir` (derive from `Path(review_tmpdir).parent` when it holds `session-env.sh` or `.larch-keepalive`). Insert keepalive `CLONE_PATH` (and optionally reuse `final_report._implement_repo_root`) before bare `consumer_repo_root()`. Pass that tmpdir from `agent_voters.dispatch_voters` into snapshot creation; add a harness where env anchors are unset but keepalive points at the consumer tree.


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


