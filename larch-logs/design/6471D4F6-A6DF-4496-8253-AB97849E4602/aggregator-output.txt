### FINDING_1: Already-latest upgrade path must preserve stamp and prune
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned RC2/idempotency rewrite risks exiting the already-latest-and-cone-ok path before preserving the existing `write_install_stamp` and `prune_cached_versions` behavior, regressing cache retention and stamp updates when no reinstall is needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep the existing block: set `ACTUAL_VERSION`, call `write_install_stamp` and `prune_cached_versions`, then print "No upgrade needed" and `exit 0`
  - From Cursor-Edge, Cursor-Innovation: carry write_install_stamp and prune_cached_versions into the already_latest_and_cone_ok branch before the no-upgrade exit message

### FINDING_2: Release Step 7 should prefer active cache root over installed metadata
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-dyn-sourcing-root-split
- **Severity**: important
- **Concern**: The proposed release Step 7 root-resolution order prefers plugin-list/installed metadata before an existing cache-shaped `CLAUDE_PLUGIN_ROOT`. In a no-restart or retried release session, metadata may point at a newer installed cache while the active Claude process is still running from an older cache, causing prune/stamp logic to protect the wrong version and undermining the active-root safety invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Codex-Edge: Prefer an existing cache-shaped CLAUDE_PLUGIN_ROOT as the active prune context before metadata-derived cache roots; use metadata only when no valid active root is available, or keep separate active-root and installed-version concepts.
  - From Codex-Pragmatic: Prefer a valid cache-shaped CLAUDE_PLUGIN_ROOT as RESOLVED_ROOT before plugin metadata, or otherwise protect both the active root version and the installed metadata version; use metadata for target validation rather than active-root selection
  - From Codex-dyn-sourcing-root-split: Prefer an existing cache-shaped CLAUDE_PLUGIN_ROOT before plugin-list metadata, or explicitly pass/protect both the active CLAUDE_PLUGIN_ROOT version and the installed metadata version during prune.

### FINDING_3: SessionStart drift warning adds unnecessary hook surface
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Adding a warn-only SessionStart sparse-cone drift probe introduces hook complexity, docs/tests/security churn, and per-session maintenance surface even though the actual defect is already repaired by `/upgrade-larch` and `/release`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Drop the SessionStart drift-warning portion and its related docs/tests/security updates; keep the minimum repair in `upgrade-larch.sh` and release Step 7/8 restart handling

### FINDING_4: Retention harness HOME isolation must account for source-time globals
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-home-fixture-isolation
- **Severity**: important
- **Concern**: The plan requires setting `HOME` before sourcing `upgrade-larch.sh`, but leaves an existing top-level source in place. Because `MARKETPLACE_CLONE` is assigned at source time, cone-related tests that change `HOME` afterward may still read or mutate the developer’s real marketplace path, making tests vacuous or unsafe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Relocate the initial `source` below per-suite `export HOME="$TMP/home"` (and fixture setup), or re-source after each HOME change; alternatively assign `MARKETPLACE_CLONE` inside `marketplace_sparse_cone_matches` from `$HOME` on each call so isolation does not depend on source order
  - From Cursor-dyn-home-fixture-isolation: State explicitly that cone cases must reassign MARKETPLACE_CLONE="$HOME/.claude/plugins/marketplaces/larch-local" after export HOME= (or defer/remove the line-8 source); if re-sourcing, note it reruns upgrade-larch.sh:306-308 and will clobber the harness LARCH_CACHE_DIR override unless reset afterward

### FINDING_5: Root-resolution validation must be required acceptance coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Release Step 7’s root-resolution validation is treated as optional/manual even though it is core to RC1. Without required tests for fallback ordering and ambiguous cache cases, the release path could still stamp/prune the wrong root or fail to apply the allowlist in-cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Make validation required for the root-resolution acceptance cases: parsed installed version wins, CURRENT_VERSION is accepted only on match or sole defensible fallback, 0 or 2+ cache dirs do not pick an arbitrary root, and the resolved-root path invokes the working-tree script with explicit CLAUDE_PLUGIN_ROOT.

### FINDING_6: Step 7 cone-reconcile sentinel must capture stderr explicitly
- **Reviewer(s)**: Codex-dyn-release-cone-detection
- **Severity**: important
- **Concern**: Step 7 says to parse stdout/stderr for the reconcile sentinel, but the concrete command does not capture output or redirect stderr. Since the upgrade script’s diagnostics use stderr after quiet initialization, the cone-only repair path can emit the sentinel while Step 7 fails to record it, causing Step 8 to skip the required restart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-release-cone-detection: Change Step 7 to a concrete captured form, e.g. upgrade_out=$(CLAUDE_PLUGIN_ROOT="$RESOLVED_ROOT" bash "$PWD/skills/upgrade-larch/scripts/upgrade-larch.sh" 2>&1); upgrade_rc=$?; then parse upgrade_out for the fixed reconcile fragments. Drop the same-version reinstall inference, or replace it with an explicit script-emitted CONE_RECONCILED=true contract.

### FINDING_7: CONE_RECONCILED needs a concrete cross-step state contract
- **Reviewer(s)**: Codex-dyn-release-cone-detection
- **Severity**: important
- **Concern**: Step 8 depends on `CONE_RECONCILED`, but the plan only describes persisting a boolean informally and does not define a state holder across separate skill steps or Bash fences. The restart instruction can be lost after cone-only repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-release-cone-detection: Add a minimal concrete state contract: initialize CONE_RECONCILED=false in Step 7, write the parsed value to a temp Step 7 state file under PREPARE_DIR, and have Step 8 read that file before deciding the restart message.

### FINDING_8: SessionStart HOME fixture tests need helper-local env injection
- **Reviewer(s)**: Codex-dyn-home-fixture-isolation
- **Severity**: important
- **Concern**: The plan says to thread `HOME` through SessionStart test helpers, but does not specify the `env -i` assignment shape needed to preserve it. If `HOME` is exported outside the helper or placed before `env -i`, the hook can run with empty `HOME`, causing sparse-cone probe tests to pass without exercising the intended fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-home-fixture-isolation: Revise the plan to require helper-local env injection, e.g. env -i HOME="$home_dir" PATH="$bin" "$BASH_BIN" "$SCRIPT" and env -i HOME="$home_dir" PATH="$bin" XDG_CACHE_HOME="$xdg_cache" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$BASH_BIN" "$SCRIPT".
