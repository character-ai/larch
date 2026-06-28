### OOS_1: [OUT_OF_SCOPE] nit: agent-lint.toml OOS/disposition excludes overlap with SKILL.md anchors
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: OOS/disposition script excludes in `agent-lint.toml:325-327` overlap with paths still anchored in `SKILL.md` line 696. Future removal of line 696 without exclude cleanup may silently drop reachability coverage; redundant excludes mask drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] architecture: extracted-script-registry contract misstates agent-lint reachability
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-reachability
- **Severity**: nit
- **Concern**: `skills/implement/references/extracted-script-registry.md:5` claims the file is “not an agent-lint reachability anchor,” but qualified paths under `skills/implement/references/*.md` are scanned by agent-lint S030/G004. The lazy catalog still mechanically anchors listed script-path literals. A contributor could add a Makefile-only harness only to this catalog and drop its `agent-lint.toml` exclude believing the disclaimer, causing `make lint` failure on merge or leaving paths without excludes. The contract misstates how much dead-script detection remains for catalog-listed wrappers versus exclude-only machine-reachability paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases, dyn-dyn-reachability: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] risk-integration: broad agent-lint exclude stopgaps reduce dead-path detection
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-reachability
- **Severity**: nit
- **Concern**: New exclude blocks in `agent-lint.toml` (including `agent-lint.toml:25-133` disabling G004/S030 stale-script detection for ~100 paths until agent-lint#106, and the broader stopgap at `agent-lint.toml:260-367` covering registry `.md` contracts surfaced by post-deletion orphan diffs) are accepted tradeoffs but increase the agent-lint#106 cleanup surface. Paths in these sets can go dead without `make lint` flagging them; only `make lint-retired-scripts` partially backstops formally retired paths. Removing the blocks later will require re-anchoring or smarter walks, not just deleting SKILL inventories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing, dyn-dyn-reachability: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] architecture: design SKILL.md Plan helper contracts remain always-loaded
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md:779-799` — `### Wrapper contract inventory` was removed (~62 lines), but **Plan helper contracts** remains always-loaded (~20 lines of path literals). That limits context savings on `/design`; it was out of this issue’s scope but is the next obvious slimming target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] risk-integration: relocated fences reduce CI enforcement coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Fence relocations out of always-loaded `skills/implement/SKILL.md` reduce structural CI coverage. `scripts/test-implement-fence-shape.md:26` previously documented 26 new-shape fences while the script expected 22 on main (this branch fixes the doc). The `pr closes-issue` old-shape Bash fence moved to `skills/implement/references/extracted-script-registry.md:36-42`, so `scripts/test-implement-fence-shape.sh` no longer enforces its guard shape; drift in the lazy reference would not fail CI until something exercises that pin at runtime. Completing the timing-rehydration harness update addresses the blocking half of this gap but not lazy-reference guard-shape enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness, cursor-specialist-testing: Address the concern above.

