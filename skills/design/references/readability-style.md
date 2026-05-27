# Readability Style

**Consumer**: `/design` prompt surfaces that produce user-facing text, either through an external-agent prompt token or through inline orchestration prose.

**Contract**: this file is the only source of truth for the `/design` readability preamble. External prompt files embed the literal `<READABILITY_STYLE>` token, and assembly code or orchestration expands it to this full file. Inline composition sites read this file before writing user-facing text.

**When to load**: load only when a `/design` step is about to compose user-facing prose or render a prompt that asks another agent to compose such prose. Do not load during setup, pure validation, or byte-stable artifact handling.

---

## Style Axes

Write in three styles at once:

- **Strunk & White**: use active voice. Omit needless words. Prefer concrete nouns and verbs.
- **Dyslexia-friendly**: use short sentences. Prefer simple words. Break dense ideas into headings and bullets.
- **Brevity**: shorter is better. Minimize the total artifact length while preserving meaning.

## Precision Contract

Keep these byte-stable unless the task explicitly edits them:

- fenced code blocks
- backticked tokens
- file paths
- identifiers
- flag names
- `### NEW:` / `### UPDATED:` / `### REWRITTEN:` plan grammar
- the trailing `diff_lines: <N>` line

Do not rewrite those items for style. Explain around them instead.

## Precedence

When rules conflict, use this order:

`code references > meaning > brevity > dyslexia-friendly chunking > Strunk & White micro-rewrites`

Apply it directly:

- Preserve code references first.
- Preserve exact meaning next.
- Cut words before adding layout.
- Add headings or bullets only when they improve scanning.
- Polish grammar last.

## Substitution Token

External-agent prompt files MUST embed this literal token:

`<READABILITY_STYLE>`

Before launch, replace every literal `<READABILITY_STYLE>` token with the full contents of this file.

## Examples

Before: "It is recommended that the implementer should consider adding a validation step."

After: "Add a validation step."

Before: "The plan should make sure that users are not able to continue when the file cannot be read."

After: "Block the flow when the file cannot be read."

Before: "In order to avoid potential future confusion, documentation can be updated."

After: "Update the docs to avoid confusion."

Before: "The script performs an operation that checks if the path exists."

After: "The script checks that the path exists."

Before: "This could possibly be out of scope depending on how the team wants to proceed."

After: "This may be out of scope."
