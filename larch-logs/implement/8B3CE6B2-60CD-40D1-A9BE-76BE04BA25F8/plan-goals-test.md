## Goal
Implement issue #4916: [IMPLEMENTING] architectural diagram generation overhaul.

## Implementation Plan
## Plan

## Approach

- Treat `NO_SKETCHES` as binding. Draft from direct repo inspection only.
- Keep the plan-review FINALIZE boundary at pre-Gate-C Step 3b only.
- Move diagram classification, orchestrator mermaid authoring, candidate creation, and sanitization to a post-approval step after Gate C **Approve** and Step 5b.
- Insert Step **5b.5** (post-approval architecture diagram) between Step 5b and Step 5c on every happy path.
- Remove all `/design` and `/implement` chat re-emission of diagram bodies. Diagrams are issue-only (`larch:diagrams` upsert).
- Exclude all top-level diagram body artifacts **and diagram-generation/sanitizer failure captures containing Mermaid** from committed design run logs.
- Exclude implement code-flow diagram body artifacts and `code-flow-diagram.failure.log` from committed implement run logs; stop Step 7a from copying failure captures into `larch-logs/implement/<RUN_ID>/`.
- Fail closed on Step 5c / publish when `.completed/step-5b.5` is absent (mirror existing `step-5b` guard).
- On post-approval diagram rejection or missing candidate, write `architecture-diagram.skipped` so publish clears stale issue Architecture content.
- On post-approval diagram generation failure, log **bounded** status tokens only to `execution-issues.md`; never flush partial Mermaid to run logs (design or implement).
- Publish `--clear-architecture` only when `architecture-diagram.skipped` exists (including `DIAGRAM_REQUIRED=false` skip path); never clear from sentinel-plus-missing-files alone.
- Remove pre-approval "diagram generation" anti-halt language from Step 2b; diagram work is explicitly Step 5b.5 after Gate C approval.
- Mirror no-chat-diagram rule in `/implement` SKILL verbosity and NEVER list.
- Keep Step 5c publish behavior unchanged except guards, skip-marker contract, bounded failure logging, comments, and tests.
- Do not change `/implement` routing beyond Step 7a bounded-failure / no-run-log-copy behavior. Add verify-only regression coverage.

## Files to modify/create

### UPDATED: skills/design/SKILL.md

- **Anti-halt continuation reminder**
  - Insert `5b.5` into the sub-step transition chain: `…→5→5b→5b.5→5c.1→5c.5→5c.7→5c.8→6`.
  - Remove `diagrams` from the list of permitted visible outputs after Bash steps. Diagram bodies must never appear in chat.
  - Add a second anti-halt boundary: after Step 5b.5 completes (`.completed/step-5b.5` present), continue immediately to Step 5c.
- **Verbosity control**
  - Remove `architecture diagrams` from the preserved-output bullet. Permitted visible output is breadcrumbs, warnings, structured summaries (plans, voting tallies, findings), and the Step 3 reviewer table only.
  - Add an explicit NEVER: do not print `$DESIGN_TMPDIR/architecture-diagram.md`, `architecture-diagram.candidate.md`, or sanitizer marker bodies to chat.
- **Execution-issues logging carve-out (diagram failures)**
  - Add explicit exception to the global "append full capture verbatim" rule for Step **5b.5** diagram generation **and sanitizer rejection** paths: append **bounded** status lines only (`reason=`, `exit-code=`, `site=design Step 5b.5`); do **not** pipe raw generator stdout/stderr, sanitizer stdout, or candidate bodies through `run-log append-failure`.
  - Optional full capture may land in `$DESIGN_TMPDIR/architecture-diagram-generation.failure.log` or `$DESIGN_TMPDIR/architecture-diagram-sanitizer.failure.log` for operator repair, but both files are excluded from committed run logs (see `design_log_publish_flow.py`).
- **Completion sentinels table**
  - Add row `step-5b.5` | post-approval diagram entry/sanitize fences | boundary-local | between `step-5b` and `step-5c`.
  - Update Step 3b row to describe finalize-only boundary (no diagram artifacts).
  - Remove diagram branch cleanup from Step 3b entry; diagram-mode wrapper owns stale artifact cleanup post-approval.
- **Step 2b anti-halt continue reminders**
  - Replace pre-approval "diagram generation" wording in Step 2b and Step 2b.5 continue blocks with: plan review, Gate B, rejected-findings reporting, and cleanup still must run pre-Gate-C.
  - Add explicit pointer that architecture diagram work runs only at Step **5b.5** after Gate C **Approve** (or `--skip-approve` auto-approve).
- **Rewrite Step 3b as pre-Gate-C finalize boundary only**
  - Banner: `> **🔶 /design 3b: finalize**` (or equivalent finalize label from registry).
  - Run `design-step3b-entry.sh --mode finalize` (not `--mode entry`).
  - Touch `.completed/step-3.5`, pause-check, `ACTION=FINALIZE`, `.completed/step-3b`.
  - Do not classify plans, generate diagrams, write `architecture-diagram.*`, or run diagram sanitizer.
  - Continue to `design-step3b-tail.sh` → Step 4.
- **Update all Step 3 routing prose**
  - Replace "Step 3b completion boundary (FINALIZE + step-3b), then Step 4" wording that implied diagram generation.
  - Gate C **Discuss further** / **Re-run review panel** re-entries must not run diagram generation until a later Gate C **Approve**.
- **Add Step 5b.5 — Post-approval architecture diagram** (new subsection after Step 5b, before Step 5c)
  - **Gate**: run only after Gate C returned **Approve** (or `--skip-approve` auto-approve) and Step 5b finished (success, skip, or non-blocking failure paths that today continue past 5b).
  - **Entry fence**: `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3b-entry.sh --mode diagram`
  - Print: `> **🔶 /design 5b.5: arch diagram**`
  - Parse `DIAGRAM_REQUIRED=` from entry wrapper output.
  - **`DIAGRAM_REQUIRED=false`**: wrapper removes stale diagram files, writes `architecture-diagram.skipped`, emits skip breadcrumb, writes `.completed/step-5b.5`. Continue to Step 5c. Do not print diagram content.
  - **`DIAGRAM_REQUIRED=true`**: relocate the current Step 3b orchestrator authoring block here (between entry and sanitize):
    - Read `skills/design/references/readability-style.md`.
    - Generate mermaid architecture diagram from finalized approved plan.
    - Obey `skills/shared/mermaid-safe-content.md`.
    - Write `$DESIGN_TMPDIR/architecture-diagram.candidate.md` with `## Architecture Diagram` heading and fence.
    - On generation failure: print `**⚠ 5b.5: arch diagram — generation failed, proceeding without diagram (<elapsed>)**`; write optional full capture to `$DESIGN_TMPDIR/architecture-diagram-generation.failure.log` for local repair only; append **bounded** warning to `execution-issues.md` via `design_diagram_log.write_bounded_diagram_failure_log` sidecar (never raw Mermaid); invoke sanitize to fail closed.
    - Do **not** re-emit diagram body to chat under any path.
  - **Sanitize fence**: `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3b-sanitize.sh`
  - Sanitizer silently promotes accepted candidate to `architecture-diagram.md` and writes `.completed/step-5b.5`. On rejection or missing candidate, write `architecture-diagram.skipped`, delete rejected/stale diagram files, emit warning-only breadcrumb with bounded `execution-issues.md` entry (no diagram body). Do not run FINALIZE.
  - Anti-halt: `> **Continue to Step 5c IMMEDIATELY**` only after `.completed/step-5b.5` exists.
- **Rewrite Step 5b exit routing**
  - Replace every `continue to Step 5c` in Step 5b with `continue to Step 5b.5`.
  - Update anti-halt block: Step 5b → Step 5b.5 → Step 5c.
  - Manual OOS recovery prose: finish 5b sequence, then Step 5b.5, then Step 5c.
- **Update finalize invariant**
  - New ordering: Step **5b** (OOS filing) → Step **5b.5** (post-approval diagram) → Step **5c** (plan write + publish + rename). Do not run 5c before 5b.5 sentinel when Gate C already approved.
  - Document mechanical fail-closed: `step5c` / publish refuse when `.completed/step-5b.5` absent (parallel to existing `step-5b` guard).
- **Step 5d warning replay**
  - Change example from `**⚠ 3b: arch diagram — generation failed…**` to `**⚠ 5b.5: arch diagram — generation failed…**`.

### NEW: python/design_diagram_log.py

- **`strip_diagram_sections(text: str) -> str`**: remove `## Architecture Diagram` and `## Code Flow Diagram` sections and fenced ` ```mermaid ` blocks from arbitrary capture text before any run-log append.
- **`write_bounded_diagram_failure_log(tmpdir, *, site, reason, exit_code, raw_capture_path=None) -> Path`**: write a redaction-safe sidecar under the session tmpdir with only bounded KVs (`reason=`, `exit-code=`, optional one-line `detail=` without fence content); return path suitable for `run-log append-failure --output-file`.
- **`bounded_diagram_warning_body(reason, exit_code) -> str`**: compose the `Warnings` markdown bullet for orchestrator-visible `execution-issues.md` append without Mermaid.
- Shared by design Step 5b.5 sanitize/generation paths and implement Step 7a / `pr_body.generate_code_flow_diagram` failure logging.
- Stdlib-only; pytest in `python/test_design_diagram_log.py`.

### UPDATED: skills/design/references/approval-gates.md

- Update settled review paths: Step 3b finalize → Step 4 → Gate C → on **Approve** only: Step 5b → Step 5b.5 → Step 5c.
- Remove wording that diagram generation happens at Step 3b or before Gate C.
- Gate C **Approve final design** bullet: proceed to Step 5b, then post-approval diagram (5b.5), then Step 5c.
- **Discuss further** / **Re-run review panel**: explicit that diagram step does not run until a subsequent **Approve**.
- Preserve cap, degraded-panel, and re-entry semantics unchanged otherwise.

### UPDATED: skills/design/scripts/design-step3b-entry.sh

- Split responsibilities by `--mode`:
  - **`finalize`** (pre-Gate-C Step 3b): touch `.completed/step-3.5`, pause-check, `ACTION=FINALIZE`, `.completed/step-3b`. No classifier, no diagram files, no `DIAGRAM_REQUIRED` emission required for orchestrator branching.
  - **`diagram`** (post-approval Step 5b.5): run existing classifier unchanged; emit `DIAGRAM_REQUIRED=true|false`; on false path write `architecture-diagram.skipped`, clean stale artifacts, write `.completed/step-5b.5`, exit without FINALIZE; on true path clean stale artifacts and exit for orchestrator authoring. Do not run FINALIZE in diagram mode.
- Keep `--mode entry` as deprecated alias for `finalize` only if harnesses require it; SKILL uses explicit mode names.

### UPDATED: skills/design/scripts/design-step3b-entry.md

- Document `finalize` vs `diagram` modes.
- State diagram mode is post-Gate-C-Approve / post-Step-5b only.
- Remove claims that Step 3b owns plan-review FINALIZE plus diagram generation together.

### UPDATED: skills/design/scripts/design-step3b-sanitize.sh

- Remove printing of `---LARCH-DIAGRAM-BEGIN---` / `---LARCH-DIAGRAM-END---`.
- Remove `run_step3b_finalize` calls; this script is post-approval only.
- **Accepted path**: silently promote candidate to `architecture-diagram.md`; delete failure logs; write `.completed/step-5b.5`.
- **Missing-candidate / sanitizer-rejection paths**: delete `architecture-diagram.md` and candidate; touch empty `architecture-diagram.skipped`; append **bounded** warning to `execution-issues.md` via `design_diagram_log.write_bounded_diagram_failure_log` (pass bounded sidecar to `append-failure --output-file`; do **not** pass raw sanitizer stdout or a Mermaid-bearing `architecture-diagram-sanitizer.failure.log`); write `.completed/step-5b.5`; exit 0 (warning-only, non-blocking).
- Retire writing full sanitizer output to `architecture-diagram-sanitizer.failure.log` on fail-closed paths; if a local repair file is kept, it must be bounded/stripped only and is never published.
- Update warning breadcrumbs and `--site` strings from `3b` to `5b.5`.
- Do not run plan-review FINALIZE.

### UPDATED: skills/design/scripts/design-step3b-sanitize.md

- Remove chat-marker emission invariant.
- Document silent promotion, skip-marker on fail-closed paths, bounded failure logging via `design_diagram_log.py`, and post-approval `.completed/step-5b.5` sentinel.

### UPDATED: skills/design/scripts/design-step3b-tail.sh

- Follow finalize-mode Step 3b only.
- Do not depend on diagram artifacts.
- Keep Step 4 rejected-findings markers, Gate C preview, and `.completed/step-4` behavior unchanged.

### UPDATED: skills/design/scripts/design-step3b-tail.md

- Purpose: tail after Step 3b finalize boundary, not diagram generation.

### UPDATED: skills/design/scripts/step-name-registry.tsv

- Relabel Step 3b to finalize-oriented short name (e.g. `finalize`).
- Add `5b.5` row with short name `arch diagram`.
- Ensure registry order places `5b.5` after `5b` and before `5c` for pause/resume scanning.

### UPDATED: python/design_lifecycle.py

- **`step5c_core`**: after existing `.completed/step-5b` check, require `.completed/step-5b.5`; on absence emit repair breadcrumb `**⚠ Step 5c: missing .completed/step-5b.5 — post-approval diagram step incomplete; repair Step 5b.5 before publish**` and return rc `1` (same fail-closed posture as missing `step-5b`).
- Update `_setup_step5c_design` helper consumers: all Step 5c tests must touch `step-5b.5` sentinel alongside `step-5b`.

### UPDATED: python/design_publish.py

- **`publish_main`**: after existing `step-5b` guard (currently returns rc `5`), require `.completed/step-5b.5`; return rc `5` when absent (no plan write, no rename).
- **Diagram upsert tail (narrow clear semantics)**:
  - When readable non-empty `architecture-diagram.md` exists → upsert with `--architecture-file`.
  - When `architecture-diagram.skipped` exists (including `DIAGRAM_REQUIRED=false` entry path and sanitizer fail-closed path) → upsert with `--clear-architecture`.
  - When `.completed/step-5b.5` is present but **neither** non-empty `architecture-diagram.md` **nor** `architecture-diagram.skipped` exists → **do not** call `--clear-architecture`; skip diagram upsert and append bounded `Warnings` entry (`reason=diagram-artifact-missing-after-step5b5`) so a lost tmpdir file cannot wipe a valid issue diagram.
  - When neither diagram nor skip marker and upsert is skipped, plan write/rename still proceed (non-blocking tail).
- Update module comments: Step 5c consumes post-approval artifacts written by Step 5b.5; clear only on explicit skip marker.

### UPDATED: python/design_pause.py

- **`_determine_step`**
  - Keep pre-Gate-C rule: after `step-3b` finalize and before `step-4`, resume to `4` (not diagram).
  - Replace direct `step-5b` → `5c` jump with: when `step-5b` present and `step-5b.5` absent, return `5b.5`; when `step-5b.5` present and `step-5c` absent, return `5c`.
  - Do not resume to diagram generation when paused after Step 3/3.5/3b finalize but before Gate C / Step 4.
- **Allowed pause marker set**: add `5b.5` to the validated step id set.

### UPDATED: python/design_log_publish_flow.py

- Extend `_PUBLISH_EXCLUDE_TOPLEVEL_NAMES` with top-level diagram body and failure-capture artifacts:
  - `architecture-diagram.candidate.md`
  - `architecture-diagram.skipped`
  - `architecture-diagram-generation.failure.log`
  - `architecture-diagram-sanitizer.failure.log`
- Keep existing `architecture-diagram.md` exclusion.
- Preserve curated nested subtree behavior unchanged.

### UPDATED: python/step_7a.py

- **Remove `_copy_diagram_failure_log`** and its call site on diagram failure; diagram failure diagnostics are durable only via bounded `execution-issues.md` warning (`_append_diagram_warning` with `DIAGRAM_REASON` carrying `rc=` and capped redacted tail).
- On diagram failure, do **not** copy `code-flow-diagram.failure.log` (or any code-flow diagram body file) into `larch-logs/implement/<RUN_ID>/`.
- Optional tmpdir-local repair log may remain for operator debugging but is never committed to run logs.

### UPDATED: python/pr_body.py

- **`generate_code_flow_diagram`**: on non-zero subprocess exit, keep optional tmpdir-local repair artifact for operator use only; write via `design_diagram_log.write_bounded_diagram_failure_log` (bounded/stripped sidecar) instead of piping raw generator stdout/stderr (which may contain partial Mermaid) into a committed-path artifact.
- Returned `reason` remains bounded (`generation-failed rc=<N> tail=<capped-redacted-tail>`); no Mermaid in durable surfaces.

### UPDATED: python/cli.py

- Wire `design_diagram_log` helpers if a thin CLI surface is needed for shell fences; otherwise import from `design_diagram_log.py` inside sanitize wrapper via `python3 …/cli.py` subcommand only if agent-lint requires it.

### UPDATED: python/test_design_diagram_log.py

- Assert `strip_diagram_sections` removes `## Architecture Diagram`, `## Code Flow Diagram`, and mermaid fences while preserving non-diagram error text.
- Assert bounded sidecar contains no fence tokens.

### UPDATED: python/test_step_7a.py

- **`test_step7a_diagram_failure_exits_zero_and_clears_stale_artifacts`**: assert `larch-logs/implement/run-1/code-flow-diagram.failure.log` is **absent** (no copy into committed run-log tree).
- Assert bounded warning still lands in `execution-issues.md` with `reason` / `rc=` tail; `DIAGRAM_REASON` KV still emitted.
- Optional: assert tmpdir-local bounded failure sidecar may exist when `pr_body` writes one, but it stays under `$IMPLEMENT_TMPDIR` root only.

### UPDATED: python/test_pr_body.py

- Update diagram-failure fixtures to expect bounded failure sidecar (no raw mermaid in append payload) when failure-log path is exercised.

### UPDATED: python/test_design_pause.py

- After Step 3b finalize and before Step 4: resume → Step 4.
- After Step 5b and before `step-5b.5`: resume → `5b.5`.
- After `step-5b.5` and before Step 5c: resume → `5c`.
- Paused before Gate C (e.g. after Step 4, before 5b): must not resume into diagram step.

### UPDATED: python/test_design_lifecycle.py

- Extend `test_step5c_core_requires_step5b_sentinel` pattern with `test_step5c_core_requires_step5b5_sentinel`: `step-5b` present, `step-5b.5` absent → rc `1` and repair breadcrumb.
- Update `_setup_step5c_design` and all Step 5c success-path fixtures to write `.completed/step-5b.5`.

### UPDATED: python/test_design_publish.py

- Update all publish fixtures to include `.completed/step-5b.5`.
- Add `test_publish_main_requires_step5b5_sentinel`: `step-5b` present, `step-5b.5` absent → rc `5`, no plan write.
- Add `test_publish_clears_architecture_on_skipped_marker_after_sanitizer_rejection`: `architecture-diagram.skipped` touched by sanitizer fail-closed path → `--clear-architecture`.
- Add `test_publish_does_not_clear_when_step5b5_complete_without_diagram_or_skip_marker`: sentinel present, no `architecture-diagram.md`, no `architecture-diagram.skipped` → **no** `--clear-architecture`, bounded warning only.
- Retain existing skip-marker / non-empty diagram upsert tests; remove any test asserting clear-on-missing-files-alone.

### UPDATED: python/test_design_log_publish_flow.py

- Assert top-level exclusions for `architecture-diagram.md`, `architecture-diagram.candidate.md`, `architecture-diagram.skipped`, `architecture-diagram-generation.failure.log`, and `architecture-diagram-sanitizer.failure.log`.
- Assert curated nested copies of kept artifacts (if any test fixtures use them) still publish when not top-level.

### UPDATED: skills/implement/SKILL.md

- **Verbosity control**: remove `diagrams` from the **Preserved** output bullet (alongside voting tallies, final reports, etc.). Step 7a issue upsert remains; diagram bodies are not chat output.
- **NEVER list**: add rule mirroring design: never print `$IMPLEMENT_TMPDIR/code-flow-diagram.md`, `$IMPLEMENT_TMPDIR/code-flow-section.md`, or `## Code Flow Diagram` section bodies to chat. Diagram content is issue-only via `python/cli.py diagrams upsert`.
- **NEVER list**: add rule that diagram failure captures (including `code-flow-diagram.failure.log` and any generator/sanitizer stdout containing Mermaid) must not be copied or flushed into committed `larch-logs/implement/<RUN_ID>/`; durable failure surface is bounded `execution-issues.md` warnings only.
- **Step 7a prose**: confirm helper owns upsert silently; orchestrator emits breadcrumbs/KVs only, not diagram fence content.

### UPDATED: scripts/test-design-structure.sh

- Keep classifier tests (target diagram mode entry path).
- Assert sanitizer scripts contain no `LARCH-DIAGRAM` marker strings.
- Assert sanitizer fail-closed paths touch `architecture-diagram.skipped`.
- Assert Step 5b.5 SKILL prose does not instruct full-capture `append-failure` for diagram generation or sanitizer failures.
- Assert `SKILL.md` verbosity bullet does not authorize architecture diagram chat emission.
- Assert `SKILL.md` does not instruct orchestrator to re-emit diagram bodies.
- Assert Step 2b anti-halt lines do not promise pre-approval diagram generation.
- Assert anti-halt chain includes `5b.5` between `5b` and `5c`.
- Assert Step 5b continue paths reference Step 5b.5, not direct Step 5c (except where 5b.5 is explicitly intermediate).

### UPDATED: scripts/test-implement-anti-halt.sh

- Update `/design` anti-halt pin for Step 3b finalize → Step 4 wording.
- Add pin for Step 5b.5 → Step 5c boundary after diagram completion sentinel.
- Add pin that `/implement` SKILL Preserved list excludes `diagrams` and NEVER forbids code-flow diagram chat emission.
- Add pin that `/implement` SKILL or `step_7a.py` does not copy `code-flow-diagram.failure.log` into `larch-logs/implement/`.

### UPDATED: skills/implement/scripts/test-step-7a.sh

- Verify-only assertions:
  - Successful Step 7a stdout must not contain `## Code Flow Diagram`.
  - Step 7a still calls `python/cli.py diagrams upsert` for the tracking issue.
  - Step 7a must not write a dedicated diagrams run-log batch.
  - Step 7a must not copy `code-flow-diagram.failure.log` into `larch-logs/implement/<RUN_ID>/`.

### MAY_UPDATE: scripts/lint-readability-preamble.tsv

- Update only if SKILL step markers or readability directive count changes after relocating diagram prompt text to Step 5b.5.

### MAY_UPDATE: docs/run-logs.md

- Update only if wording implies architecture diagram is generated before Gate C.
- Document that top-level diagram body artifacts and diagram-generation/sanitizer failure captures are excluded from committed design logs; implement `code-flow-diagram*.md`, `code-flow-section.md`, and `code-flow-diagram.failure.log` are not committed under `larch-logs/implement/<RUN_ID>/`; destination for diagram content remains issue-scoped `larch:diagrams`.

## Edge cases

- `DIAGRAM_REQUIRED=false` after approval still writes `architecture-diagram.skipped` so Step 5c clears stale issue diagram content.
- Gate C **Discuss further** / **Re-run review panel** must not generate or regenerate diagrams.
- Diagram generation or sanitizer failure after approval must not block OOS filing (already complete), plan write, rename, final summary, or cleanup; sanitizer fail-closed paths must still write `architecture-diagram.skipped` and `.completed/step-5b.5`.
- Diagram generation/sanitizer failure logs must not publish partial Mermaid to committed design or implement run logs even when full capture is retained locally for repair.
- Sanitizer rejection deletes candidate and accepted diagram file; skip marker ensures publish clears stale Architecture content.
- Lost `architecture-diagram.md` after successful sanitization but before publish (tmpdir corruption) must **not** trigger `--clear-architecture`; publish skips diagram upsert with bounded warning only.
- Implement Step 7a diagram failure: bounded `execution-issues.md` warning is the durable diagnostic; no `code-flow-diagram.failure.log` copy under `larch-logs/implement/<RUN_ID>/` even when tmpdir-local repair log exists.
- Paused run after Step 5b resumes at Step 5b.5, not Step 5c.
- Paused run before Gate C must not resume into diagram generation.
- Direct `design step5c` / `design publish` invocation without `step-5b.5` fails closed with repair breadcrumb; no `[DESIGNED]` rename.
- If post-approval diagram wrapper exits before writing `step-5b.5`, preserve tmpdir and surface error; do not enter Step 5c without sentinel unless an explicit fail-closed degrade path documents otherwise.

## Failure modes

- Post-approval entry/sanitize wrapper failure before sentinel: preserve `$DESIGN_TMPDIR`, surface wrapper error, block Step 5c until operator resume/repair.
- Generation failure before candidate: warning to `execution-issues.md` with bounded token only (optional raw capture in excluded local log), sanitize fail-closed writes `architecture-diagram.skipped`, writes `step-5b.5`, continue to Step 5c with architecture clear via skip marker.
- Sanitizer rejection: skip marker written, publish clears architecture; bounded sidecar only in execution-issues append; no diagram upsert of rejected content; sanitizer failure log excluded from committed design logs.
- Implement generation failure: bounded execution-issues warning only; no run-log copy of `code-flow-diagram.failure.log`; Step 7a remains non-fatal.
- Missing `step-5b.5` at publish: fail-closed rc `1`/`5`; operator must complete or repair Step 5b.5.
- Missing diagram file without skip marker at publish: no architecture clear; bounded warning; plan publish continues.
- Step 5c upsert failure: keep existing non-blocking warning behavior.

## Testing strategy

- Run `make lint`.
- Run `make py-lint`.
- Run `make py-test`.
- Run targeted tests first:
  - `bash scripts/test-design-structure.sh`
  - `bash scripts/test-implement-anti-halt.sh`
  - `bash skills/implement/scripts/test-step-7a.sh`
  - `python3 -m pytest python/test_design_diagram_log.py python/test_design_pause.py python/test_design_publish.py python/test_design_lifecycle.py python/test_design_log_publish_flow.py python/test_step_7a.py python/test_pr_body.py`

## Acceptance

- `/design` generates the architecture diagram only after Gate C **Approve** (new Step 5b.5, between Step 5b and Step 5c). It is never generated before Gate C; **Discuss further** / **Re-run review panel** loops do not generate it.
- `/design` no longer emits the diagram body to chat: `design-step3b-sanitize.sh` prints no `---LARCH-DIAGRAM-*---` markers, and `SKILL.md` carries no re-emit instruction.
- The architecture diagram still lands in the tracking-issue `larch:diagrams` comment via Step 5c. `DIAGRAM_REQUIRED=false` writes `architecture-diagram.skipped` and Step 5c clears stale Architecture content.
- Diagram body artifacts and diagram-generation/sanitizer failure captures are excluded from committed design run logs; `/implement` no longer copies `code-flow-diagram.failure.log` into `larch-logs/implement/<RUN_ID>/`.
- `/implement` diagram routing is unchanged: still upserted to the tracking issue and embedded in the PR body; never printed to chat.
- Step 5c and `design publish` fail closed when `.completed/step-5b.5` is absent (parallel to the existing `step-5b` guard); publish `--clear-architecture` fires only when `architecture-diagram.skipped` exists.
- Pause/resume reaches Step 5b.5 between Step 5b and Step 5c; a pause before Gate C never resumes into diagram generation.
- `make lint`, `make py-lint`, and `make py-test` pass, including the new `python/test_design_diagram_log.py` and the updated structure, anti-halt, step-7a, pause, publish, and log-publish harnesses.

diff_lines: 675

## Test plan
(no test plan section in plan-file)
