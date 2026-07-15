## Pieces

### Piece 1: SECURITY.md sweep
- Scope: `SECURITY.md` — re-point all 24 dead pointers to current `python/larch/**` and `python/tests/**` paths; remove the retired Step 3.6 assessor paragraph; update the `scripts/lib-run-log` breadcrumbs reference to the Python path; add one reason-bearing suppression for `.claude/hook-audit.log`.
- Firm-headings: `### UPDATED: SECURITY.md`
- Acceptance: enumeration procedure prints nothing for `SECURITY.md`; existing tests pass.
- Dependencies: none
- Size estimate: ~250 lines changed (SECURITY.md edits)

### Piece 2: doc-pointer-paths lint
- Scope: `python/larch/lint/lint_doc_pointer_paths.py` (new), `python/tests/lint/test_lint_doc_pointer_paths.py` (new), `python/larch/cli.py` (1 line), `python/lint-module-manifest.json` (1 entry), `Makefile` (3 lines)
- Firm-headings: `### NEW: python/larch/lint/lint_doc_pointer_paths.py`, `### NEW: python/tests/lint/test_lint_doc_pointer_paths.py`, `### UPDATED: python/larch/cli.py`, `### UPDATED: python/lint-module-manifest.json`, `### UPDATED: Makefile`
- Acceptance: `python3 python/cli.py lint doc-pointer-paths` exits 0; tests pass; `python3 python/cli.py lint module-manifest` exits 0.
- Dependencies: blocked-by Piece 1
- Size estimate: ~170 lines added

