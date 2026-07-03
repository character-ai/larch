# test-brainstorm-prompts.sh

Offline regression harness ensuring `skills/design/references/brainstorm-prompts.md` retains the three `<BRAINSTORM_*_PROMPT>` token literals, each slot contains the exact `Style requirements: \`<READABILITY_STYLE>\`.` line, and `skills/design/references/brainstorm.md` still references the slot tokens plus the MANDATORY shared readability path and the path pin to `brainstorm-prompts.md`.

## Run

```bash
make test-brainstorm-prompts
```
