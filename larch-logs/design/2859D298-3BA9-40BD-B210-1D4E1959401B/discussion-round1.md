## Decision 1: Scope breadth — all 14 items
- **Question**: Should the plan cover all 14 bundled items, or a narrower set?
- **Resolution**: Plan all 14 items. They are independent and may be implemented piecemeal. This matches the `/combine-issues --oos` intent that merged 7 issues into #4833 to reduce issue count.
- **Source**: user

## Decision 2: No-defect items — document, no code change
- **Question**: For the ~7 "investigate, then pin a defect or close as no-defect" items, what happens when Step 2b investigation finds no real defect?
- **Resolution**: Document the no-defect rationale in the plan and make no code change for that item. Do not force speculative edits to working code, and do not add pinning tests for items that close as no-defect.
- **Source**: user

## Decision 3: Item 14 direction — wire the real secret-scrub counter
- **Question**: `_commit_run` always emits `SECRET_SCRUB_VIOLATIONS=0` (the variable is set to 0 and never reassigned), so the secret-rotation warning is inert. Wire the real counter, or remove the inert warnings?
- **Resolution**: Wire the real scrub-violation count into `_commit_run` so the warning fires when a secret is scrubbed. This combined issue lifts the #4782 scope ban on touching `run_logs.py` and the implement path.
- **Source**: user

## Decision 4: Hard constraints — preserve contracts and harnesses (codebase)
- **Question**: What must not break?
- **Resolution**: Preserve all `KEY=value` stdout grammars (including the `SECRET_SCRUB_VIOLATIONS=` line shape that downstream parsers read), existing pytest harnesses, and run-log/contract tokens. Every item is additive or a minimal targeted fix; no refactors beyond what the item requires.
- **Source**: codebase
