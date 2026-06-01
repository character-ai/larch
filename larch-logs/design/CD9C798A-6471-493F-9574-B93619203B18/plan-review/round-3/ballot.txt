### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: skills/review-and-fix/scripts/review-and-fix.md:56 / SECURITY.md:64
- **Concern**: Acceptance criterion 4 (FINDING_9 sandbox-confinement trust boundary) has no planned doc bullet. Scenario: Planned `review-and-fix.md` / `SECURITY.md` updates cover relocation lifecycle, `chmod 0444`, and Step 2 grant width only; checkbox 4 ("sandbox-confinement trust boundary is documented") can ship unchecked and readers may treat relocation as sufficient without the stated assumption that `codex exec --full-auto` confines writes to declared grants
- **Proposed resolution**: Add one short sentence in the planned pre-coder / SECURITY updates: integrity assumes Codex `--full-auto` confines writes to declared `--add-dir`/workspace roots; `chmod 0444` is defense-in-depth if not — explicitly no CI sandbox probe (per session decision 4)

