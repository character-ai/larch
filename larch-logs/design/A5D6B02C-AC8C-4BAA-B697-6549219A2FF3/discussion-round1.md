## Decision 1: Scope of pre-fix rebase
- **Question**: Should the pre-fix rebase apply to `operator-bail` handoffs, or only to autonomous fix paths (`ci-fix` and `reship`)?
- **Resolution**: Autonomous paths only — `ci-fix` and `reship`. `operator-bail` stops for human intervention; the operator decides whether to rebase.
- **Source**: user
