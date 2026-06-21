# Review Round 1

- Mode: `diff`
- 10 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Diagram mode lacks pre–Step-5b sentinel guards
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-diagram-flow-output.txt
- **Severity**: important
- **Concern**: `--mode diagram` in `design-step3b-entry.sh` can classify or generate Step 5b.5 work (architecture diagrams, `.completed/step-5b.5`) before Gate C approval and Step 5b OOS filing. Ordering is SKILL-orchestrator-only today; mistaken early CLI or orchestrator invocation violates plan ordering and acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: At diagram branch entry, require .completed/step-5b (and optionally step-4b); fail closed with repair breadcrumb and non-zero exit if absent.
  - From dyn-diagram-flow-output.txt: In diagram mode, fail closed unless `.completed/step-4` (or a dedicated Gate-C-approved sentinel) and `.completed/step-5b` exist; emit a clear error when guards fail.


### FINDING_2: `pause_load` rejects `STEP=5b` while `_determine_step` can save it
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `pause_load` allows `5b.5` but not `5b` while `_determine_step` can return `5b`. Pausing during Step 5b OOS filing saves `STEP=5b`; resume fails with invalid-step and clears pause state, blocking mid-OOS recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add 5b to the allowed pause step set; add pause_load test for STEP=5b.


### FINDING_4: `publish_main` missing Step 5b.5 repair breadcrumb on rc 5
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `publish_main` returns rc 5 when `step-5b.5` sentinel is missing without emitting the repair breadcrumb that `step5c_core` prints. Direct `python/cli.py design publish` fails closed silently from an operator perspective.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit the same missing step-5b.5 repair breadcrumb before returning 5.
  - From cursor-specialist-edge-cases-output.txt: Print the same repair breadcrumb as step5c_core before returning 5; assert it in test_publish_main_requires_step5b5_sentinel.


### FINDING_6: Bounded diagram failure sidecars committed in design run logs
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-diagram-flow-output.txt, dyn-log-hygiene-output.txt
- **Severity**: important
- **Concern**: `write_bounded_diagram_failure_log` writes top-level `*-diagram-failure.bounded.log` sidecars in `DESIGN_TMPDIR`, but `_PUBLISH_EXCLUDE_TOPLEVEL_NAMES` excludes only legacy `architecture-diagram-*` failure logs. Design log publish still copies bounded sidecars into committed `larch-logs/design/<RUN_ID>/`, violating plan acceptance that diagram failure captures stay out of committed design run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Delete the sidecar after append, write it outside DESIGN_TMPDIR, or exclude a top-level *-diagram-failure.bounded.log glob.
  - From cursor-specialist-edge-cases-output.txt: Add *-diagram-failure.bounded.log to _PUBLISH_EXCLUDE_GLOBS or _PUBLISH_EXCLUDE_TOPLEVEL_NAMES and cover with python/test_design_log_publish_flow.py.
  - From dyn-diagram-flow-output.txt: Add a top-level glob such as `*diagram-failure.bounded.log` (or an explicit basename set) to `_PUBLISH_EXCLUDE_TOPLEVEL_NAMES` / `_PUBLISH_EXCLUDE_GLOBS`, and extend `python/test_design_log_publish_flow_flow.py` to assert exclusion.
  - From dyn-log-hygiene-output.txt: Add a top-level exclusion for `*-diagram-failure.bounded.log` (or a dedicated basename set), and add a regression test in `python/test_design_log_publish_flow.py` asserting publish skips them.


### FINDING_7: `write_bounded_diagram_failure_log` does not redact `reason=`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-log-hygiene-output.txt
- **Severity**: important
- **Concern**: `write_bounded_diagram_failure_log` normalizes `reason=` with whitespace collapse only; unlike `_bounded_detail`, it does not run `redact.redact()` or strict tokenization. Raw stderr, inline Mermaid, or secrets passed as `reason` can reach the sidecar and `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Redact and strip reason before writing, or enforce enum-safe reason tokens and keep free-form content only in redacted raw_capture_path detail.
  - From dyn-log-hygiene-output.txt: Run the same strip + `redact.redact()` pipeline on `reason=` that `_bounded_detail` uses for `detail=`, and cap `reason` length.


### FINDING_8: Unfenced Mermaid in code-flow failure tails reaches committed implement logs
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Bounded code-flow failure logging can carry unfenced Mermaid-like stdout into `DIAGRAM_REASON` and `execution-issues.md`. A failed generator that prints `graph TD` / `A-->B` without a diagram heading or mermaid fence bypasses `strip_diagram_sections`; Step 7a then flushes that warning into committed implement run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Drop stdout from failure tails or strip Mermaid syntax lines before composing tail= and bounded details


### FINDING_9: Plan-listed structural harness pins missing from `test-design-structure.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-listed structural harness pins for Step 5b routing, no-chat verbosity, and Step 2b anti-halt wording were not all added. A future edit could reintroduce direct Step 5b to Step 5c skips, restore diagram chat emission in verbosity rules, or promise pre-approval diagram generation without CI failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add the missing contains/not_contains assertions from the plan to test-design-structure.sh.


### FINDING_11: `_determine_step` routes to `5c` without requiring `step-5b`
- **Reviewer(s)**: dyn-diagram-flow-output.txt
- **Severity**: important
- **Concern**: `_determine_step` routes to `5c` whenever `.completed/step-5b.5` exists and `.completed/step-5c` is absent, without requiring `.completed/step-5b`. If Step 5b.5 completes out of order (orchestrator mis-order, manual sentinel repair, or partial tmpdir), pause-save writes `STEP=5c`, so resume skips Step 5b OOS filing even though `publish_core` / `step5c_core` still fail closed on missing `step-5b`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-diagram-flow-output.txt: Gate the `5c` branch on both sentinels (`step-5b` and `step-5b.5` present), or return `5b` when `step-5b.5` exists without `step-5b`; add a pause test for that sentinel combination.


### FINDING_12: Legacy `STEP=5c` pause markers bypass Step 5b.5 on resume
- **Reviewer(s)**: dyn-diagram-flow-output.txt
- **Severity**: important
- **Concern**: Pause resume binds `ROUTE=resume@{STEP}` from the saved marker only. Pre-5b.5 runs that paused after Step 5b with `STEP=5c` (old `_determine_step` behavior) resume straight to Step 5c on upgraded larch, bypassing Step 5b.5 even when `.completed/step-5b.5` is absent. Publish then fails closed with the repair breadcrumb instead of resuming diagram work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-diagram-flow-output.txt: On pause load or route, downgrade `resume@5c` to `resume@5b.5` when `step-5b` is present and `step-5b.5` is absent; add a regression test for legacy `STEP=5c` markers.


### FINDING_13: `strip_diagram_sections` misses unfenced and generic fenced diagram syntax
- **Reviewer(s)**: dyn-log-hygiene-output.txt
- **Severity**: important
- **Concern**: `strip_diagram_sections` only drops ` ```mermaid ` fences and `## Architecture Diagram` / `## Code Flow Diagram` sections. Generic triple-backtick blocks and unfenced graph lines (for example bare `graph TD` / `A-->B`) pass through into `_bounded_detail`, then into `detail=` on the bounded sidecar and into Step 7a `DIAGRAM_REASON` tails via `pr_body._diagram_failure_capture`. Those surfaces are flushed into committed run logs through `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-hygiene-output.txt: Extend stripping to elide any fenced code block when the capture is diagram-failure context, or reject/limit `detail=` to a fixed token set (site/reason/exit-code only). Add a unit test with unfenced graph output and assert no graph tokens in sidecar, warning body, or `reason` tail.


