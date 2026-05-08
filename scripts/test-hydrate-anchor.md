# scripts/test-hydrate-anchor.sh - contract

Sibling regression harness for `scripts/hydrate-anchor.sh`.

The full behavioral contract lives in `scripts/hydrate-anchor.md`. This harness stubs `gh` on `PATH`, feeds a local anchor-body fixture to the primary script, and verifies that only canonical `SECTION_MARKERS` slugs hydrate into `anchor-sections/`. The fixture includes `token-report` so the split token-report section is covered alongside existing valid slugs. It specifically pins the path-traversal guard by including `../`, `../../`, embedded traversal, and unknown-slug markers and asserting they do not create or clobber files outside the allowed section-fragment set.

## Makefile wiring

Run with `make test-hydrate-anchor`; included in `make test-harnesses` and therefore `make lint`.
