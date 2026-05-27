## Decision 1: Audit scope across render-* scripts
- **Question**: Which files should the safe-empty array audit cover, and which actually have the hazard?
- **Resolution**: Audit walks `skills/design/scripts/render-final-summary.sh`, `scripts/render-run-summary.sh`, `scripts/render-cost-line.sh`. Only `render-final-summary.sh` has the hazard (5 empty-array declarations at lines 119/298/300/311/313; failing expansion at line 338). `render-run-summary.sh` and `render-cost-line.sh` populate their `*_args` arrays inline on declaration, so they have no empty-expansion risk under `set -u`.
- **Source**: user (Step 1c Audit scope answer) + codebase (Read of all three files; grep for `=()` and `${arr[@]}`)

## Decision 2: Sites to fix in render-final-summary.sh
- **Question**: Which lines actually need the `${arr[@]+"${arr[@]}"}` guard?
- **Resolution**: Line 338 expansion site — guard `render_cost_args` and `note_args`. Line 304 — guard `COST_ARGS` even though control flow currently guarantees it is populated (defense-in-depth + uniform static-grep rule). No edit needed at lines 119, 298, 300, 311, 313 (those are array declarations, not expansions).
- **Source**: codebase (read of `invoke_render` body and COST_ARGS lifecycle)

## Decision 3: Test coverage
- **Question**: What test coverage lands in this PR?
- **Resolution**: Both (a) a static-grep regression pin enforcing the safe-empty idiom at the `invoke_render` call site, AND (b) a dynamic test that runs `render-final-summary.sh --post-publish-only` under `/bin/bash` 3.2 with a minimal approved-outcome fixture and asserts rc=0 + `final-summary.md` non-empty.
- **Source**: user (Step 1c Test coverage answer)

## Decision 4: Edit discipline
- **Question**: Surgical or light cleanup?
- **Resolution**: Surgical — touch only the failing expansion sites. Add one comment line near the guarded expansion at line 338 pointing at `BASH_AUTHORING.md §3` so future editors understand the safe-empty idiom intent.
- **Source**: user (Step 1c Edit discipline answer)

## Decision 5: Hard constraints to preserve
- **Question**: What downstream contracts must the fix preserve?
- **Resolution**: `$DESIGN_TMPDIR/final-summary.md` body and the `larch:final-summary` GitHub upsert must remain byte-identical on Bash 4+ happy paths (the safe-empty idiom is a no-op when arrays are non-empty). Existing `skills/design/scripts/test-render-final-summary.sh` must keep passing without modification.
- **Source**: codebase (read of `invoke_render` and `compose_self_fallback`)

## Decision 6: Non-goals
- **Question**: What is explicitly out of scope?
- **Resolution**: No refactoring of `render-final-summary.sh` or sibling render scripts beyond the three guarded expansions and one comment line. No editing of `render-run-summary.sh` or `render-cost-line.sh`. No broader audit of other `skills/design/scripts/*.sh` files (separate PR if needed).
- **Source**: user (Step 1c Edit discipline answer) + codebase (no hazards in adjacent files)

Recorded: 6 decisions resolved (4 from Step 1c user answers, 2 from codebase inspection).
