# test-scout-dynamic-archetypes.sh Contract

Regression harness for `scripts/scout-dynamic-archetypes.sh`.

The harness stubs `claude` on `PATH` and exercises valid four-archetype output, over-cap parse failure, duplicate-name rejection with warning, malformed JSON, Claude subprocess failure, empty output, reserved names, invalid focus areas, empty prompt bodies, and standalone frontmatter fence rejection.

Primary callers: `make test-scout-dynamic-archetypes` and `make test-harnesses`.

Edit in sync with `scripts/scout-dynamic-archetypes.sh` and `scripts/scout-dynamic-archetypes.md`.
