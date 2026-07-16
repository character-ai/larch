## Pieces

### Piece 1: Core detector, tests, and CLI registration
- Scope: `python/larch/lint/lint_status_routing_truthiness.py` (new detector, engine adapter, CLI), `python/tests/lint/test_lint_status_routing_truthiness.py` (all 20 test cases), `python/larch/cli.py` (register command), `python/status-routing-truthiness-baseline.json` (initial generated baseline from live scan)
- Firm-headings: ### NEW: python/larch/lint/lint_status_routing_truthiness.py; ### NEW: python/tests/lint/test_lint_status_routing_truthiness.py; ### UPDATED: python/larch/cli.py; ### NEW: python/status-routing-truthiness-baseline.json
- Acceptance: `python3 -m pytest -q python/tests/lint/test_lint_status_routing_truthiness.py` passes; `python3 python/cli.py lint status-routing-truthiness` exits 0 after baseline; exit codes 0/1/2 verified
- Dependencies: none
- Size estimate: ~840 lines (detector ~145, tests ~420, CLI +1, baseline generated)

### Piece 2: Makefile targets, lint manifest, and docs
- Scope: `Makefile` (add `py-lint-checks-fast` entry and three targets), `python/lint-module-manifest.json` (new-module-justified row), `docs/linting.md` (scan scope, evidence gate, suppression, stale-row, regeneration)
- Firm-headings: ### UPDATED: python/lint-module-manifest.json; ### UPDATED: Makefile; ### UPDATED: docs/linting.md
- Acceptance: `python3 python/cli.py lint module-manifest` passes; `make lint-status-routing-truthiness` passes; `make test-lint-status-routing-truthiness` passes; `make py-lint-checks-fast` passes; `python3 python/cli.py checks run-relevant` clean
- Dependencies: blocked-by Piece 1
- Size estimate: ~120 lines
