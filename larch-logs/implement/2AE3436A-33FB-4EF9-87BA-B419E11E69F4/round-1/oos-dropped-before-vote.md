### OOS_1: [OUT_OF_SCOPE] Automated lint/acceptance for post-deletion import grep not implemented
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The plan’s optional automated lint/acceptance criterion (#5698 fix #2) is not implemented; only manual grep is documented. Future migrations may skip manual grep; `make lint-retired-scripts` does not catch flat-name Python imports under `skills/`, so the same class of miss as #5655 can recur without mechanical enforcement. Regression prevention still depends on manual grep at migration time and existing skill harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Importer scan limited to `*.py` misses shell/harness consumers
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: The importer-scan recipe only searches `*.py` files, so it misses shell wrappers with embedded Python that import flat modules (e.g. `skills/fluff-analysis/scripts/test-fluff-analysis.sh` importing from a here-doc). Retiring a module can still pass the prescribed scan while live importers remain in harnesses; deleting the flat module then breaks those harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Decision-log bullet title omits `.claude/skills/` (line 14)
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The decision-log title scopes to `skills/**/*.py` but the body correctly includes `.claude/skills/`. Operators scanning titles only may be confused about whether dev-only skill scripts are in scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Flat-name grep does not cover package-path imports of the same module (line 49)
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Flat-name grep does not detect package-path imports of the same module. Retiring a `python/foo.py` stub may pass grep while `larch.*` package imports still depend on the underlying module (usually fine for stubs, risky for true deletions). Stub retirement vs full module removal need different grep patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Importer-scan guidance under step 4 may misroute packaging-only migrations
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The importer-scan guidance lives under step 4 (“Cut ALL consumers to direct `cli.py` calls”). Flat-import repointing in standalone skill scripts (e.g. `fluff-analysis.py`) is not always a `cli.py` cutover. The decision-log bullet mitigates this, but a future packaging-only migration checklist outside the sh-to-py recipe could reduce misrouting risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Recipe steps 1–2 still reference flat `python/<module>.py` layout
- **Reviewer(s)**: codex-generalist
- **Severity**: latent
- **Concern**: The recipe still says to add modules under `python/<module>.py` and register `_REGISTRY` in `python/cli.py`, but the same doc says new modules belong under `python/larch/` and `python/cli.py` is now only a shim. Wording predates the branch diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Address the concern above.

---

**Subsumed without separate blocks:** `cursor-specialist-testing` in-scope observations (FINDING_10–14: `sys.path` consumer inventory, directory coverage, GNU grep syntax soundness, decision-log cross-reference, and `lint-retired-scripts` scope) are confirmations with no actionable defect; slot attribution is preserved via FINDING_3 and FINDING_8.

