## Decision 1: Fix scope
- **Question**: Reactive (lint-fix-loop prompt) only, preventive (implementer-base agent) only, or both?
- **Resolution**: Both A and B. Add PLR0911 guidance to the lint-fix-loop prompt AND add a PLR0911 note to the implementer-base agent.
- **Source**: user

## Decision 2: Lint-fix-loop guidance content
- **Question**: Should the PLR0911 guidance include a `# noqa` fallback path?
- **Resolution**: Primary guidance is semantic consolidation (consolidate guards that return the same value into a compound condition). No `# noqa` fallback in the prompt — the coder should always prefer semantic refactoring over suppression comments. Keeping the guidance focused reduces ambiguity.
- **Source**: codebase (existing Pyright guidance section uses targeted advice, not "add suppression if hard")

## Decision 3: Where to add implementer-base note
- **Question**: Harness-awareness checklist or a new section?
- **Resolution**: Add as a bullet in the existing "Harness-awareness checklist" section — this is the canonical location for preventive checks that are not hard guards.
- **Source**: codebase (harness-awareness checklist already contains non-guard preventive checks)

## Decision 4: Generated file regeneration
- **Question**: Must codex-implementer.md and cursor-implementer.md be regenerated?
- **Resolution**: Yes. Both files have AUTO-GENERATED comments saying to regenerate via `python3 python/cli.py generate <name>`. Regenerating them is required to keep them in sync with _implementer-base.md.
- **Source**: codebase (agents/codex-implementer.md line 6, agents/cursor-implementer.md line 6)
