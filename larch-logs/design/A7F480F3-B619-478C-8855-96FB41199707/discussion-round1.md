## Decision 1: Evidence bullet handling
- **Question**: The issue drafts each carry a third `- Evidence:` bullet. Keep, drop, or fold it?
- **Resolution**: Drop the `- Evidence:` bullets. Each new entry has only `- Why:` and `- Deviate when:`, matching the existing 9 entries. The consumer parser (`python/architectural_guidelines.py` `parse_guideline_entries`) keeps only Why/Deviate bullets, so Evidence would be inert dead weight.
- **Source**: user

## Decision 2: Section layout for new prefix families
- **Question**: Where do G-Cfg-1, G-IO-1, G-CLI-1, G-Sec-1 (new prefix families) live?
- **Resolution**: One `##` section per family. Add G-Py-7/8/10 to the existing "Python coding practices" section; add new sections "Configuration and protocol literals" (G-Cfg-1), "Wire-file I/O" (G-IO-1), "CLI surface" (G-CLI-1), "Security" (G-Sec-1). Single-entry sections are already precedented ("Enforcement philosophy").
- **Source**: user

## Decision 3: Heading depth
- **Question**: The issue drafts use `####` headings. What heading level is correct?
- **Resolution**: `### ` (three hashes). The parser regex `^###\s+(G-[A-Za-z0-9-]+-\d+):` requires exactly `###`, and markdownlint MD001 (heading-increment, enabled) forbids an h2→h4 jump. `####` would neither parse nor lint.
- **Source**: codebase

## Decision 4: ID numbering
- **Question**: Keep the G-Py-9 gap (G-Py-7/8/10) or renumber contiguously?
- **Resolution**: Keep IDs exactly as drafted: G-Py-7, G-Py-8, G-Py-10, G-Cfg-1, G-IO-1, G-CLI-1, G-Sec-1. G-Py-9 and G-Cfg-2 stay reserved for the sibling lint issue, preserving cross-reference stability. The issue delegates this to implementer discretion.
- **Source**: codebase

## Decision 5: Edit scope (hard constraint)
- **Question**: What must not change?
- **Resolution**: Add 7 entries only. Do not modify, reorder, or restyle the 9 existing entries or the preamble. Do not add the two mechanically-validatable proposals (subprocess-via-Runner, env-via-config-constant); those belong to the sibling linter issue per the file's own G-Enf-1 philosophy.
- **Source**: issue

## Decision 6: No call-site verification needed
- **Question**: The G-Sec-1 draft says "Confirm the specific git.py call sites during implementation." Does the docs change depend on that?
- **Resolution**: No. With Evidence dropped, the guideline text (Why/Deviate) is general and does not name specific call sites. This is a docs-only change; no code inspection of git.py call sites is required for correctness.
- **Source**: codebase
