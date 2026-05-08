# test-mermaid-fragments.sh contract

Regression harness for `scripts/sanitize-mermaid-fragment.sh` and the nested-fence extraction behavior in `scripts/lint-mermaid-fences.sh`.

The harness covers:

- rejection of literal `|` inside flowchart square, round, curly, and double-round node text;
- rejection of `<br/>`, `<br />`, `<br>`, and `$` inside `sequenceDiagram` participant / actor aliases;
- acceptance of edge-label pipes, flowchart `<br/>`, body `$` references, quoted node text pipes, escaped quotes, and nested bracket text without a pipe;
- Markdown `--from-md` mode with one accepted fence and one rejected fence plus heading-key output;
- public-safe `REASON_TOKEN=` output and categorized `### Warnings` append behavior;
- a nested documentation-fence fixture that must not be extracted by `lint-mermaid-fences.sh`.

The lint fixture accepts exit 2 as a local missing-toolchain skip because `mmdc` is installed in CI and optional locally.

Run with:

```
bash scripts/test-mermaid-fragments.sh
```
