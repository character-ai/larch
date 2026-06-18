## Decision 1: CI-fix integration scope for python-pyright
- **Question**: How much of the `/implement --merge` auto-fix machinery should the new `python-pyright` job be wired into?
- **Resolution**: Full integration (clean). Register `python-pyright` in `python/config.py` `CI_FIXABLE_JOBS`, `scripts/ci-failed-jobs.sh`, `scripts/test-ci-failed-jobs.sh` (drift guard), and `python/ci_monitor.py` (replay + toolchain). Implement via new Makefile sub-targets (`py-lint-main` + `py-typecheck`) so CI delegates to `make` and replay uses `make` targets. This resolves the rejected FINDING_3 (replay honors the Makefile `PYLINT_JOBS` sysconf fallback locally; CI overrides via env) without hardcoding `-j0` in replay. `make py-lint` stays an unchanged local umbrella running all three tools.
- **Source**: user

## Decision 2: close docs and pip-retry gaps
- **Question**: Should the plan close the `docs/linting.md` staleness and the `python-pyright` pip-retry env gap (rejected FINDING_2)?
- **Resolution**: Yes. Update `docs/linting.md` prose describing the `python-lint` job, and carry the `PIP_RETRIES` / `PIP_DEFAULT_TIMEOUT` install env block onto `python-pyright`.
- **Source**: user
