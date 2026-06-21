# Review Round 2

- Mode: `diff`
- 4 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_2: No test that pause before Gate C never resumes into diagram generation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires that a pause before Gate C must not resume into diagram generation (Step 5b.5). Routing logic appears correct but lacks explicit coverage for `step-4` without `step-4b`. A regression in `_determine_step` could resume a run paused after Step 4 at Step 5b.5, generating/upserting architecture diagrams before Gate C approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add `test_determine_step` with step-3/3b/3b/4 present and step-4b absent; assert resume target is 4b not 5b.5.
  - From cursor-specialist-testing-output.txt: Add `test_determine_step_after_step4_resumes_gate_c_not_diagram` (and optional pause_load fixture) asserting resume target is 4b/5, not 5b.5.


### FINDING_4: `strip_diagram_sections` leaves Mermaid-bearing text in committed logs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-log-hygiene-output.txt
- **Severity**: important
- **Concern**: `strip_diagram_sections` uses line-prefix heuristics (`graph|flowchart|sequenceDiagram|…` and `-->`-style edges) instead of dropping all Mermaid-bearing capture text. It also drops any line matching `_EDGE_LINE_RE` globally, not only inside diagram sections. Unfenced or partial generator output can survive stripping (`participant …`, `->>` sequence arrows, `subgraph …`, `classDef` / `style` lines, indented node declarations). Those strings flow into `_sanitize_bounded_text` → `detail=` / `reason=` in `write_bounded_diagram_failure_log`, then into `execution-issues.md` and committed run logs. A failure capture containing a line like `module A --> module B failed` could also be stripped from bounded logs, making operator repair harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict edge-line removal to in-section/in-fence state, or narrow the regex to known Mermaid contexts.
  - From dyn-log-hygiene-output.txt: Treat any diagram-failure capture as untrusted Mermaid until proven otherwise: strip fenced blocks first, then drop lines until the next markdown heading when inside `## Architecture Diagram` / `## Code Flow Diagram`, and fail closed to a fixed token such as `diagram-content-redacted` when any ``` or known Mermaid keyword remains. Apply the same helper in `python/run_logs.py:append_failure_main` for `Warnings` entries whose `--output-file` is diagram-related, and add regression tests for `participant`, `->>`, and `subgraph` tails.


### FINDING_10: `pause_load_main` rejects `STEP=4b` that `pause_save_main` can persist
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `pause_save_main` can persist `STEP=4b` because `_determine_step` falls through to `step-name-registry.tsv:16` after `.completed/step-4` and before Gate C finishes, but `pause_load_main` rejects `4b` as `invalid-step`. Concrete scenario: user pauses at the Gate C prompt before approval, the marker is saved with `STEP=4b`, then resume clears the marker and emits `LOAD_OK=false`, so the run cannot resume to Gate C or continue to the new Step 5b.5 path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Add `4b` to the allowed pause-load step set, and add a pause-load round-trip test for a marker with `STEP=4b`.


### FINDING_11: `step5b_prepare_main` prepare-failed path still breadcrumbs to Step 5c
- **Reviewer(s)**: dyn-diagram-flow-output.txt
- **Severity**: important
- **Concern**: `step5b_prepare_main` still prints `continuing to Step 5c` on the prepare-failed path, but this branch was not updated for the new `5b → 5b.5 → 5c` ordering. It does write `.completed/step-5b` via `_step5b_mark_complete`, yet it never writes `.completed/step-5b.5`. An orchestrator that follows that stdout breadcrumb can skip Step 5b.5 and jump straight to Step 5c. Publish then fail-closes (`publish_core` / `step5c_core` both require `step-5b.5`), so the run stalls with a repair breadcrumb instead of publishing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-diagram-flow-output.txt: Change the prepare-failed message to `continuing to Step 5b.5`, and add a regression test that `FILE_DESIGN_OOS_STATUS=prepare-failed-continue` does not emit any `Step 5c` continuation text.


