## Proposed Design Outline

### Goals
- Add 7 judgment-only guidelines to `ARCHITECTURAL_GUIDELINES.md`: G-Py-7, G-Py-8, G-Py-10, G-Cfg-1, G-IO-1, G-CLI-1, G-Sec-1.
- Match the existing entry format exactly: `### G-...:` heading, `- Why:`, `- Deviate when:`. No `- Evidence:` bullet.
- Keep `make lint` green.

### Non-goals
- No edits to the 9 existing entries, the preamble, or any code.
- No mechanically-validatable guidelines (subprocess-via-Runner, env-via-config-constant); those stay in the sibling lint issue, reserving IDs G-Py-9 and G-Cfg-2.
- No new tests; the parser is fixture-covered and no real-file conformance test exists.

### Approach sketch
- Single-file edit to `ARCHITECTURAL_GUIDELINES.md`.
- Append G-Py-7, G-Py-8, G-Py-10 to the existing "Python coding practices" section.
- Add four new `##` sections after "Python coding practices", before "Skill authoring and context economy": "Configuration and protocol literals" (G-Cfg-1), "Wire-file I/O" (G-IO-1), "CLI surface" (G-CLI-1), "Security" (G-Sec-1).
- Rewrite each draft as `### G-...:` + `- Why:` + `- Deviate when:`; drop the draft `####` depth and Evidence text.

### Surfaces in scope
- `ARCHITECTURAL_GUIDELINES.md` only.

### Open questions
- None.
