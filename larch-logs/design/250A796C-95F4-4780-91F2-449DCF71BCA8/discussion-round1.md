## Decision 1: Items D, E, F handling
- **Question**: Should Items D, E, F (README outline mention, /larch:pause table row, docs/issue-anchored-plan.md design-pause block) be re-verified or dropped on faith of the Step 0c grep?
- **Resolution**: Re-verified — README:61 and docs/skills.md:55 both say "before the Step 1d.7 outline-approval gate"; README:64 has the `/larch:pause` row; docs/issue-anchored-plan.md:73+ has the `## Design Pause Block Format` section with full marker schema. All three already addressed → drop from scope.
- **Source**: codebase

## Decision 2: Items H, I, J handling
- **Question**: Items H, I, J reference a "Step 3.6 plan-quality assessor" — keep, drop, or reserve?
- **Resolution**: Drop entirely. No `Step 3.6` in `skills/design/SKILL.md`, no `assessor` script under `skills/design/scripts/` or `scripts/`, no `assessor-verdict-*` / `plan-after-round-*` filenames produced by any helper. Documentation cannot describe a non-existent feature.
- **Source**: user + codebase

## Decision 3: Item C scope (46 awk rehydration blocks)
- **Question**: Is Item C in-scope as doc-only sweep, or split to a separate refactor issue?
- **Resolution**: In-scope as doc-only sweep. The 46 lines live inside `skills/implement/SKILL.md` Bash fences; 4 unique forms, the bulk byte-identical. Consolidation is a within-file dedup edit.
- **Source**: user

## Decision 4: Item A handling
- **Question**: Is Item A (AGENTS.md post-monitor wait contract) addressed?
- **Resolution**: Re-verified. `AGENTS.md:58` reads "Top-level Family B background+monitor pairs must capture the writer PID and `wait` after `breadcrumb-monitor.sh`; use the canonical two-branch pattern in `BASH_AUTHORING.md` §4." Already addressed → drop.
- **Source**: codebase

## Decision 5: Final scope
- **Question**: What is the actual implementation scope after re-verification?
- **Resolution**: 3 items — B (linting.md harness row), C (consolidate awk rehydration), G (SKILL.md:375 "item 9" → "item 10"). All doc-only.
- **Source**: user + codebase
