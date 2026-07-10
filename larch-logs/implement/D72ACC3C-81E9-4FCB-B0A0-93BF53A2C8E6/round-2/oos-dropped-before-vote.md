### FINDING_1: Direct `step2-dispatch` difficulty resolution
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `step2_dispatch_main` now resolves omitted `--difficulty` from persisted state before building `DispatchState`, so MODERATE Cursor launches receive `--difficulty MODERATE` and use `grok-4.5` instead of silently defaulting to Composer.

### FINDING_2: Bootstrap routing test coverage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `test_bootstrap.py` now covers MODERATE→Cursor, override-before-prior, the TRIVIAL/HARD/invalid/missing matrix, and MODERATE Cursor-unavailable→Codex fallback. Bootstrap, dispatch, and launch paths share `resolve_step2_effective_difficulty`; MODERATE implicit routing prefers Cursor, Cursor launch selects `grok-4.5` with override precedence, and final-report/token-cost paths split Grok tokens into dedicated flags priced at 2.00/0.50/6.00.
