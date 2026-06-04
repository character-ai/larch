### [Plan Review] FINDING_1

### FINDING_1: Already-latest upgrade path must preserve stamp and prune
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned RC2/idempotency rewrite risks exiting the already-latest-and-cone-ok path before preserving the existing `write_install_stamp` and `prune_cached_versions` behavior, regressing cache retention and stamp updates when no reinstall is needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep the existing block: set `ACTUAL_VERSION`, call `write_install_stamp` and `prune_cached_versions`, then print "No upgrade needed" and `exit 0`
  - From Cursor-Edge, Cursor-Innovation: carry write_install_stamp and prune_cached_versions into the already_latest_and_cone_ok branch before the no-upgrade exit message


### [Plan Review] FINDING_3

### FINDING_3: SessionStart drift warning adds unnecessary hook surface
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Adding a warn-only SessionStart sparse-cone drift probe introduces hook complexity, docs/tests/security churn, and per-session maintenance surface even though the actual defect is already repaired by `/upgrade-larch` and `/release`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Drop the SessionStart drift-warning portion and its related docs/tests/security updates; keep the minimum repair in `upgrade-larch.sh` and release Step 7/8 restart handling


### [Plan Review] FINDING_8

### FINDING_8: SessionStart HOME fixture tests need helper-local env injection
- **Reviewer(s)**: Codex-dyn-home-fixture-isolation
- **Severity**: important
- **Concern**: The plan says to thread `HOME` through SessionStart test helpers, but does not specify the `env -i` assignment shape needed to preserve it. If `HOME` is exported outside the helper or placed before `env -i`, the hook can run with empty `HOME`, causing sparse-cone probe tests to pass without exercising the intended fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-home-fixture-isolation: Revise the plan to require helper-local env injection, e.g. env -i HOME="$home_dir" PATH="$bin" "$BASH_BIN" "$SCRIPT" and env -i HOME="$home_dir" PATH="$bin" XDG_CACHE_HOME="$xdg_cache" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$BASH_BIN" "$SCRIPT".

