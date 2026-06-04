### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:44-47,skills/upgrade-larch/scripts/upgrade-larch.sh:5-7
- **Concern**: RC1 sets CLAUDE_PLUGIN_ROOT to the pre-release cache dir but the plan sources lib-sparse-dirs.sh from PLUGIN_ROOT, so the release Step 7 run loads allowlist metadata from the old install tree, not the working-tree script. Scenario: After merge, CUR_ROOT is the prior semver cache (e.g. 47.0.N) which does not yet contain scripts/lib-sparse-dirs.sh and still carries the old LARCH_SPARSE_DIRS without python; the proposed fail-loud source exits or applies the stale allowlist, so Step 7 warn-and-continue leaves RC1 unsatisfied and forces a second /upgrade-larch for RC2 self-heal
- **Proposed resolution**: Source lib-sparse-dirs.sh from the executing script package root (e.g. $(cd "$SCRIPT_DIR/../../.." && pwd -P)) and keep CLAUDE_PLUGIN_ROOT only for LARCH_CACHE_DIR, INSTALLED_VERSION, and prune protection; update the release Step 7 prose to match that split

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:4-7; .claude/skills/release/SKILL.md:146-149
- **Concern**: Planned RC1 override makes the working-tree upgrade script source the sparse allowlist lib from the old installed root. Scenario: Step 7 sets CLAUDE_PLUGIN_ROOT to CUR_ROOT, and the plan also changes upgrade-larch.sh to source "$PLUGIN_ROOT/scripts/lib-sparse-dirs.sh". That reads a missing or stale installed lib instead of the just-released working-tree lib, so the release either fails before applying the cone or re-adds the old sparse list.
- **Proposed resolution**: Separate script root from installed root: source lib-sparse-dirs.sh from the script tree, while using the explicit installed root only for LARCH_CACHE_DIR and INSTALLED_VERSION/prune protection.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-148 / skills/upgrade-larch/scripts/upgrade-larch.sh (proposed)
- **Concern**: RC1 sources allowlist from installed cache while executing working-tree script. Scenario: Step 7 runs `CLAUDE_PLUGIN_ROOT="$CUR_ROOT" bash "$PWD/skills/upgrade-larch/scripts/upgrade-larch.sh"` but the plan sources `lib-sparse-dirs.sh` from `$PLUGIN_ROOT` (= `CUR_ROOT`, the pre-release cache). The new allowlist (e.g. `python/`) is not in that tree on the transitional release, so RC1 can fail loudly (missing lib) or re-add the marketplace with the old `LARCH_SPARSE_DIRS`, leaving the same drift RC1 is meant to fix
- **Proposed resolution**: Source allowlist from the executing script tree (e.g. `LIB_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"` then `source "$LIB_ROOT/scripts/lib-sparse-dirs.sh"`, matching `step2-implement.sh` sourcing `external-tool-registry.sh` via `SCRIPT_DIR`); keep `PLUGIN_ROOT`/`CLAUDE_PLUGIN_ROOT` only for `LARCH_CACHE_DIR`, `INSTALLED_VERSION`, and `lib-quiet.sh`. Update Step 7 prose and `lib-sparse-dirs.md` to document the split

### FINDING_4:
- **Reviewer(s)**: Codex-Edge, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:4-7; .claude/skills/release/SKILL.md:146-148
- **Concern**: RC1 invokes the working-tree upgrade script with CLAUDE_PLUGIN_ROOT set to the old installed root, but the plan also sources the new sparse-dir lib from PLUGIN_ROOT. Scenario: The release-cycle path will try to source $CUR_ROOT/scripts/lib-sparse-dirs.sh from the pre-release install, where that new file does not exist, so the just-released allowlist is not applied and Step 7 falls back/fails instead of fixing RC1
- **Proposed resolution**: Keep CLAUDE_PLUGIN_ROOT for cache/running-version derivation, but source lib-sparse-dirs.sh from the script checkout/root used to run upgrade-larch.sh, or pass an explicit source-root/lib path for the release Step 7 invocation

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-148
- **Concern**: RC1 sets CLAUDE_PLUGIN_ROOT to the installed cache but the plan sources lib-sparse-dirs from PLUGIN_ROOT. Scenario: Release Step 7 runs the working-tree upgrade-larch.sh with CLAUDE_PLUGIN_ROOT=$CUR_ROOT; after extraction, source "$PLUGIN_ROOT/scripts/lib-sparse-dirs.sh" reads the prior install (missing lib on first ship, or stale LARCH_SPARSE_DIRS without the new dir). RC1 does not apply the just-released allowlist in-cycle.
- **Proposed resolution**: Source lib-sparse-dirs from the script tree (e.g. "$(cd "$SCRIPT_DIR/../../.." && pwd -P)/scripts/lib-sparse-dirs.sh") and keep CLAUDE_PLUGIN_ROOT only for LARCH_CACHE_DIR / INSTALLED_VERSION / lib-quiet. Document that invariant in the Step 7 RC1 bullet and upgrade-larch.md.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-148; skills/upgrade-larch/scripts/upgrade-larch.sh:4-8
- **Concern**: Planned Step 7 sets CLAUDE_PLUGIN_ROOT to the old installed root, but the planned lib source also reads lib-sparse-dirs.sh from PLUGIN_ROOT. Scenario: A release that introduces a new allowlist dir runs the working-tree script, yet it sources the old install's lib; that old root may lack lib-sparse-dirs.sh entirely or contain the stale allowlist, so RC1 either warns and skips or re-adds the stale cone
- **Proposed resolution**: Split script source root from installed/cache root: source lib-sparse-dirs.sh from the working tree script root, while using a separate explicit installed root only to derive LARCH_CACHE_DIR and INSTALLED_VERSION

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:5-7,.claude/skills/release/SKILL.md:46
- **Concern**: RC1 assumes working-tree allowlist but plan sources lib from PLUGIN_ROOT. Scenario: Step 7 sets CLAUDE_PLUGIN_ROOT to CUR_ROOT (pre-release cache). The plan sources lib-sparse-dirs from PLUGIN_ROOT like lib-quiet. CUR_ROOT still has the old LARCH_SPARSE_DIRS until this release lands; on the shipping release it may lack lib-sparse-dirs.sh entirely (fail-loud abort). RC1 then does not apply the new dir in-cycle; #3461 regresses to manual /upgrade-larch.
- **Proposed resolution**: Source lib-sparse-dirs from the executed script tree (e.g. SCRIPT_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"; prefer "$SCRIPT_PLUGIN_ROOT/scripts/lib-sparse-dirs.sh" when present, else PLUGIN_ROOT). Keep PLUGIN_ROOT only for LARCH_CACHE_DIR, INSTALLED_VERSION, and lib-quiet. Update Step 7 prose to match.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:4-7; .claude/skills/release/SKILL.md:146-148
- **Concern**: RC1 path points CLAUDE_PLUGIN_ROOT at the old installed cache root while the proposed upgrade script sources the new sparse-dir library through PLUGIN_ROOT. Scenario: On the first release that adds scripts/lib-sparse-dirs.sh, Step 7 runs the working-tree upgrade script with CLAUDE_PLUGIN_ROOT=$CUR_ROOT, so source "$PLUGIN_ROOT/scripts/lib-sparse-dirs.sh" resolves into the pre-release install where the new lib is absent; the script fails before applying the just-released allowlist, leaving RC1 unfixed
- **Proposed resolution**: Split execution root from installed/cache root: source lib-quiet.sh and lib-sparse-dirs.sh from a SCRIPT_DIR-derived repo root for the script being executed, and use the explicit installed root only to derive LARCH_CACHE_DIR/INSTALLED_VERSION and prune protection.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:4-7;.claude/skills/release/SKILL.md:43-48
- **Concern**: RC1 runs the working-tree upgrade script with CLAUDE_PLUGIN_ROOT set to the pre-release cache, but the plan sources the new lib-sparse-dirs.sh from PLUGIN_ROOT (same as CLAUDE_PLUGIN_ROOT). Scenario: The CURRENT_VERSION cache will not ship scripts/lib-sparse-dirs.sh on the release that introduces it; Step 7 fails loud or warn-and-continues before applying the just-released allowlist, so RC1 does not run in-cycle
- **Proposed resolution**: Keep CLAUDE_PLUGIN_ROOT for LARCH_CACHE_DIR / INSTALLED_VERSION / lib-quiet only; source lib-sparse-dirs.sh from the script tree (e.g. _ALLOWLIST_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)") and document that split in upgrade-larch.md and release Step 7

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-bootstrap-release
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:5-7,.claude/skills/release/SKILL.md:43-48
- **Concern**: RC1 sources lib-sparse-dirs from PLUGIN_ROOT=CUR_ROOT but CUR_ROOT is the pre-release cache tree without the new lib. Scenario: /release Step 7 runs CLAUDE_PLUGIN_ROOT=$HOME/.claude/plugins/cache/larch-local/larch/${CURRENT_VERSION} bash $PWD/skills/upgrade-larch/scripts/upgrade-larch.sh. After extracting LARCH_SPARSE_DIRS to scripts/lib-sparse-dirs.sh, the script sources $PLUGIN_ROOT/scripts/lib-sparse-dirs.sh (plan line 25). That file is absent on the old cache dir, so the run fails (plan: fail loudly) or, if sourcing is softened, LARCH_SPARSE_DIRS stays the old list. With the old list, marketplace_sparse_cone_matches (upgrade-larch.sh:52-61,93-99) can still match the existing cone and take marketplace update only, never re-adding --sparse with python — RC1 silent miss on the release that introduces the dir.
- **Proposed resolution**: Source lib-sparse-dirs from the executing script tree: $(cd "$SCRIPT_DIR/../../.." && pwd -P)/scripts/lib-sparse-dirs.sh (working tree on /release Step 7; installed plugin root on normal /upgrade-larch). Keep sourcing lib-quiet.sh from PLUGIN_ROOT for cache/prune. Document the split in release Step 7 and upgrade-larch.md.

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-bootstrap-release
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/release/SKILL.md:146-149; skills/upgrade-larch/scripts/upgrade-larch.sh:4-7
- **Concern**: Plan makes CLAUDE_PLUGIN_ROOT serve two roles: installed-cache root and script dependency root. The proposed Step 7 runs the working-tree upgrade script with CLAUDE_PLUGIN_ROOT set to the old cached CURRENT_VERSION root, while the proposed upgrade-larch change sources scripts/lib-sparse-dirs.sh from PLUGIN_ROOT.. Scenario: In the first release that adds scripts/lib-sparse-dirs.sh, CUR_ROOT is the prior installed version and lacks that new file. The direct Step 7 invocation fails before it can apply the just-released sparse allowlist, or it would read a stale allowlist from the old install on later allowlist changes.
- **Proposed resolution**: Keep the cache/root override separate from the script-source root. For example compute SCRIPT_ROOT from BASH_SOURCE and source lib-sparse-dirs.sh from SCRIPT_ROOT, while using CLAUDE_PLUGIN_ROOT only to derive LARCH_CACHE_DIR and INSTALLED_VERSION. Add a harness case for direct-running the working-tree script with CLAUDE_PLUGIN_ROOT pointing at an older fake cache root that lacks the new lib.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-sparse-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:5-7
- **Concern**: RC1 + lib extract sources allowlist from PLUGIN_ROOT while release runs the working-tree script with CLAUDE_PLUGIN_ROOT set to the pre-release cache dir. Scenario: After moving LARCH_SPARSE_DIRS into scripts/lib-sparse-dirs.sh, source "$PLUGIN_ROOT/scripts/lib-sparse-dirs.sh" resolves under ~/.claude/plugins/cache/.../CURRENT_VERSION, which will not contain the new lib on the release that introduces it; fail-loud or silent skip blocks RC1 from applying the just-released allowlist in-cycle
- **Proposed resolution**: Keep cache/prune semantics on CLAUDE_PLUGIN_ROOT but source lib-sparse-dirs.sh from the script tree, e.g. _ALLOWLIST_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"; source "$_ALLOWLIST_ROOT/scripts/lib-sparse-dirs.sh"; document the split in upgrade-larch.md and .claude/skills/release/SKILL.md Step 7

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-sparse-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:4-7; .claude/skills/release/SKILL.md:146-148
- **Concern**: Planned lib source path conflicts with the RC1 working-tree invocation. Scenario: Step 7 sets CLAUDE_PLUGIN_ROOT to the old cached CUR_ROOT, so source "$PLUGIN_ROOT/scripts/lib-sparse-dirs.sh" looks in the old install where this new lib does not exist; the just-released allowlist cannot run this cycle
- **Proposed resolution**: Keep CLAUDE_PLUGIN_ROOT for cache math, but derive SCRIPT_ROOT from SCRIPT_DIR and source scripts/lib-sparse-dirs.sh from SCRIPT_ROOT; add a small check covering the release-style invocation

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-sparse-contract
- **Severity**: important
- **Focus area**: code-quality
- **Location**: agent-lint.toml:78-82,293-295,588-592
- **Concern**: New sourced-only root library is missing from dead-script exclusions. Scenario: agent-lint documents that G004 does not follow source directives, and existing sourced-only libs are excluded; scripts/lib-sparse-dirs.sh can fail make lint despite being used only via source
- **Proposed resolution**: Add scripts/lib-sparse-dirs.sh to the existing sourced-library exclusions with a short comment
