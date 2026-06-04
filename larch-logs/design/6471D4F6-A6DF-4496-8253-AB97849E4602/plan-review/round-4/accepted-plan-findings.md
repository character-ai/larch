### FINDING_1: Restart after cone-only reconcile
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Release Step 7 may repair/reconcile the marketplace sparse cone without changing the installed version, but Step 8 only requires a Claude restart when a new version was installed. That can leave Claude running with stale plugin state after a same-version cone repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend Step 7 to record cone-only reconcile (parse script output or exit semantics) and Step 8 to require restart when Step 7 reconciled the cone even if NEW_VERSION equals CURRENT_VERSION


### FINDING_2: Release Step 7 can bind to the wrong cache root
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-dyn-release-root-resolution, Codex-dyn-release-root-resolution
- **Severity**: important
- **Concern**: Release Step 7 can prefer the prepare-time `CURRENT_VERSION` cache directory over the actual active/installed plugin root. If the operator is running another cached version, `upgrade-larch.sh` can derive `INSTALLED_VERSION` from the wrong root, protect the wrong directory during prune, and potentially remove the live active cache root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Resolve the installed or active cache root first via CLAUDE_PLUGIN_ROOT and plugin metadata; use the CURRENT_VERSION cache dir only after confirming it matches the installed version or only as a non-prune fallback
  - From Codex-Edge: Prefer the actual installed larch version/root from claude plugin metadata or installed_plugins.json before CURRENT_VERSION. Use CURRENT_VERSION only when metadata is unavailable or confirms the active installed version matches it.
  - From Cursor-dyn-release-root-resolution: Reorder resolution: parse installed version / validate session `CLAUDE_PLUGIN_ROOT` first; use prepare `CURRENT_VERSION` only when it matches installed metadata or drop it; reuse `get_installed_larch_version` logic from `upgrade-larch.sh:113-139`
  - From Codex-dyn-release-root-resolution: Prefer a valid cache-shaped CLAUDE_PLUGIN_ROOT and installed-metadata-derived root before CURRENT_VERSION, or only accept CURRENT_VERSION when it matches the parsed installed version. Document that CURRENT_VERSION comes from Step 2 classify output and is not proof of the active cache root.


### FINDING_3: Upgrade retention tests need hermetic HOME
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Planned cone-match and already-latest tests source `upgrade-larch.sh` without first isolating `HOME`, while `MARKETPLACE_CLONE` is fixed from `$HOME` at source time. The tests may hit or mutate the developer’s real marketplace clone, pass vacuously, or flake under a clean environment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Create TMP and export HOME="$TMP" before sourcing upgrade-larch.sh; document that requirement in the harness header
  - From Cursor-Innovation: State explicitly in the retention harness section: export `HOME="$TMP/home"` (or equivalent), create `$HOME/.claude/plugins/marketplaces/larch-local`, and reset/marketplace state per case before calling `marketplace_sparse_cone_matches` / `already_latest_and_cone_ok`
  - From Cursor-Requirements: Add plan step to export HOME to a tmp fixture (fake marketplace under $HOME/.claude/plugins/marketplaces/larch-local) in test-upgrade-larch-retention.sh, mirroring test-sessionstart-health.sh.


### FINDING_4: Subshell drift probe can lose append_msg advisory
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The SessionStart plan permits running the drift probe in a subshell while using `append_msg`, but `append_msg` mutates parent-shell state. A mismatch detected inside the subshell may be discarded before the parent emits the advisory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep append_msg in the parent shell: use set +e/restore around the probe, or have any subshell return a simple mismatch flag/string and call append_msg after it exits


### FINDING_5: SECURITY.md missing for SessionStart hook surface change
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes SessionStart hook behavior by sourcing a runtime lib and probing the marketplace git clone, but does not update `SECURITY.md` or justify why the change is not security-relevant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a concise SECURITY.md note for the sparse-cone probe covering fail-open behavior, no mutation, fixed advisory text, and cwd-independent sourcing, or explicitly state why this hook change is not security-relevant


### FINDING_7: Release cache fallback ambiguity is underspecified
- **Reviewer(s)**: Codex-dyn-release-root-resolution
- **Severity**: important
- **Concern**: The release Step 7 fallback allows choosing an “unambiguous” valid cache version directory, but does not define ambiguity or what to do when zero or multiple version-shaped cache directories exist. An implementer could pick an arbitrary stale root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-release-root-resolution: Specify the minimum rule: unambiguous means exactly one version-shaped directory under $HOME/.claude/plugins/cache/larch-local/larch; if zero or more than one exist, do not choose a cache fallback, warn, and use the existing Skill-tool/no-install fallback.


### FINDING_8: SessionStart probe tests miss required guard cases
- **Reviewer(s)**: Cursor-dyn-hook-probe-completeness, Codex-dyn-hook-probe-completeness
- **Severity**: important
- **Concern**: The SessionStart test plan does not cover every safety guard required by the probe spec, including empty `HOME`, marketplace directory without `.git`, `larch-logs` present, and empty configured/expected sparse-checkout inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-hook-probe-completeness: Add explicit harness cases empty HOME unset no advisory non-git marketplace dir silent larch-logs present with mismatched cone silent empty sparse-checkout list silent exit 0
  - From Codex-dyn-hook-probe-completeness: Add explicit scripts/test-sessionstart-health.sh cases for empty HOME, existing marketplace dir without .git, larch-logs present, and empty configured/expected compare inputs; keep the existing missing-lib/function cases.

