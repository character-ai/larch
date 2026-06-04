### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/release/SKILL.md:146-181
- **Concern**: Step 7 moves to working-tree bash but Step 8 still restarts only when a new version was installed. Scenario: After RC1 same-version cone reconcile the marketplace allowlist updates but Step 8 omits the restart Claude needs to load the repaired install
- **Proposed resolution**: Extend Step 7 to record cone-only reconcile (parse script output or exit semantics) and Step 8 to require restart when Step 7 reconciled the cone even if NEW_VERSION equals CURRENT_VERSION

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-148
- **Concern**: Proposed Step 7 resolves the CURRENT_VERSION cache dir before the actual installed plugin root. Scenario: If the operator's installed larch is older than the repo CURRENT_VERSION but that CURRENT_VERSION cache dir exists, the working-tree upgrade runs with PLUGIN_ROOT set to the wrong version; upgrade-larch then protects that wrong INSTALLED_VERSION during prune and can remove the active cached plugin root before the required restart
- **Proposed resolution**: Resolve the installed or active cache root first via CLAUDE_PLUGIN_ROOT and plugin metadata; use the CURRENT_VERSION cache dir only after confirming it matches the installed version or only as a non-prune fallback

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh:7-23
- **Concern**: Cone-match harness cases lack isolated HOME before sourcing upgrade-larch.sh. Scenario: MARKETPLACE_CLONE is fixed at source time from real $HOME; new cone tests would read or mutate the developer's live marketplace clone
- **Proposed resolution**: Create TMP and export HOME="$TMP" before sourcing upgrade-larch.sh; document that requirement in the harness header

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/release/SKILL.md:146-149 skills/upgrade-larch/scripts/upgrade-larch.sh:255-308
- **Concern**: Step 7 root resolution can prefer a cached CURRENT_VERSION root over the actual installed root. Scenario: The plan says to use $HOME/.claude/plugins/cache/larch-local/larch/${CURRENT_VERSION} first when it exists. If the operator's active install is behind or otherwise differs but that cache dir remains, upgrade-larch.sh derives INSTALLED_VERSION from the wrong CLAUDE_PLUGIN_ROOT and prune protects the wrong running version, contradicting the plan's prune-safety claim.
- **Proposed resolution**: Prefer the actual installed larch version/root from claude plugin metadata or installed_plugins.json before CURRENT_VERSION. Use CURRENT_VERSION only when metadata is unavailable or confirms the active installed version matches it.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh:1-94
- **Concern**: New cone-match / drift cases omit harness HOME wiring. Scenario: `MARKETPLACE_CLONE` is fixed to `$HOME/.claude/plugins/marketplaces/larch-local` in `upgrade-larch.sh`; the harness uses `mktemp` for cache only and never sets `HOME`, so fake marketplace trees will not be exercised and new tests may pass vacuously or hit the real user clone
- **Proposed resolution**: State explicitly in the retention harness section: export `HOME="$TMP/home"` (or equivalent), create `$HOME/.claude/plugins/marketplaces/larch-local`, and reset/marketplace state per case before calling `marketplace_sparse_cone_matches` / `already_latest_and_cone_ok`

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:38-43
- **Concern**: Plan permits isolating the whole drift probe in a subshell while also using append_msg, but append_msg only mutates parent-shell MSG. Scenario: A mismatched sparse cone is detected inside the subshell, append_msg runs, then the subshell exits and the parent emits no advisory
- **Proposed resolution**: Keep append_msg in the parent shell: use set +e/restore around the probe, or have any subshell return a simple mismatch flag/string and call append_msg after it exits

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh:133-151; plan.txt:133-151
- **Concern**: Planned cone/already_latest tests omit hermetic HOME for MARKETPLACE_CLONE. Scenario: upgrade-larch.sh hardcodes MARKETPLACE_CLONE to $HOME/.claude/plugins/marketplaces/larch-local; the retention harness never threads HOME (unlike the planned sessionstart changes). New marketplace_sparse_cone_matches / already_latest_and_cone_ok cases would hit the operator real marketplace or flake under env -i.
- **Proposed resolution**: Add plan step to export HOME to a tmp fixture (fake marketplace under $HOME/.claude/plugins/marketplaces/larch-local) in test-upgrade-larch-retention.sh, mirroring test-sessionstart-health.sh.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:139-149
- **Concern**: Plan changes the SessionStart hook security surface but omits SECURITY.md. Scenario: The hook will start sourcing a new runtime lib and probing the marketplace git clone, while SECURITY.md continues to describe only the old SessionStart advisory behavior despite the repo rule to update SECURITY.md for security-relevant changes
- **Proposed resolution**: Add a concise SECURITY.md note for the sparse-cone probe covering fail-open behavior, no mutation, fixed advisory text, and cwd-independent sourcing, or explicitly state why this hook change is not security-relevant

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-shell-root-binding
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:19-23,121-123; <TMPDIR>/plan.txt:88-89
- **Concern**: SessionStart plan still allows sourcing lib-sparse-dirs.sh through CLAUDE_PLUGIN_ROOT instead of the executing script tree. Scenario: Current sessionstart-health.sh already has SCRIPT_DIR before the probe and does not define PLUGIN_ROOT until the later HOOK_CWD block. If the allowed alternative is implemented, a mismatched CLAUDE_PLUGIN_ROOT can make the new hook read an older cache root's allowlist and miss drift, repeating the stale-root failure shape for the warning path.
- **Proposed resolution**: Remove the CLAUDE_PLUGIN_ROOT alternative for this probe. Require source "$SCRIPT_DIR/lib-sparse-dirs.sh" or derive any root only from SCRIPT_DIR, and keep later PLUGIN_ROOT out of the allowlist path.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-release-root-resolution
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:117-121
- **Concern**: Step 7 resolves `RESOLVED_ROOT` with prepare-time `CURRENT_VERSION` before installed metadata and `CLAUDE_PLUGIN_ROOT`. Scenario: `CURRENT_VERSION` is the Step 2 prepare KV (pre-bump main semver per `.claude/skills/release/scripts/release-prepare.md:21`), not necessarily the running install. If `$HOME/.claude/plugins/cache/larch-local/larch/${CURRENT_VERSION}` exists while Claude is on another cached version, `CLAUDE_PLUGIN_ROOT` targets the wrong tree; `upgrade-larch.sh` prune protects `basename "$PLUGIN_ROOT"` (`upgrade-larch.sh:255-265`) and can delete the live cache dir
- **Proposed resolution**: Reorder resolution: parse installed version / validate session `CLAUDE_PLUGIN_ROOT` first; use prepare `CURRENT_VERSION` only when it matches installed metadata or drop it; reuse `get_installed_larch_version` logic from `upgrade-larch.sh:113-139`

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-release-root-resolution
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-149 (proposed replacement in plan.txt:117-121)
- **Concern**: The last cache fallback says to choose an existing valid cache version dir only if unambiguous, but the plan does not define ambiguity or the required action when multiple dirs remain.. Scenario: If CURRENT_VERSION root is missing, CLAUDE_PLUGIN_ROOT is unusable, installed metadata cannot be parsed, and two valid cache dirs remain after a failed prune, the Step 7 prose leaves the implementer free to pick one arbitrarily. Existing prune behavior can leave extra dirs after rm failure at skills/upgrade-larch/scripts/upgrade-larch.sh:291-294 and docs/installation-and-setup.md:42 documents that failed removals can remain.
- **Proposed resolution**: Specify the minimum rule: unambiguous means exactly one version-shaped directory under $HOME/.claude/plugins/cache/larch-local/larch; if zero or more than one exist, do not choose a cache fallback, warn, and use the existing Skill-tool/no-install fallback.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-release-root-resolution
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-149 (proposed replacement in plan.txt:117-123); .claude/skills/release/scripts/release-prepare.sh:251-253; .claude/skills/release/scripts/classify-bump.sh:97-109
- **Concern**: The plan tries the CURRENT_VERSION cache dir before the actual installed/cache root, but CURRENT_VERSION is derived from release classification of origin/main, not from the active larch install.. Scenario: If the operator's installed larch is behind but a newer CURRENT_VERSION cache dir still exists, Step 7 can pass a non-active CLAUDE_PLUGIN_ROOT. The upgrade script then derives LARCH_CACHE_DIR and INSTALLED_VERSION from that root at skills/upgrade-larch/scripts/upgrade-larch.sh:305-309 and protects that basename during prune at skills/upgrade-larch/scripts/upgrade-larch.sh:255-263, so it can protect the wrong cached version.
- **Proposed resolution**: Prefer a valid cache-shaped CLAUDE_PLUGIN_ROOT and installed-metadata-derived root before CURRENT_VERSION, or only accept CURRENT_VERSION when it matches the parsed installed version. Document that CURRENT_VERSION comes from Step 2 classify output and is not proof of the active cache root.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-hook-probe-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:154-163
- **Concern**: SessionStart test-extension list does not cover every probe guard named in the hook spec. Scenario: Plan lines 92-100 and edge case line 193 require skip paths for empty HOME missing .git larch-logs present empty configured or expected and silent non-mutation but lines 158-163 only name drift match no-clone missing-lib and PLUGIN_ROOT or HOOK_CWD independence Implementer can ship a probe that mishandles those guards with no harness failure
- **Proposed resolution**: Add explicit harness cases empty HOME unset no advisory non-git marketplace dir silent larch-logs present with mismatched cone silent empty sparse-checkout list silent exit 0

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-hook-probe-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:88-100,157-163,204-207
- **Concern**: SessionStart test-extension plan does not cover every safety guard listed for the probe. Scenario: The probe requirements name empty HOME, missing .git, larch-logs present, missing lib, missing normalize_sparse_dirs, and empty compare inputs, but the planned test cases only cover drift, match, no clone, missing lib or function, and path independence. No-clone is not a missing-.git case, and there is no explicit empty-HOME, larch-logs-present, or empty-compare-input case.
- **Proposed resolution**: Add explicit scripts/test-sessionstart-health.sh cases for empty HOME, existing marketplace dir without .git, larch-logs present, and empty configured/expected compare inputs; keep the existing missing-lib/function cases.
