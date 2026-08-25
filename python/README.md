# Retired Python surface

All larch production commands are Rust-owned and enter through
`scripts/larch.sh`. `python/cli.py` and `python/larch/cli.py` preserve an empty
dispatcher boundary until release artifact cleanup in issue #8903. The
dispatcher registry must remain empty and has no Python command fallback.

Issue #8902 retired the Python lint, type-check, test, sharding, dependency,
and CI surfaces. The remaining files are removal inputs, static fixtures, or
historical tests owned by issue #8903. They are not a supported runtime or CI
lane. Repository validation is Rust-owned; see `../docs/linting.md` and
`../docs/rust-testing.md` for current commands.
