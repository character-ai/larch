### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:54-122
- **Concern**: Drift probe sources lib via PLUGIN_ROOT before that variable exists. Scenario: Probe runs in the JQ+GIT block while PLUGIN_ROOT is only set later when HOOK_CWD is set; source fails silently and SessionStart never warns on sparse-cone drift
- **Proposed resolution**: Resolve and source lib-sparse-dirs.sh in the probe via SCRIPT_DIR or CLAUDE_PLUGIN_ROOT with a SCRIPT_DIR/.. fallback; do not reference PLUGIN_ROOT from the HOOK_CWD-only block

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-148
- **Concern**: Step 7 fallback treats a missing CURRENT_VERSION cache dir as no marketplace install. Scenario: The operator may have a marketplace install at an older version, so CUR_ROOT is absent and the fallback can invoke a stale /upgrade-larch path that does not apply the just-released sparse allowlist in this release cycle
- **Proposed resolution**: Distinguish no install from a different installed version; when an installed cache root is resolvable, run the working-tree upgrade-larch.sh with CLAUDE_PLUGIN_ROOT set to that root, otherwise warn and skip/fallback only for true dev-clone/no-install cases

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:54-114; plan.txt:45-53
- **Concern**: SessionStart drift probe cites PLUGIN_ROOT before it is bound. Scenario: Plan places the probe inside the JQ_AVAILABLE && GIT_AVAILABLE block before HOOK_CWD handling; PLUGIN_ROOT is only assigned at line 122 inside if [[ -n "$HOOK_CWD" ]]. Sourcing "$PLUGIN_ROOT/scripts/lib-sparse-dirs.sh" runs with an empty/wrong root, source fails under || true, and drift is never warned even when the marketplace cone is wrong
- **Proposed resolution**: In the drift block set plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" and source "$SCRIPT_DIR/lib-sparse-dirs.sh" (or "$plugin_root/scripts/lib-sparse-dirs.sh"); document that binding in sessionstart-health.md

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/release/SKILL.md:146-148
- **Concern**: Proposed Step 7 only uses the CURRENT_VERSION cache root and falls back to the Skill tool when that root is absent. Scenario: A maintainer whose local plugin is older than CURRENT_VERSION, or whose CURRENT_VERSION cache was pruned, still has a marketplace install but lacks CUR_ROOT; the fallback can run the stale installed upgrade script with the old sparse allowlist, so the just-released allowlist is not applied in the release cycle
- **Proposed resolution**: Before using the Skill-tool fallback, locate an existing larch-local cache root for the actual installed version or another valid numeric cache dir and run the working-tree upgrade-larch.sh with CLAUDE_PLUGIN_ROOT set to that root; reserve the Skill fallback for no cache or marketplace install

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:45-53
- **Concern**: Drift probe sources lib via PLUGIN_ROOT but PLUGIN_ROOT is only assigned inside the HOOK_CWD block. Scenario: Probe sits in the JQ_AVAILABLE&&GIT_AVAILABLE branch outside the work-tree sub-block; PLUGIN_ROOT is set only at lines 121-122 when HOOK_CWD is non-empty. run_from_dir and many real invocations use empty stdin, so PLUGIN_ROOT is unset, source fails silently, and drift is never warned despite a bad marketplace cone
- **Proposed resolution**: Resolve the lib at $SCRIPT_DIR/lib-sparse-dirs.sh (same pattern as lib-quiet.sh on line 21), or set plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" immediately before the probe; do not depend on HOOK_CWD

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/sessionstart-health.sh:54-114 skills/upgrade-larch/scripts/upgrade-larch.sh:21-50
- **Concern**: Proposed SessionStart drift probe and shared sparse-dir library expand the hook surface beyond the release and upgrade fixes. Scenario: Every Claude session would gain new source plus git sparse-checkout comparison logic for a condition that /upgrade-larch already repairs, increasing hook risk and test/docs churn without being required for RC1 or RC2
- **Proposed resolution**: Limit this PR to RC1 and RC2: keep the allowlist in upgrade-larch.sh unless another required runtime consumer remains, drop the SessionStart drift probe and its related docs/tests/agent-lint plumbing, and rely on /upgrade-larch reconcile-on-drift for repair

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-release-coupling
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-149, .claude/skills/release/scripts/release-prepare.sh:251-253, skills/upgrade-larch/SKILL.md:15-19
- **Concern**: Step 7 treats missing $HOME/.claude/plugins/cache/larch-local/larch/${CURRENT_VERSION} as pure-dev fallback, but CURRENT_VERSION is the repo/plugin.json version, not the installed plugin version; the fallback Skill path still runs the installed skill via ${CLAUDE_PLUGIN_ROOT}.. Scenario: If the maintainer's local marketplace install is behind CURRENT_VERSION or that cache dir was pruned, CUR_ROOT is absent even though a marketplace install exists. The fallback invokes the pre-release installed upgrade-larch skill, whose script can use the old sparse allowlist and reintroduce the bootstrap lag RC1 is meant to close.
- **Proposed resolution**: Before falling back to the Skill tool, derive a real installed cache root: prefer CLAUDE_PLUGIN_ROOT when it is an existing larch-local cache version dir, otherwise parse the installed larch version and use $HOME/.claude/plugins/cache/larch-local/larch/$installed_version. Run the working-tree script with that root; reserve Skill fallback for true dev-clone/no marketplace install.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-hook-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:54-114 / scripts/sessionstart-health.sh:121-122
- **Concern**: Drift probe resolves lib via unset PLUGIN_ROOT under set -u. Scenario: Plan places the probe inside the JQ_AVAILABLE && GIT_AVAILABLE block before HOOK_CWD parsing; PLUGIN_ROOT is only assigned inside the later if [[ -n "$HOOK_CWD" ]] block. set +e does not disable set -u, so expanding "$PLUGIN_ROOT/scripts/lib-sparse-dirs.sh" aborts SessionStart before exit 0
- **Proposed resolution**: At probe entry bind plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" (or source "$SCRIPT_DIR/lib-sparse-dirs.sh" directly) before any PLUGIN_ROOT expansion; keep the probe cwd-independent of HOOK_CWD

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-hook-isolation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:17 / plan sessionstart-health section
- **Concern**: Subshell-only wrapper is insufficient for missing normalize_sparse_dirs. Scenario: Plan allows "set +e … set -e or a subshell". A bare ( … ) inherits set -euo pipefail; calling an undefined normalize_sparse_dirs after a silent source still exits 127 and kills the subshell; parent continues but a top-level probe without an inner set +e still violates exit 0 if any step escapes the subshell
- **Proposed resolution**: Treat subshell as requiring inner set +e, or match existing line 127-129: source … || true then declare -F normalize_sparse_dirs before expected=$(normalize_sparse_dirs …); alternatively expected=$(normalize_sparse_dirs 2>/dev/null || true) so missing lib skips without a set +e envelope

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-hook-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:54-127
- **Concern**: Planned drift probe may read PLUGIN_ROOT before it is initialized. Scenario: Current sessionstart-health.sh only assigns PLUGIN_ROOT in the later HOOK_CWD block at lines 121-127, while the plan inserts the probe in the earlier JQ_AVAILABLE && GIT_AVAILABLE block at lines 54-113 and says to resolve "$PLUGIN_ROOT/scripts/lib-sparse-dirs.sh"; with set -u, expanding an unset PLUGIN_ROOT aborts even under set +e before the final exit 0
- **Proposed resolution**: Use the already-initialized SCRIPT_DIR path, e.g. "$SCRIPT_DIR/lib-sparse-dirs.sh", or initialize a local plugin_root before the probe; do not rely on the later HOOK_CWD-only PLUGIN_ROOT assignment

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-hook-isolation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/sessionstart-health.sh:45-53
- **Concern**: Missing lib is swallowed but normalize_sparse_dirs remains unguarded. Scenario: On an older installed tree without scripts/lib-sparse-dirs.sh, source ... 2>/dev/null || true succeeds, but expected=$(normalize_sparse_dirs) then emits "command not found"; under set +e the [ -n "$expected" ] guard is reached with empty expected, but the failure is not silent, and a subshell wrapper can still propagate nonzero unless explicitly neutralized
- **Proposed resolution**: After sourcing, skip unless declare -F normalize_sparse_dirs succeeds, or compute expected with stderr suppressed and || true inside the best-effort block before comparing

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-sync-surfaces
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.md:30-36
- **Concern**: Edit-in-sync list omits `.claude/skills/release/SKILL.md` even though the plan rewrites release Step 7 to invoke working-tree `upgrade-larch.sh` with `CLAUDE_PLUGIN_ROOT` override. Scenario: Allowlist or reconcile semantics change in `lib-sparse-dirs.sh` / `upgrade-larch.sh` can land with release Step 7 still describing Skill-tool-only `/upgrade-larch`, so RC1 never runs in maintainer releases
- **Proposed resolution**: Add `.claude/skills/release/SKILL.md` (Step 7 + Step 8 restart text) to `upgrade-larch.md` § Edit-in-sync and cross-link from `scripts/lib-sparse-dirs.md`; mirror in `skills/upgrade-larch/SKILL.md` if that file gains an edit-in-sync note

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-sync-surfaces
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:73,117
- **Concern**: Future `test-upgrade-larch-retention.sh` literal regression guard has no dual-update contract; self-comparing lib output would be tautological. Scenario: Adding a top-level dir updates only `scripts/lib-sparse-dirs.sh` and the test fails until someone discovers the duplicated expected literal, or the guard is dropped
- **Proposed resolution**: Document in `scripts/lib-sparse-dirs.md` and the test header that allowlist edits require updating the lib assignment and the harness expected literal together; prefer sourcing `SCRIPT_ROOT/scripts/lib-sparse-dirs.sh` and asserting `normalize_sparse_dirs` matches a hermetic git sparse-checkout fixture (as the other new cases do) rather than re-embedding the full dir string

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-sync-surfaces
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:17,54-55,121-123
- **Concern**: Finding 1: Drift probe can use PLUGIN_ROOT before it is bound under set -u. Scenario: The plan inserts the probe in the JQ/GIT block before the current PLUGIN_ROOT assignment; set +e does not disable set -u, so a literal $PLUGIN_ROOT lookup can abort SessionStart instead of staying warn-only
- **Proposed resolution**: Revise the plan to bind a local plugin_root from CLAUDE_PLUGIN_ROOT or SCRIPT_DIR before the probe, then source lib-sparse-dirs.sh from that value while keeping the probe fail-open

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-sync-surfaces
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.md:30-36, .claude/skills/release/SKILL.md:146-149, skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh:6-8
- **Concern**: Finding 2: Planned sync contract omits the new test literal and release Step 7 coupling. Scenario: The plan creates an expected-literal sparse-dir assertion and changes release Step 7, but the documented edit-in-sync surface only names upgrade/docs/SECURITY/Makefile; future allowlist or SCRIPT_ROOT changes can miss those coupled files
- **Proposed resolution**: Add .claude/skills/release/SKILL.md Step 7 to upgrade-larch.md Edit-in-sync, and mark the test expected literal as an intentional dual-update guard; do not replace it with a lib-vs-itself comparison unless the duplicate guard is deliberately removed
