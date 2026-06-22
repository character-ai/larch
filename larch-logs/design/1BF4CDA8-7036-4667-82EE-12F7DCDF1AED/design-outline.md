## Proposed Design Outline

### Goals
- Re-enable ruff complexity rules `C901`, `PLR0911`, `PLR0912`, `PLR0913`, `PLR0915` so new or over-threshold `python/` code fails `make py-lint` and CI.
- Grandfather existing production violations so `cd python && ruff check .` stays green today.
- Document the ratchet and its removal path in `docs/linting.md`.

### Non-goals
- Do not fix or refactor existing complexity violations (god-function split is a separate item).
- No changed-files lint lane and no new Makefile/CI wiring.
- No threshold overrides; use ruff defaults.

### Approach sketch
- Remove the 5 codes from the global `[lint] ignore` list in `python/ruff.toml`.
- Add the same 5 codes to the existing `test_*.py` block under `[lint.per-file-ignores]` (exempt tests).
- Enumerate currently-violating production files via ruff, then grandfather each under `[lint.per-file-ignores]` with only the codes that file actually trips.
- Verify the tree is green after the baseline; the only ruff output should be on new over-budget code.
- Add a `docs/linting.md` subsection describing the ratchet: per-file entries shrink as modules are cleaned.

### Surfaces in scope
- `python/ruff.toml` — config change (un-ignore + grandfather baseline).
- `docs/linting.md` — ratchet documentation.

### Open questions
- None. The exact grandfather file list is derived mechanically from ruff output during plan drafting.
