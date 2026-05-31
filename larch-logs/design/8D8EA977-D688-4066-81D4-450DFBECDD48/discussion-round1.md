## Decision 1: Heavyweight client module depth (git.py / gh.py / agents.py)
- **Question**: How complete should the heavyweight client modules be in Phase 1, given agents.py replaces CI-fix launch scripts only later phases invoke?
- **Resolution**: Full surface. Build every operation the issue lists for git.py, gh.py, and agents.py (full waterfall + failure classification) now, each unit-tested against a stub proc.run. Later phases only call into these.
- **Source**: user

## Decision 2: bash-parity test coverage for Phase 1
- **Question**: Does every ported component carry a bash-parity test, or only redact.py (the sole one named in acceptance)?
- **Resolution**: Parity-test the modules with a clean standalone bash counterpart: redact.py (vs redact-secrets.sh + redact-tmpdir-paths.sh), retry.py (vs lib-net.sh), agents.py (vs launch-cursor/codex/claude-ci.sh). git.py and gh.py get standalone unit tests (their bash logic is scattered inline in ship-pr.sh — no clean diff target).
- **Source**: user

## Decision 3: dev-tool version pinning timing
- **Question**: When are exact latest-stable ruff/pylint/pyright/pytest versions resolved?
- **Resolution**: Resolve and pin exact latest-stable versions (Python 3.12-supporting) in the plan now. The implementer copies them verbatim into python/requirements-dev.txt.
- **Source**: user

## Decision 4: Phase 1 is strictly additive (hard constraint)
- **Question**: What may Phase 1 modify outside the new python/ tree?
- **Resolution**: New files under python/ only, plus edits to .github/workflows/ci.yaml (two new jobs), Makefile (py-lint / py-test targets), root AGENTS.md (repo-layout update), and a new python/README.md. Zero change to the live /implement path. No .sh deleted (strangler-fig; deletion waits until a caller grep shows zero users in a later phase).
- **Source**: issue

## Decision 5: runtime/dev dependency boundary (hard constraint)
- **Question**: What may python/ runtime modules import?
- **Resolution**: Runtime modules import stdlib only (Python >= 3.12). ruff / pylint / pyright / pytest are dev/CI-only and never imported by runtime code. A stdlib-only enforcement test imports every runtime module and asserts no non-stdlib import.
- **Source**: issue
