## Architecture Diagram

Architecture diagram not available.

## Code Flow Diagram

```mermaid
flowchart TD
    A[run-analysis.sh start] --> B{parse flags}
    B -->|--no-issue / --no-plot / --plot-from| C[resolve REPO via gh]
    C --> D{PLOT_FROM set?}
    D -->|yes| E[gh issue view PLOT_FROM\nwrite body to tmpfile]
    D -->|no| F[scan GitHub: search issues\nfetch each issue JSON\njq -s to cache JSON]
    F --> G[write ANALYZER Python to tmpfile]
    E --> G
    G --> H{--plot-from mode?}
    H -->|yes| I[load_raw_records:\nfind ## Raw per-issue data\nextract JSON fence\nparse records]
    H -->|no| J[analyze cache JSON:\nparse token reports\ncompute costs per issue]
    I --> K[plot records:\nwrite plot.py + input.json\nsubprocess: python plot.py input plot_dir]
    J --> K
    K --> L{subprocess exit 0?}
    L -->|no| M[warn plot skipped\nreturn empty paths]
    L -->|yes| N[return PNG paths\nopen with open on macOS]
    M --> O{--plot-from mode?}
    N --> O
    O -->|yes| P[print plot paths and exit]
    O -->|no| Q[redirect_stdout to StringIO\nprint_analysis\nwrite to stdout]
    Q --> R{NO_ISSUE set?}
    R -->|yes| S[exit 0]
    R -->|no| T[create_report_issue via gh issue create]
    T --> S
```
