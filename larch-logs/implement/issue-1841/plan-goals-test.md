## Goal

Skip unnecessary diagram generation: (A) Step 7a Code Flow Diagram in `/implement` when ≤2 files changed and all are non-runtime docs/config, and (B) Step 3b Architecture Diagram in `/design` when the plan is docs-only / scripts-only / config-only.

## Implementation Plan

### Files to modify

1. `skills/implement/SKILL.md` — Step 7a: add small/non-runtime skip condition before normal-mode generation
2. `skills/design/SKILL.md` — Step 3b: add conservative non-architectural classifier that emits a placeholder and skips generation

### Approach

**Part A — implement/SKILL.md Step 7a**

After the existing `quick_mode=true` skip block, add: compute `CHANGED_COUNT` via `git diff --name-only "$(git merge-base HEAD origin/main)" | wc -l`. Check whether every changed path is non-runtime (`.md`, `.txt`, `.tsv`, `CHANGELOG`, `docs/**`). If count ≤ 2 AND all non-runtime: print `⏩ 7a: code flow status=skip reason=small-non-runtime-change`, write diagrams fragment with placeholder `"(Code Flow Diagram skipped — small/non-runtime change)"`, proceed to Step 8. On any git failure, fall through to normal generation.

Update the `diagrams` anchor-fragment sub-section Code Flow placeholder list to include the new `small/non-runtime-change` entry.

**Part B — design/SKILL.md Step 3b**

Before the diagram generation instruction, add: classify plan type from `$DESIGN_TMPDIR/plan.txt`. If ALL modified files are exclusively docs (`.md`, `CHANGELOG`, `docs/**`), config (`.json`, `.yaml`, `.yml`, `.tsv`), or plain text (`.txt`) with no new behavioral contracts — write `N/A — no architectural change` directly to `$DESIGN_TMPDIR/architecture-diagram.md`, print `⏩ 3b: arch diagram status=skip reason=no-architectural-change`, proceed to Step 4. Apply conservative classifier: SKILL.md, `.sh`, `.py` count as potentially architectural — when uncertain, generate rather than skip.

## Test plan

- Run `/relevant-checks` (pre-commit + agent-lint) after changes
- Visually verify Step 7a new skip block is syntactically consistent with surrounding text
- Verify `diagrams` anchor-fragment sub-section lists all three Code Flow placeholder strings
- Verify Step 3b classifier gate is positioned before the diagram generation block with correct skip breadcrumb format
