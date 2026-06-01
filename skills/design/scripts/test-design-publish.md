# test-design-publish.sh

Offline harness for [`design-publish.sh`](design-publish.md). Stub `PATH` shims exercise argv, preconditions, plan-write failure, happy path, ordering, `SESSION_ID` empty, `PUBLISH_OK=false`, unexpected publish, and render env binding.

Wired via `make test-design-publish` (see `Makefile`).
