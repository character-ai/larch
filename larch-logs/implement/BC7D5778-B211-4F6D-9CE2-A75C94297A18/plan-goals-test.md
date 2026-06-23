## Goal
Implement issue #5160: [IMPLEMENTING] [DEDUP] centralize the repeated final-summary marker-extraction instruction (design SKILL.md).

## Implementation Plan
## Plan

## Approach

- Add `skills/shared/final-summary-emit.md` as the single source for the common final-summary emit procedure.
- Define two profiles in the shared reference:
  - **Marker-first profile** (default): extract markers from the caller-named completed background task's `<task-notification>` stdout already in the orchestrator context window, then Read fallback, then optional sidecars.
  - **File-only profile**: Read non-empty `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` only; no marker pass; no `REPORT_GATE_SIDECARS_FILE` follow-on unless a caller names a sidecar source outside this profile.
- Keep only site-specific glue in `skills/design/SKILL.md`:
  - which profile and completed task output to use (when applicable)
  - when to emit: cancel route, Final summary block, Step 5c abort, Step 5c item 5
  - after-action: terminate, stop immediately, warn, footer, or continue
- Replace full near-verbatim procedure text with pointers to the shared file.
- Repoint the Anti-halt reminder and Step 5d partial paraphrases to the same shared source.
- Repoint `scripts/test-render-cost-line-callsites.sh` (and sibling `.md`) so `make lint` pins the common contract in the shared file and only site-specific gates remain in `skills/design/SKILL.md`.
- Do not move any emit logic into Python or Bash.
- Do not change marker names, fallback path, sidecar handling, or orchestrator-text requirement.

## Files to modify/create

### NEW: skills/shared/final-summary-emit.md

Create a compact shared reference with the common contract and two profiles.

**Shared rules (both profiles):**

- Emit only the body as plain orchestrator chat markdown.
- Write the Read result directly as orchestrator text.
- Never use Bash, Python, or another tool call to extract or print the final-summary body.
- Do not paraphrase, summarize, reorder, add prose between bullets, or add prose around the block.
- Preserve the full structured block, including title, mode, duration, cost line, per-agent breakdown, tokens, and bullets.
- Note that the caller supplies the profile, task-output source (when applicable), and after-action.

**Marker-first profile (default):**

- Primary extraction: locate the first balanced whole-line `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` pair in the `<task-notification>` stdout from the named completed background task already in the orchestrator context window (for example `design-step-final-summary.sh` or `design-step5c.sh`).
- Do not re-read task-output files, stdout captures, result env files, or tmpdir logs to recover markers; do not scrape markers via Bash or Python.
- If markers are absent or invalid in that in-context notification text, use the Read tool on `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` when non-empty.
- When the completed notification stdout includes non-empty `REPORT_GATE_SIDECARS_FILE=<path>`, Read that file and emit its full body verbatim immediately after the final-summary body.

**File-only profile:**

- Skip marker extraction entirely; do not scan prior tool output for markers.
- When `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`, Read that file and emit its full body verbatim as plain chat markdown.
- No `REPORT_GATE_SIDECARS_FILE` follow-on unless a caller explicitly names a sidecar source outside this profile.

### UPDATED: skills/design/SKILL.md

Replace duplicated procedure text with concise references.

- In the Anti-halt continuation reminder:
  - Keep the no-free-form-recap rule.
  - Replace the detailed marker/fallback/tool-call prose with a pointer to `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` (marker-first profile).
  - Preserve `_publish_rc` 0, 1, or 3 and cancellation outcome scope.

- In Step 0b cancel routes (`cancel-title-filter`, `cancel-reentry-guard`):
  - Replace the inline Read-tool fallback instructions with a callout to follow the shared reference **file-only profile**.
  - Keep site-specific glue explicit:
    - no task-output source
    - no marker pass
    - no sidecars
    - emit only when `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`
    - terminate before sub-step 3 even when the summary file is empty, missing, or render failed

- In `### Final summary block`:
  - Keep all wait, background, sentinel, and outcome text unchanged unless needed for the pointer.
  - Replace the large repeated extraction paragraph with:
    - source: completed `design-step-final-summary.sh` `<task-notification>` stdout per marker-first profile in `skills/shared/final-summary-emit.md`
    - profile: marker-first per `skills/shared/final-summary-emit.md`
    - for Step 5c handoff wording, defer to the Step 5c site
  - Keep the note that Step 5c item 5 uses the same common procedure.

- In Step 5c abort path:
  - Replace the repeated extraction/fallback/sidecar prose with a pointer to the shared file (marker-first profile).
  - Keep source: completed `design-step5c.sh` `<task-notification>` stdout.
  - Keep after-action: emit sidecars before stopping, then stop immediately without Step 5c items 5-7, Step 5d, or Step 6.

- In Step 5c item 5:
  - Keep source: completed `design-step5c.sh` `<task-notification>` task output.
  - Keep timing: emit before plan-write failure warning or success footer decisions.
  - Keep `Regardless of `PLAN_WRITE_OK`` and `_publish_rc` 0, 1, or 3 behavior.
  - Keep “not gated on render-final-summary exit 0.”

- In Step 5d:
  - Replace partial paraphrases of the shared emit rule with a pointer to the shared file (marker-first profile).
  - Keep the no-free-form-recap ban.
  - Keep a compact site-specific gate phrase for post-driver emit (`_publish_rc` 0, 1, or 3) without re-stating the full marker/fallback procedure.
  - Keep warning replay and footer ordering.

### UPDATED: scripts/test-render-cost-line-callsites.sh

Retarget design full-body emit pins so CI passes after centralization.

- Add `skills/shared/final-summary-emit.md` to the design contract grep surface.
- Move common procedure pins from `skills/design/SKILL.md` to the shared file, including at minimum:
  - `emit its full body verbatim as plain chat markdown`
  - marker extraction from completed task `<task-notification>` stdout already in the orchestrator context window (`LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END`)
  - `Do NOT paraphrase, summarize, reorder, or add prose between bullets`
  - `REPORT_GATE_SIDECARS_FILE` sidecar follow-on prose
  - explicit prohibition on re-reading task-output files or Bash/Python marker scraping (Read fallback limited to `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}`)
- Keep site-specific pins in `skills/design/SKILL.md`, including:
  - `--post-publish-only`
  - `Step 5c `python/cli.py design step5c` returns with the latest `_publish_rc` 0, 1, or 3`
  - Step 0b non-empty file gate: `when `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]``
  - `Regardless of `PLAN_WRITE_OK``
  - Step 5d post-driver gate phrase (compact pointer form, not full procedure)
  - `NEVER write a free-form natural-language recap summary at end of turn`
  - pointer reference to `skills/shared/final-summary-emit.md` at each emit call site
- Add a pin that Step 0b cancel-route glue names the file-only profile (or equivalent explicit no-marker language).
- Add a negative check that the full marker-extraction procedure does not reappear verbatim in `skills/design/SKILL.md` outside compact pointers.

### UPDATED: scripts/test-render-cost-line-callsites.md

Sync the harness description to document:

- common emit contract pins live in `skills/shared/final-summary-emit.md`
- site-specific gates and pointers remain in `skills/design/SKILL.md`
- Step 0b cancel routes use the file-only profile
- marker-first profile pins in-context `<task-notification>` extraction and forbids task-output re-reads

## Edge cases

- Do not make the shared file imply it can select the completed task output or profile. Each call site must name both.
- Do not make the shared file imply a single after-action. Each call site must keep its stop, continue, footer, or warning behavior.
- Step 0b cancel routes (`cancel-title-filter`, `cancel-reentry-guard`) use the **file-only profile** only: no task-output source, no marker pass, no sidecars; Read fallback applies only when the summary file is non-empty.
- Marker-first call sites must name their completed background task (`design-step-final-summary.sh` or `design-step5c.sh`) and extract markers only from that task's `<task-notification>` stdout already in context; do not scan unrelated prior tool output or re-open task-output files.
- Preserve the Read fallback only for non-empty fallback files.
- Preserve sidecar emit ordering immediately after the final-summary body on marker-first paths.
- Do not introduce a second canonical procedure in `skills/design/SKILL.md` while trying to explain the pointer.

## Failure modes

- If the lint harness is not repointed, `make lint` fails even when behavior is correct because removed strings are still asserted in `skills/design/SKILL.md`.
- If a call site loses its task-output source, the orchestrator may extract markers from the wrong background result.
- If marker-first extraction omits the in-context `<task-notification>` rule, an implementer may re-read task-output files or use Bash/Python to scrape markers, violating the no-tool-call contract and risking missed or wrong-source extraction.
- If Step 0b is pointed at the marker-first profile, cancel routes may scan unrelated prior tool output before the file fallback, changing behavior versus today's line 271.
- If the shared reference omits the orchestrator-text rule, an implementer may incorrectly pipe the body through Bash or Python.
- If Step 5c item 5 loses its “before warning/footer” placement, final output ordering can change.
- If the Anti-halt reminder keeps a near-complete copy, acceptance fails because the instruction still appears more than once.

## Testing strategy

- Run `grep -n "LARCH_FINAL_SUMMARY_BEGIN\\|REPORT_GATE_SIDECARS_FILE\\|task-notification\\|final-summary body\\|Do NOT paraphrase" skills/design/SKILL.md skills/shared/final-summary-emit.md` and verify:
  - the full procedure exists only in `skills/shared/final-summary-emit.md`
  - `skills/design/SKILL.md` contains only compact pointers plus site-specific glue
- Run `grep -n "design-step5c.sh\\|design-step-final-summary.sh\\|file-only\\|task-notification" skills/design/SKILL.md skills/shared/final-summary-emit.md` and verify each emit site still names the correct profile and source.
- Run `scripts/test-render-cost-line-callsites.sh` (via `make lint`) and confirm shared-file pins (including in-context notification extraction and no task-output re-read) plus remaining design SKILL site-specific gates pass.
- Run `make lint`.
- No `make py-lint` or `make py-test` is required unless implementation unexpectedly changes Python.

## Acceptance

- The common final-summary emit procedure (marker extraction, Read fallback, verbatim no-paraphrase emit, never-via-Bash/Python-tool-call, `REPORT_GATE_SIDECARS_FILE` follow-on) lives once in `skills/shared/final-summary-emit.md`, with a marker-first profile and a file-only profile.
- Every final-summary emit site in `skills/design/SKILL.md` (Anti-halt reminder, Step 0b cancel routes, Final summary block, Step 5c abort path, Step 5c item 5, Step 5d) points to the shared file and keeps only its site-specific source, profile, and after-action glue inline.
- The full marker-extraction procedure does not reappear verbatim in `skills/design/SKILL.md` outside compact pointers.
- Step 0b cancel routes use the file-only profile: no marker pass, no sidecars, emit only when the summary file is non-empty.
- `scripts/test-render-cost-line-callsites.sh` and its sibling `.md` are retargeted so common pins assert against the shared file and only site-specific gates remain pinned in `skills/design/SKILL.md`; `make lint` passes.
- No behavioral change: each emit site keeps its exact source, after-action, and the plain-orchestrator-text emit rule.

diff_added: 105
diff_deleted: 55
mechanical_churn: false
diff_lines: 160

## Test plan
(no test plan section in plan-file)
