## Proposed Design Outline

### Goals
- Scope the compact reviewer status table to Step 3 and its resume fence only.
- Replace the reviewer table with a plain progress breadcrumb for Step 5c and the Final summary block.
- Eliminate confusing "reviewer slot" output in non-review contexts.

### Non-goals
- No script changes; `skills/design/SKILL.md` only.
- Do not change the reviewer table format or behavior for Step 3.
- Do not add a general conditional clause — scope it at the source.

### Approach sketch
- In the **Compact reviewer status table** paragraph (Progress Reporting section), change "each immediate-background wait" to "Step 3 review fence and Step 3 resume fence."
- Update the **Verbosity Control** bullet that lists permitted output to match the narrowed scope.
- In the **Final summary block** Immediate-background wait rule, replace "print only the permitted breadcrumb/status table" with a plain progress breadcrumb instruction (e.g., `⏳ <outcome>: writing final summary…`).
- In the **Step 5c** Immediate-background wait rule, replace the same phrase with a plain progress breadcrumb instruction (e.g., `⏳ 5c: writing plan to GitHub…`).

### Surfaces in scope
- `skills/design/SKILL.md` — Progress Reporting section (compact table paragraph + Verbosity Control bullet), Final summary block section, Step 5c section.

### Open questions
- None.
