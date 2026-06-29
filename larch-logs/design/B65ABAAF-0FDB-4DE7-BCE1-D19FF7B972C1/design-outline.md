## Proposed Design Outline

### Goals
- Regenerate `python/complexity-baseline.json` from live ruff so it holds only genuine residual violations; split-removed rows drop out.
- Tighten `python/ruff.toml` per-file-ignores per-code: keep only codes each production file still violates; delete fully-clean entries.
- Re-document the re-tightened policy in `docs/linting.md` and keep `make py-lint` green.

### Non-goals
- No new complexity-reducing refactors; splits 2/14 through 12/14 own that paydown.
- No new per-package config, directory-scoped ruff sections, or new linter mode.
- No edits to test exemptions, non-complexity ignores, the audit config shape, or the other ratchets (subprocess / env / layering).

### Approach sketch
- Reuse existing mechanisms only. `make regen-complexity-baseline` (= `cli.py lint complexity-baseline --write`) regenerates the baseline via `ruff-complexity-audit.toml`, which already sees every production violation.
- Treat the regenerated baseline as ground truth: a production `(file, code)` stays in `ruff.toml` per-file-ignores only when it still appears in the baseline; drop the rest.
- Preserve byte-canonical baseline output (sorted, 2-space, trailing newline) and all test-facing globs.
- Verify with `make py-lint`; tightened ignores plus regenerated baseline must leave it green.

### Surfaces in scope
- `python/complexity-baseline.json` (regenerated)
- `python/ruff.toml` (per-file-ignores, complexity codes only)
- `docs/linting.md` (policy section)

### Open questions
- Mechanize the `ruff.toml` tightening as a one-shot derivation (honors "no new make targets") or add a committed regen target for reproducibility? Lean one-shot.
- Confirm baseline path keys map cleanly to `ruff.toml` basename globs when deriving the kept-ignore set; resolve during plan drafting.
