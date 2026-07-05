# test-design-structure.sh

Structural guard for the `/design` runtime contract.

The harness pins the mixed Step 0/1 migration surface:

- Step 0 session uses the direct Python `design step0-session` verb.
- Ported Step 0/1 fences use bare launcher verbs.
- Clarify and Step 2+ fences still use `*.sh` launcher basenames.
- The PID-keyed launcher dual-dispatches to Python verbs or legacy shell wrappers.
- Retired Step 0/1 shell bodies are listed in `python/migrated-scripts.tsv` and absent from the runtime tree.

It also pins the Python lifecycle strings for parsed argv persistence, degraded-tools relay, route/init result-env handling, pause-aware sentinel ordering, clarify hard halt staging, brainstorm collection idempotency, and re-entry cleanup.

It runs the `/design` `SKILL.md` closure growth ratchet after in-place prose compression. The ratchet includes blank-line-neutral content-token metrics.

The harness pins Gate A, Gate B default, and Gate C prompt-copy delegation to `python/cli.py design render-gate`, including CLI registry and lifecycle stdout registration.

The harness also pins the post-approval Step 5 reference split: `skills/design/SKILL.md` keeps the Step 5 entry read, prepare fence, `oos-step5b-dispatch.md` adjacency, diagram/Step 5c fences, and final-summary bindings; `skills/design/references/finalize-step5.md` owns the moved OOS, diagram, compose/publish, shared readability-anchor, and warning-replay body prose. It also requires the restored Step 2b shared readability anchor in `skills/design/SKILL.md`. It verifies sanitizer fail-closed paths write `architecture-diagram.skipped`, chat diagram markers remain absent, and moved Step 5 body needles are not duplicated inline.
It also pins the repeat-fingerprint silent-yield contract across Tier-1 prose, shared wait prose, `/design` Step 3 post-loop routing, and Step 5c routing. It keeps the shared `orchestrator-never.md` distinction between `/design` premature-notification probes and the narrower `/implement` Step 3/5 post-denial retry contract.
