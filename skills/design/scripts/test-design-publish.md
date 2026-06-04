# test-design-publish.sh

Offline harness for [`design-publish.sh`](design-publish.md). Stub `PATH` shims exercise argv, preconditions, plan-write failure, happy path, ordering, `SESSION_ID` empty, `PUBLISH_OK=false`, unexpected publish, and render env binding.

Wired via `make test-design-publish` (see `Makefile`).

## Recent contract coverage

- Covers non-zero publish exits that also print `PUBLISH_OK=true` and empty-`SESSION_ID` `publish-skipped` rendering with rename/reentry marker skipped.
