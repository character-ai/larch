### FINDING_1: SessionStart drift probe can read PLUGIN_ROOT before initialization
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-Edge, Cursor-Innovation, Cursor-dyn-hook-isolation, Codex-dyn-hook-isolation, Codex-dyn-sync-surfaces
- **Severity**: important
- **Concern**: The planned SessionStart drift probe is inserted before `PLUGIN_ROOT` is bound, but it sources `lib-sparse-dirs.sh` through `PLUGIN_ROOT`. Depending on shell state, this either silently skips drift warning or aborts SessionStart under `set -u`, so sparse-cone drift may not be reported and the hook may violate its fail-open contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements: Resolve and source lib-sparse-dirs.sh in the probe via SCRIPT_DIR or CLAUDE_PLUGIN_ROOT with a SCRIPT_DIR/.. fallback; do not reference PLUGIN_ROOT from the HOOK_CWD-only block
  - From Cursor-Edge: In the drift block set plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" and source "$SCRIPT_DIR/lib-sparse-dirs.sh" (or "$plugin_root/scripts/lib-sparse-dirs.sh"); document that binding in sessionstart-health.md
  - From Cursor-Innovation: Resolve the lib at $SCRIPT_DIR/lib-sparse-dirs.sh (same pattern as lib-quiet.sh on line 21), or set plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" immediately before the probe; do not depend on HOOK_CWD
  - From Cursor-dyn-hook-isolation: At probe entry bind plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" (or source "$SCRIPT_DIR/lib-sparse-dirs.sh" directly) before any PLUGIN_ROOT expansion; keep the probe cwd-independent of HOOK_CWD
  - From Codex-dyn-hook-isolation: Use the already-initialized SCRIPT_DIR path, e.g. "$SCRIPT_DIR/lib-sparse-dirs.sh", or initialize a local plugin_root before the probe; do not rely on the later HOOK_CWD-only PLUGIN_ROOT assignment
  - From Codex-dyn-sync-surfaces: Revise the plan to bind a local plugin_root from CLAUDE_PLUGIN_ROOT or SCRIPT_DIR before the probe, then source lib-sparse-dirs.sh from that value while keeping the probe fail-open

### FINDING_2: Release Step 7 fallback can run stale installed upgrade logic
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-dyn-release-coupling
- **Severity**: important
- **Concern**: Release Step 7 treats a missing `CURRENT_VERSION` marketplace cache directory as equivalent to no install, but maintainers may have an older installed marketplace version or a pruned current cache. The fallback can then invoke the stale installed `/upgrade-larch` path instead of the working-tree script, so the just-released sparse allowlist may not be applied during the release cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Distinguish no install from a different installed version; when an installed cache root is resolvable, run the working-tree upgrade-larch.sh with CLAUDE_PLUGIN_ROOT set to that root, otherwise warn and skip/fallback only for true dev-clone/no-install cases
  - From Codex-Edge: Before using the Skill-tool fallback, locate an existing larch-local cache root for the actual installed version or another valid numeric cache dir and run the working-tree upgrade-larch.sh with CLAUDE_PLUGIN_ROOT set to that root; reserve the Skill fallback for no cache or marketplace install
  - From Codex-dyn-release-coupling: Before falling back to the Skill tool, derive a real installed cache root: prefer CLAUDE_PLUGIN_ROOT when it is an existing larch-local cache version dir, otherwise parse the installed larch version and use $HOME/.claude/plugins/cache/larch-local/larch/$installed_version. Run the working-tree script with that root; reserve Skill fallback for true dev-clone/no marketplace install.

### FINDING_3: SessionStart drift probe may add unnecessary hook surface
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: Adding the drift probe and shared sparse-dir library expands the SessionStart hook with extra sourcing and git sparse-checkout comparison logic for a condition already repaired by `/upgrade-larch`, increasing runtime hook risk and test/docs churn beyond the release/upgrade fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Limit this PR to RC1 and RC2: keep the allowlist in upgrade-larch.sh unless another required runtime consumer remains, drop the SessionStart drift probe and its related docs/tests/agent-lint plumbing, and rely on /upgrade-larch reconcile-on-drift for repair

### FINDING_4: Missing normalize_sparse_dirs guard can leak failures despite best-effort sourcing
- **Reviewer(s)**: Cursor-dyn-hook-isolation, Codex-dyn-hook-isolation
- **Severity**: important
- **Concern**: The plan swallows a missing `lib-sparse-dirs.sh` source but may still call an undefined `normalize_sparse_dirs`. Under `set -euo pipefail` or insufficient subshell guarding, this can emit errors or propagate nonzero status instead of silently skipping the warn-only probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-hook-isolation: Treat subshell as requiring inner set +e, or match existing line 127-129: source … || true then declare -F normalize_sparse_dirs before expected=$(normalize_sparse_dirs …); alternatively expected=$(normalize_sparse_dirs 2>/dev/null || true) so missing lib skips without a set +e envelope
  - From Codex-dyn-hook-isolation: After sourcing, skip unless declare -F normalize_sparse_dirs succeeds, or compute expected with stderr suppressed and || true inside the best-effort block before comparing

### FINDING_5: Edit-in-sync docs omit release Step 7 coupling
- **Reviewer(s)**: Cursor-dyn-sync-surfaces, Codex-dyn-sync-surfaces
- **Severity**: important
- **Concern**: The upgrade-larch edit-in-sync documentation omits `.claude/skills/release/SKILL.md` even though release Step 7 is being coupled to the working-tree `upgrade-larch.sh` and sparse allowlist behavior. Future allowlist or reconcile changes could miss the release path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sync-surfaces: Add `.claude/skills/release/SKILL.md` (Step 7 + Step 8 restart text) to `upgrade-larch.md` § Edit-in-sync and cross-link from `scripts/lib-sparse-dirs.md`; mirror in `skills/upgrade-larch/SKILL.md` if that file gains an edit-in-sync note
  - From Codex-dyn-sync-surfaces: Add .claude/skills/release/SKILL.md Step 7 to upgrade-larch.md Edit-in-sync, and mark the test expected literal as an intentional dual-update guard; do not replace it with a lib-vs-itself comparison unless the duplicate guard is deliberately removed

### FINDING_6: Sparse allowlist regression test needs explicit dual-update contract
- **Reviewer(s)**: Cursor-dyn-sync-surfaces, Codex-dyn-sync-surfaces
- **Severity**: important
- **Concern**: The planned literal regression guard for sparse dirs has no documented dual-update contract. Future allowlist edits could either fail unexpectedly because the duplicated expected literal was not updated, or the test could be weakened into a tautological lib-vs-itself comparison.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sync-surfaces: Document in `scripts/lib-sparse-dirs.md` and the test header that allowlist edits require updating the lib assignment and the harness expected literal together; prefer sourcing `SCRIPT_ROOT/scripts/lib-sparse-dirs.sh` and asserting `normalize_sparse_dirs` matches a hermetic git sparse-checkout fixture (as the other new cases do) rather than re-embedding the full dir string
  - From Codex-dyn-sync-surfaces: Add .claude/skills/release/SKILL.md Step 7 to upgrade-larch.md Edit-in-sync, and mark the test expected literal as an intentional dual-update guard; do not replace it with a lib-vs-itself comparison unless the duplicate guard is deliberately removed
