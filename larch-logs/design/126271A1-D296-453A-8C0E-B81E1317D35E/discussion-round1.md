## Decision 1: Structural model
- **Question**: What existing lint should the new rule mirror?
- **Resolution**: Mirror `python/larch/lint/lint_tempfile_dir.py`: module-level `main(argv) -> int`, `TOOL_FAILURE_EXIT = 2`, frozen `Finding` dataclass, `Record` TypedDict, `BaselineError`, only-shrinks reason-bearing baseline, `--write`/`--initial-reason` regen. AST-based static analysis only; never import scanned modules at runtime.
- **Source**: issue / codebase

## Decision 2: Scan surface (inverted from the model)
- **Question**: Which files does this lint scan?
- **Resolution**: Test files only — `python/tests/**/test_*.py` and `python/test_*.py`. This is the inverse of `lint_tempfile_dir`, which scans production `python/larch/**` and excludes tests.
- **Source**: issue

## Decision 3: False-positive handling (V1 scope boundary)
- **Question**: Does V1 detect the known false positive (late attribute access through the facade)?
- **Resolution**: No. V1 does not attempt late-attribute-access detection; affected lines use the inline suppression `# lint-monkeypatch-binding: ok <reason>` (reason required, G-Py-11).
- **Source**: issue

## Decision 4: Baseline + Makefile wiring
- **Question**: How are existing violations grandfathered and regenerated?
- **Resolution**: Only-shrinks reason-bearing baseline (G-Enf-2) mirroring `lint_tempfile_dir`. Add `regen-monkeypatch-facade-binding-baseline` Makefile target + `.PHONY` entry; add `python/cli.py lint monkeypatch-facade-binding` to `py-lint-checks-fast`; add registry entry to `python/larch/cli.py`.
- **Source**: issue

## Decision 5: Rule precision (hard constraints)
- **Question**: What exactly is flagged vs. skipped?
- **Resolution**: Flag `monkeypatch.setattr(M, "name", ...)` and the dotted-string `monkeypatch.setattr("pkg.mod.name", ...)` form when M is a repo module that binds `name` only by import (not `def`/`class`/assignment/annotated-assignment). Skip silently: non-literal attribute names, first args not resolving to a repo module, and modules whose source cannot be located.
- **Source**: issue
