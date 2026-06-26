## Decision 1: Linter 1 detection breadth
- **Question**: Narrow high-signal rule (only modules that hold a Runner but bypass it) vs broad rule (all library modules calling subprocess directly)?
- **Resolution**: Broad rule + baseline. Flag every `python/` library module calling `subprocess.*` directly. Exclude `proc.py`, test files, and an exemptions allowlist of CLI-glue modules. Snapshot the current ~57 violating modules into a baseline JSON so only NEW violations fail. Mirrors the `lint_complexity_baseline.py` / `lint_keyword_only.py` ratchet.
- **Source**: user

## Decision 2: Existing violations — fix vs baseline/allowlist
- **Question**: Fix existing violations now, or allowlist/baseline them?
- **Resolution**: Baseline/allowlist all now. Record all current violations mechanically via `--write` baseline regeneration. Do not edit existing module logic. Real fixes deferred to follow-up issues.
- **Source**: user

## Decision 3: Linter template and suppression mechanisms
- **Question**: Which existing pattern do these linters follow for harness, baseline, and allowlist-with-reason?
- **Resolution**: Mirror `lint_keyword_only.py` exactly. Each linter ships: a baseline JSON (canonical sorted, `--write` regenerates); an optional exemptions JSON with a `reason` field (the CLI-glue / documented allowlist); an inline pragma `# lint-<name>: ok <reason>`; `lint_common` helpers; a `python/cli.py lint <name>` registration; wiring into `py-lint-main` plus a pre-commit hook (`pass_filenames: false`, `always_run: true`, `files: ^python/[^/]+\.py$`); a `regen-<name>-baseline` target; and a pytest harness `python/test_lint_<name>.py` (auto-discovered).
- **Source**: codebase

## Decision 4: config.py ENV_ parsing for Linter 2
- **Question**: How are `ENV_*` constants shaped, and what is exempt?
- **Resolution**: Constants are annotated assignments `ENV_NAME: Final = "VALUE"` (60 present). Linter 2 parses `ast.AnnAssign` (and plain `ast.Assign`) in `config.py`, builds a map `VALUE -> ENV_NAME`, and flags `os.environ.get("X")` / `os.environ["X"]` where `"X"` is a known VALUE, outside `config.py`. Exempt: env names matching `*_SH` (test override seams) and vars with no matching constant.
- **Source**: codebase

## Decision 5: In-flight overlap and sequencing
- **Question**: Does this overlap in-flight `#5167` (packaging) or the `md-to-py-VI` design issues (`#5405`-`#5408`)?
- **Resolution**: No meaningful overlap. The fix surface is new linter files, new baseline data, a localized 2-line `cli.py` dispatch addition, and Makefile / pre-commit / docs wiring. `#5167` (foundation `larch/` package) does not touch `config.py`, `proc.py`, the violation modules, or the Makefile lint targets. The `md-to-py-VI` issues touch skill prose. No postponement, no hard blocked-by edge; relationship is informational.
- **Source**: codebase
