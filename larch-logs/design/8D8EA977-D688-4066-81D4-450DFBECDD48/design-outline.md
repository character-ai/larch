## Proposed Design Outline

### Goals
- Stand up a flat `python/` tree (stdlib-only runtime, Python >= 3.12) with all 10 foundation modules built and unit-tested.
- Add two CI gates (Python Lint: ruff + pylint + pyright strict; Python Tests: pytest) plus `make py-lint` / `py-test`, green on colocated tests.
- Prove behavioral parity for the redaction, retry, and agent-launch ports — with zero change to the live `/implement` path.

### Non-goals
- No live-path change: `ship-pr.sh` and all skills keep using bash until Phase 7 flips `LARCH_SHIP_PR_IMPL=python`.
- No `.sh` deletion (strangler-fig); deletion waits for a later phase's zero-caller grep.
- No state file / `--resume-phase` (locked: idempotent process, ground-truth recovery).

### Approach sketch
- Author `config.py` first, then build outward: `proc.py` -> `errors.py`/`outcomes.py` -> `run_context.py` -> `logging_util.py` -> `redact.py` -> `retry.py` -> `git.py` -> `gh.py` -> `agents.py`.
- All inter-function data are `@dataclass(frozen=True)`; the `proc.run` seam is injected so git/gh/agent calls unit-test against a stub runner (no network, no real binaries).
- Full operation surface for `git.py` / `gh.py` / `agents.py` (agents = launch + waterfall + failure classification), each unit-tested.
- Parity tests for `redact.py`, `retry.py`, `agents.py` (clean bash counterparts); unit tests for the rest.
- CI jobs modeled on the existing `lint` job; pin exact latest-stable `ruff`/`pylint`/`pyright`/`pytest` (py3.12) in `requirements-dev.txt`.

### Surfaces in scope
- `python/` (new): config, proc, errors, outcomes, run_context, logging_util, redact, retry, git, gh, agents + colocated `test_*.py`; `requirements-dev.txt`, `ruff.toml`, `pyrightconfig.json`, `.pylintrc`, `pyproject.toml`, `README.md`.
- `.github/workflows/ci.yaml` (two new jobs), `Makefile` (py-lint / py-test), root `AGENTS.md` (repo-layout update).

### Open questions
- None. Module depth, parity scope, and version-pinning timing were resolved in Round 1.
