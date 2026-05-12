## Architecture Diagram

Architecture diagram not available.

## Code Flow Diagram

```mermaid
flowchart TD
    A[run-analysis.sh invoked] --> B[RATES dict initialized\nCodex/Cursor updated, Gemini added]
    B --> C[ACTUAL_SPEND = env_rate LARCH_REPORT_TOKENS_ACTUAL_SPEND]
    C --> D[analyze cache JSON]
    D --> E[parse_report per issue\nclassifies section_name - gemini path added]
    E --> F[cost_vendor per vendor]
    F --> G{vendor in RATES?}
    G -->|claude| H[input + cache_read + cache_create + output]
    G -->|codex / cursor / gemini| I{known == 0?}
    I -->|yes| J[total x aggregate]
    I -->|no| K[input x rate.input + output x rate.output + hidden x rate.aggregate]
    H --> L[record.cost accumulated]
    J --> L
    K --> L
    L --> M[print_analysis]
    M --> N[Cost by workflow section\nper-vendor breakdown added]
    N --> O{ACTUAL_SPEND > 0?}
    O -->|yes| P[Print reconciliation line\ntracked vs actual delta]
    O -->|no| Q[end]
    P --> Q
```
