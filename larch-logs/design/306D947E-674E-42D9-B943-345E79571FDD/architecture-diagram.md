## Architecture Diagram

```mermaid
flowchart LR
    A[pre-commit / Makefile] --> B[lint-readability-preamble.sh]
    B --> C{manifest_rows}
    C -->|orchestrator-inline:N| D[grep -Ec / compare to expected count]
    C -->|external-prompt:N:kind| E[grep -F[xc] / compare existing]
    D -->|count == N| OK[pass]
    D -->|count != N AND file exists| F[expected N, found M]
    D -->|file missing| G[missing orchestrator-inline directive]
    E -->|count == N| OK
    E -->|count != N| H[missing external-prompt directive]
    F --> X[exit 1]
    G --> X
    H --> X
    OK --> Y[exit 0]
    HARNESS[test-lint-readability-preamble.sh] -.fixtures.-> B
```
