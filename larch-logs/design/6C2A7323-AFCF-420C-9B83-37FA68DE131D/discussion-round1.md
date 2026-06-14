## Decision 1: Lint vehicle
- **Question**: Which vehicle — `scripts/test-design-structure.sh` or agent-lint — should host the new structural lint?
- **Resolution**: `scripts/test-design-structure.sh`. It already has a Makefile target (`test-design-structure`) and existing assertions for SKILL.md wrapper-only fences. Agent-lint covers only SKILL.md-level rules and has no custom-rule support for this check.
- **Source**: codebase

## Decision 2: Lint scope — which files to check
- **Question**: Does "every `bash` fence under `skills/design/`" include `scripts/*.md` sibling docs or only orchestrator-facing references?
- **Resolution**: Orchestrator-facing surfaces only — `skills/design/SKILL.md` (already covered) + `skills/design/references/*.md`. Mirrors `lint-bare-grep-probe.sh` which explicitly excludes non-orchestrator-facing documentation. The `scripts/*.md` sibling docs contain harness invocations and documentation examples that are not executed as Bash tool blocks by the orchestrator.
- **Source**: codebase (lint-bare-grep-probe.sh precedent, brainstorm.md/decompose-panel.md survey)

## Decision 3: What counts as a valid first command
- **Question**: Does `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py"` pass the lint?
- **Resolution**: Yes. The lint allows `python3 "${CLAUDE_PLUGIN_ROOT}/..."` because the first argument to python3 is a `${CLAUDE_PLUGIN_ROOT}`-rooted path. This already works for all `decompose-panel.md` fences. Only fences with a first command that has no `${CLAUDE_PLUGIN_ROOT}` reference AND no launcher prefix are flagged (e.g., `[ -f ... ] && source ...`, `_launch_id=...`).
- **Source**: codebase (decompose-panel.md fences all pass)

## Decision 4: Failing fences — exact count
- **Question**: What raw fences need fixing?
- **Resolution**: Exactly 4 raw fences in `references/*.md`:
  - `brainstorm.md` line 88: one-external collection fence (`[ -f ... ] && source ...` prelude)
  - `brainstorm.md` line 96: two-external collection fence (same pattern)
  - `plan-review.md` line 121: collector fence (`[ -f ... ] && source ...` prelude) → demote to text
  - `plan-review.md` line 149: voter-dispatch argv reference (`_launch_id=...`) → demote to text
- **Source**: codebase (python3 survey of references/*.md)

## Decision 5: brainstorm.md --mode collect structure
- **Question**: Should `--mode entry` absorb the skip+complete path, removing `--mode complete` from SKILL.md?
- **Resolution**: Yes. "Brainstorm-off path: one Bash call" (acceptance criterion) requires that when `brainstorm_requested=false`, only ONE launcher call runs. `--mode entry` handles skip+sentinel-write internally. `--mode complete` moves to brainstorm.md body (called after externals + collect when brainstorm IS active). SKILL.md removes its unconditional `--mode complete` fence.
- **Source**: issue acceptance criterion

## Decision 6: Suppression comment format
- **Question**: What suppression comment syntax should the new lint use?
- **Resolution**: `# lint-script-only-fences: ok <reason>` (same-line suppression, mirrors `lint-bare-grep-probe.sh`'s `# lint-bare-grep-probe: ok <reason>` pattern).
- **Source**: codebase (lint-bare-grep-probe.sh, scripts/lint-bare-grep-probe.md)
