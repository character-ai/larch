## Decision 1: Filing paths in scope
- **Question**: Which OOS filing paths should attach the priority label?
- **Resolution**: Both paths — /implement Step 9a.1 (`oos_filer.py`) and /design Step 5b (`design_oos.py` + `/larch:issue`).
- **Source**: user

## Decision 2: High-risk signal definition
- **Question**: What focus-area value qualifies as high-risk?
- **Resolution**: `focus-area: correctness` only. Security is already separately routed; risk-integration is too broad.
- **Source**: user

## Decision 3: Design path label precision
- **Question**: Should the design path label the whole batch (if any correctness block exists) or per-item only?
- **Resolution**: Per-item precision required. Extend `file_oos_annotate_main()` to apply labels to only the correctness-tagged items after `/larch:issue` files them, via `gh issue edit --add-label`.
- **Source**: user

## Decision 4: Label provisioning
- **Question**: What happens if the `oos-correctness` label doesn't exist when filing runs?
- **Resolution**: Auto-create via `gh label create --force` before filing (implement path) and before label application (design path annotate step). No pre-creation required.
- **Source**: user

## Decision 5: analyze-issues reporting scope
- **Question**: What is the MVP scope for backlog reporting?
- **Resolution**: Label-based GitHub query. Filter open `[OOS]` issues with `oos-correctness` label, report sorted by age. Added as a new section in `analyze_issues.py`.
- **Source**: user

## Decision 6: Non-goals
- **Resolution**: No change to inline review acceptance or OOS-vs-accept routing. SLA breach reporting and `/deps`/`combine-issues` priority wiring are OOS for MVP.
- **Source**: codebase + user
