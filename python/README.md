# Python development tooling

All larch production commands are Rust-owned and enter through
`scripts/larch.sh`. `python/cli.py` and `python/larch/cli.py` preserve an empty
dispatcher boundary until the release artifact cleanup in issue #8903. The
dispatcher registry must remain empty and has no Python command fallback.

The remaining Python files are development and CI support:

- `pytest_sharding.py`, `conftest.py`, and `shard-assignments.json` split the
  temporary Python test job. Issue #8902 owns their retirement.
- `tests/test_cli.py` proves that only the empty dispatcher remains under
  `python/larch/`.
- `tests/test_pytest_sharding.py`, `tests/test_python_cli_invocations.py`, and
  `tests/test_stdlib_only.py` cover the temporary development boundary.
- The tests under `tests/implement/`, `tests/issue/`, and `tests/release/` are
  static contract checks for surviving skills, agents, workflows, and thin
  wrappers. They do not import deleted Python runtime code.
- `../fixtures/plan-fidelity-calibration/` is consumed by the Rust calibration
  command and its Rust integration tests.
- `analyze-issues-fixture.json`, `ship.md`, and the stall-recovery contract
  files remain inputs to Rust code or repository tooling.

## Dependencies

| File | Purpose |
|------|---------|
| `requirements-dev.txt` | Ruff, Pyright, and Pytest for `make py-lint` |
| `requirements-test.txt` | Pytest for `make py-test` and the temporary CI job |

## Run locally

From the repository root:

```bash
make py-lint
make py-test
```

Install `python/requirements-dev.txt` for both commands, or install
`python/requirements-test.txt` when only tests are needed. Python 3.11 or newer
is required for this development tooling.
