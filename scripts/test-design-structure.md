# test-design-structure.sh

Structural guard for the `/design` runtime contract.

The harness pins the mixed Step 0/1 migration surface:

- Step 0 session uses the direct Python `design step0-session` verb.
- Ported Step 0/1 fences use bare launcher verbs.
- Clarify and Step 2+ fences still use `*.sh` launcher basenames.
- The PID-keyed launcher dual-dispatches to Python verbs or legacy shell wrappers.
- Retired Step 0/1 shell bodies are listed in `python/migrated-scripts.tsv` and absent from the runtime tree.

It also pins the Python lifecycle strings for parsed argv persistence, degraded-tools relay, route/init result-env handling, pause-aware sentinel ordering, clarify hard halt staging, brainstorm collection idempotency, and re-entry cleanup.

The harness also pins the post-approval Step 5b.5 architecture-diagram contract: Step 3b is finalize-only, Step 5b.5 owns diagram mode and bounded warning logging, sanitizer fail-closed paths write `architecture-diagram.skipped`, and chat diagram markers remain absent.
