### [Plan Review] FINDING_3

### FINDING_3: Sanitizer `--warnings-step` still hardcoded to 3b after diagram move to 5b.5
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan retargets sanitizer breadcrumbs and `append-failure --site` to Step 5b.5 but does not list updating the `mermaid sanitize --warnings-step` argument still hardcoded to `"3b"` in `skills/design/scripts/design-step3b-sanitize.sh:136`. Warnings, diagnostics, and any consumer keyed on `warnings-step` stay tied to the pre-move Step 3b label after diagram work moves to Step 5b.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add --warnings-step 5b.5 (or equivalent) to the design-step3b-sanitize.sh update list and pin it in scripts/test-design-structure.sh if needed

