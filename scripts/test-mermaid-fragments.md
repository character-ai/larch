# test-mermaid-fragments.sh contract

Regression harness for `scripts/sanitize-mermaid-fragment.sh`. Mermaid fence extraction coverage lives in `python/test_lint_mermaid_fences.py`.

The harness covers:

- rejection of literal `|` inside flowchart square, round, curly, and double-round node text;
- rejection of `<br/>`, `<br />`, `<br>`, and `$` inside `sequenceDiagram` participant / actor aliases;
- acceptance of edge-label pipes, flowchart `<br/>`, body `$` references, quoted node text pipes, escaped quotes, and nested bracket text without a pipe;
- Markdown `--from-md` mode with one accepted fence and one rejected fence plus heading-key output;
- public-safe `REASON_TOKEN=` output and categorized `### Warnings` append behavior;
Mermaid fence extraction and missing-toolchain behavior are covered by `python/test_lint_mermaid_fences.py`.

Run with:

```
bash scripts/test-mermaid-fragments.sh
```
