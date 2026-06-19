## Goal
Implement issue #4781: [IMPLEMENTING] [port-drift] [BUG] /design no longer upserts the architecture diagram to the tracking issue.

## Implementation Plan
## Summary

Since the #3681 port of `design-publish.sh` to `python/design_publish.py`, the `/design` publish tail no longer upserts the architecture diagram into the `larch:diagrams` tracking-issue comment. `SKILL.md` and `SECURITY.md` still say it does. Functional regression (not security). Found by the post-#4766 migration-wave audit.

## Root cause

The bash `design-publish.sh` ran a diagrams-upsert block (`UPSERT_RAN` / `ARCHITECTURE_SOURCE`, `--architecture-file` / `--clear-architecture`). The Python `publish_main` has no diagram call, and no other design-side caller of `diagrams upsert` exists — the only `diagrams upsert` invocation in the tree is implement-side (`python/step_7a.py:280`, code-flow). So the architecture-diagram comment is no longer posted at `/design` completion.

## Evidence

- `python/design_publish.py` — `publish_main` contains no `diagram` / `upsert` / `architecture` reference.
- Recovered `design-publish.sh` had the upsert block (`UPSERT_RAN`, `ARCHITECTURE_SOURCE`, `--architecture-file`, `--clear-architecture`).
- `skills/design/SKILL.md:833` lists "diagrams upsert" as part of the `design publish` deterministic tail.
- `SECURITY.md` "larch:diagrams outbound path": "/design Step 5c publishes the Architecture section via python/cli.py design publish (diagrams upsert) ... Architecture diagrams are now posted at /design completion."
- Step 3b still generates `architecture-diagram.candidate.md` / `architecture-diagram.md`, so the diagram is produced but not published.

## Affected files

- `python/design_publish.py` (publish tail) — restore the upsert call.
- `python/test_design_publish.py` — assert the upsert is invoked when an architecture diagram exists, and the clear path when `DIAGRAM_REQUIRED=false`.
- `skills/design/SKILL.md` / `SECURITY.md` — reconcile if behavior is intentionally changed.

## Suggested fix

Restore the architecture-diagram upsert in the `design publish` tail: thread the generated `architecture-diagram.md` (and the `--clear-architecture` path when no diagram) to `python/cli.py diagrams upsert`, matching the bash contract and the `UPSERT_STATUS`-gated `failed-publish` recovery note. Confirm the regression empirically (whether recent `/design` runs posted architecture diagrams) and add a test.

## Related

Adjacent to #4677 (sh-to-py G6.4 Step 5c publish-tail port, still designing), but distinct: this regression is in the already-merged #3681 `design_publish.py` port, not the pending `design-step5c.sh` wrapper #4677 targets. Link them so completing #4677 does not silently re-drop or double-fix the upsert.

## Test plan
(no test plan section in plan-file)
