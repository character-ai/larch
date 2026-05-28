## Proposed Design Outline

### Goals
- Land all 12 OOS items (Cluster 1 breadcrumb pipeline, Cluster 2 render-cache/symlink hardening, Cluster 3 `sanitize_diagnostic_line` adoption) in one combined PR over the shared output/publish surfaces.
- Eliminate the `/implement` Step 5 early-exit cascade: nested Family-B scripts must not satisfy the orchestrator's monitor coupling.
- Close the redaction and failure-mode parity gaps in `breadcrumb-monitor.sh` and `design-log-publish.sh` (live monitor redaction + hard-abort on breadcrumb-helper failure).

### Non-goals
- No refactor of the FD-3 / `lib-quiet` public contract beyond auditing and adding opt-in `sanitize_diagnostic_line` call sites.
- No new breadcrumb taxonomy, status-file format, or `PUBLISH_OK` schema change.
- No re-hardening of the already-merged render-cache symlink protections from #2823; only the four follow-up concerns are in scope.

### Approach sketch
- Cluster 1 Item A: in `scripts/run-step5-review.sh` (and any other top-level Family B caller), unset `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` / `LARCH_BREADCRUMBS_SURFACED_FILE` / `LARCH_PAIRED_PID_FILE` before synchronous nested Family-B calls so the orchestrator's pair couples only with its top-level writer. Add a focused harness covering the early-exit cascade.
- Cluster 1 Item B + C + D: pipe each line through `redact-tmpdir-paths.sh` inside `breadcrumb-monitor.sh:149` (drop-on-fail); convert the breadcrumb-helper invocation in `design-log-publish.sh:402-405` to fail-closed (`PUBLISH_OK=false`); add 1-3 sentence cross-refs in `design-log-publish.md` and the early `SECURITY.md` summary pointing at the canonical `## Breadcrumb stream redaction` section.
- Cluster 2 Items A + D: close the parent-directory replacement race between the tree-wide `find -type l` scan and the `find -type f` enumeration in both the render-cache (lines 384-431) and plan-review (lines 320-374) loops, or explicitly restate the gap. Cluster 2 Item B: add a render-cache path-escape harness case mirroring the plan-review one at `test-design-log-publish.sh:779`. Cluster 2 Item C: verify and tighten the `SECURITY.md` render-cache fail-closed note (line 186 already documents a high-level form; clarify near line 139 if needed).
- Cluster 3: route `scripts/ship-pr.sh:719-723` failure-log relay and `skills/implement/scripts/step-7a.sh:368-380` `CODE_FLOW_SKIP_REASON` through `sanitize_diagnostic_line`; audit other external-stderr passthrough call sites in `scripts/lib-quiet.sh:105-122`; add the embedded-`=` `REASON_TOKEN` harness case to `scripts/test-mermaid-fragments.sh`.

### Surfaces in scope
- `scripts/lib-quiet.sh`, `scripts/breadcrumb-monitor.sh`, `scripts/design-log-publish.sh`, `scripts/run-step5-review.sh`, `scripts/ship-pr.sh`, `skills/implement/scripts/step-7a.sh`.
- `SECURITY.md`, `scripts/design-log-publish.md`.
- `scripts/test-design-log-publish.sh`, `scripts/test-mermaid-fragments.sh`, and a new (or extended) harness for the sentinel-inheritance regression.

### Open questions
- Item 2C: render-cache fail-closed policy is already documented at `SECURITY.md:186`; verify whether a separate note near line 139 is still required, or whether 2C is satisfied by the existing line.
- Item 1A path choice (unset-env-before-nested-call vs hide-from-child wrapper) deferred to plan review; outline favors the lighter unset-env approach.
