### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:849-909
- **Concern**: Centralized terminal and step5c publish helpers omit RECOVERY_BRANCH handling that clarify adds. Scenario: log_publish_main can exit 0 with PUBLISH_OK=true and a non-empty RECOVERY_BRANCH when recovery work is needed. Clarify will treat that as failure, but _publish_terminal_final_summary only checks return code and PUBLISH_OK, so cancelled terminal outcomes and step5c failed-publish-tail can still mark completion and upsert while logs are incomplete.
- **Proposed resolution**: In _publish_terminal_final_summary (and any shared wrapper), parse RECOVERY_BRANCH from captured stdout the same way as PUBLISH_OK. Treat any non-empty RECOVERY_BRANCH as publish failure even when PUBLISH_OK=true. Propagate that through step_final_summary_core and step5c failed-publish-tail before disk upsert or sentinel writes.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/clarify.py
- **Concern**: The disk-upsert helper is pinned to clarify.py but reused from design_terminal.py and design_step5c.py. Scenario: clarify already imports design_lifecycle, which imports design_terminal. Putting the shared helper in clarify.py and importing it from design_terminal creates clarify -> design_lifecycle -> design_terminal -> clarify.
- **Proposed resolution**: Place a neutral helper such as upsert_final_summary_from_disk in design_summary.py next to the existing tracking-issue upsert block (~628-638). Have clarify.py, design_terminal.py, and design_step5c.py import it from there.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:849-909
- **Concern**: Terminal centralized publish does not fail closed on disk-upsert failure. Scenario: The clarify section requires returning PUBLISH_OK=false when upsert fails after a clean log publish. The terminal section only says to fail when centralized publish fails, then unconditionally runs disk upsert, marker emit, and .completed/step-final-summary on publish success. A failed upsert can leave the fence complete without an updated larch:final-summary comment.
- **Proposed resolution**: After centralized log publish succeeds, require the disk-upsert helper to return true before _emit_final_summary_marked_from_disk, sidecar emit, or sentinel touch. On upsert failure, append an execution issue, return non-zero, and skip completion. Apply the same success contract in step5c failed-publish-tail (centralized attempt fails if upsert fails; only then fall back to local render).

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_log_publish_flow.py:470-484
- **Concern**: Dry-run render can still perform failure-report GitHub writes. Scenario: The planned dry-run call to _render_final_summary_before_copy uses the post-publish render path. For failed outcomes with terminal state, render_final_summary_main runs the failure-report gate, which can invoke gh-backed filing even though dry-run must keep real git/gh side effects disabled.
- **Proposed resolution**: Wrap the dry-run render with the stall-recovery dry-run env or use a render path that still writes final-summary.md but skips failure-report filing and other GitHub-capable post-publish work.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/clarify.py:1274-1280
- **Concern**: Clarify happy-path publish rows still hardcode CLARIFY_PUBLISH_STATUS=ok. Scenario: The plan updates _publish_clarify_log_and_summary to fail on RECOVERY_BRANCH or disk-upsert failure, but _handle_design_clarify_publish always emits CLARIFY_PUBLISH_STATUS=ok in its final rows block. After a successful log publish with failed upsert or recovery, PUBLISH_OK=false and rename is skipped, yet CLARIFY_PUBLISH_STATUS stays ok. That repeats the stale-success contract the issue targets.
- **Proposed resolution**: Gate the success rows on publish_ok and parsed publish stdout: emit CLARIFY_PUBLISH_STATUS=ok only when publish_ok is true and RECOVERY_BRANCH is empty; otherwise emit summary-upsert-failed or log-publish-recovery and keep PUBLISH_OK=false.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/clarify.py / python/larch/design/design_terminal.py
- **Concern**: The shared disk-upsert helper is planned in clarify.py but reused from design_terminal.py. Scenario: The plan puts _upsert_clarify_final_summary_from_disk in clarify.py and has design_terminal.py and design_step5c.py call it. clarify already imports design_lifecycle, which imports design_terminal at import time. A design_terminal to clarify import closes a cycle and can fail module load or force fragile lazy imports.
- **Proposed resolution**: Place the shared disk-upsert helper in design_summary.py (or design_terminal.py) and import it from clarify.py, design_terminal.py, and design_step5c.py. Do not import clarify from design_terminal.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: architecture
- **Location**: python/larch/design/clarify.py
- **Concern**: python/larch/design/design_terminal.py. Scenario: python/larch/design/design_step5c.py
- **Proposed resolution**: Disk-upsert helper is planned only in clarify.py but reused from design_terminal.py and design_step5c.py clarify.py already imports design_lifecycle, which imports design_terminal and design_step5c. Top-level imports of the clarify helper from those modules create a circular import at module load. Place the shared disk-upsert helper in a neutral module such as design_summary.py (alongside existing upsert logic) or design_core.py, and import it from clarify, design_terminal, and design_step5c.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py
- **Concern**: Centralized terminal publish omits RECOVERY_BRANCH failure signaling. Scenario: _publish_terminal_final_summary is specified to treat success as rc 0 plus PUBLISH_OK=true only. log_publish_main can exit 0 with PUBLISH_OK=true and a non-empty RECOVERY_BRANCH when push or PR creation leaves a recovery branch. Terminal cancelled outcomes could mark .completed/step-final-summary and emit chat markers while logs are incomplete, repeating the clarify recovery gap the plan fixes elsewhere.
- **Proposed resolution**: Parse RECOVERY_BRANCH from centralized publish stdout in design_terminal.py and design_step5c.py, treat any non-empty value as publish failure, and apply the same gate in tests for terminal and failed-publish-tail paths.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:849-909
- **Concern**: Terminal centralized path does not fail closed when disk upsert fails. Scenario: After a successful log publish, step_final_summary_core is planned to call the disk-upsert helper then emit markers and touch .completed/step-final-summary. The contract only hard-fails on centralized publish failure, not upsert failure. A committed log PR with a missing or stale larch:final-summary comment matches the issue's primary failure mode.
- **Proposed resolution**: Require disk upsert to return success before _emit_final_summary_marked_from_disk, report-gate sidecars, or completion sentinel writes; return non-zero and skip completion on upsert failure.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:875-908
- **Concern**: cancelled-clarify and failed-clarify still re-render in the Final summary block. Scenario: The plan fixes clarify to upsert from design_tmpdir/final-summary.md after log publish, but explicitly keeps cancelled-clarify and all failed-* outcomes on the unchanged render_final_summary_main path in step_final_summary_core. That path still runs a full render and default tracking-comment upsert after clarify already published and upserted, which can drift the GitHub comment away from the committed log summary or hide a failed second upsert.
- **Proposed resolution**: For cancelled-clarify and failed-clarify, when a non-empty final-summary.md already exists after clarify publish, skip render_final_summary_main and only run _emit_final_summary_marked_from_disk plus _emit_report_gate_sidecars_from_disk from disk. ## Findings ### 1. architecture — Shared upsert helper placement (blocking) The plan puts `_upsert_clarify_final_summary_from_disk` in `clarify.py` and tells `design_terminal.py` and `design_step5c.py` to reuse it. That creates a load-time cycle: `clarify` → `design_lifecycle` → `design_terminal` / `design_step5c` → `clarify`. Move the helper to a neutral module (`design_summary.py` is the natural home; upsert logic already lives at ```628:638:python/larch/design/design_summary.py```). ### 2. correctness — `RECOVERY_BRANCH` missing on centralized paths (important) Clarify publish is planned to treat non-empty `RECOVERY_BRANCH` as failure. `_publish_terminal_final_summary` and the `step5c_core` `failed-publish-tail` retry only check `PUBLISH_OK`. `log_publish_main` can emit both `PUBLISH_OK=true` and `RECOVERY_BRANCH` when recovery is needed (```530:535:python/larch/design/design_log_publish_flow.py```). Apply the same `RECOVERY_BRANCH` gate on terminal and step5c centralized publish paths. ### 3. correctness — Terminal upsert failure not gated (important) The plan fails closed when centralized publish fails, but not when the follow-up disk upsert fails. That leaves room for a committed log PR with a stale or missing tracking comment, which is the core issue this work targets. Gate completion sentinel and marker emission on upsert success, same as clarify's planned `PUBLISH_OK=false` on upsert failure. ### 4. correctness — `cancelled-clarify` / `failed-clarify` double-render (important) The plan avoids a second `design log-publish` for `cancelled-clarify`, but still runs unchanged `render_final_summary_main` in `step_final_summary_core` (```875:908:python/larch/design/design_terminal.py```). That path re-renders and upserts by default after clarify already published and upserted from disk. The stale-comment risk moves from clarify's follow-up to the Final summary block without fixing the root cause for those outcomes. For outcomes clarify already published (`cancelled-clarify`, `failed-clarify`), emit markers from the existing `final-summary.md` instead of re-rendering. --- **Prior-round notes:** FINDING_1–5 and the double-publish scope reductions appear addressed in the current plan. FINDING_2 (dry-run) and FINDING_5 (step5c `failed-publish-tail`) look complete. The gaps above are new or residual relative to those fixes.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:91
- **Concern**: `design_step5c.py` uses a nonstandard plan heading, so the required failed-publish-tail fix may be missed by plan tooling. Scenario: The issue-wire parser recognizes only `### NEW:`, `### UPDATED:`, `### REWRITTEN:`, and `### MAY_UPDATE:` headings. `### NEW behavior in:` does not create a firm file contract for the live failed-publish-tail source.
- **Proposed resolution**: Change the heading to `### UPDATED: python/larch/design/design_step5c.py` while keeping the existing body.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/clarify.py:841-917
- **Concern**: The shared disk-upsert helper is scoped to clarify.py but terminal and step5c also need it.. Scenario: The plan tells `design_terminal.py` and `design_step5c.py` to call the helper defined in `clarify.py`. `clarify` already imports `design_lifecycle`, which imports `design_terminal` at import time. A `design_terminal` import of `clarify` creates a circular import and can fail at module load.
- **Proposed resolution**: Define one shared `_upsert_final_summary_from_disk(...)` in `design_summary.py` (or `design_core.py`) and call it from clarify, terminal, and step5c. Do not make `design_terminal` import `clarify`.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:849-909
- **Concern**: The terminal and step5c centralized paths do not gate success on disk-upsert failure.. Scenario: Clarify publish will return `PUBLISH_OK=false` when the post-log-publish upsert fails. The terminal plan only fails on centralized `log_publish_main` failure and still emits readiness markers and `.completed/step-final-summary` after calling the upsert helper. Step5c treats centralized publish success as done before upsert. A successful log publish with a failed tracking upsert can still finish with a stale or missing `larch:final-summary` comment.
- **Proposed resolution**: Treat disk-upsert failure like clarify: return non-zero, keep `PUBLISH_OK=false`, skip `.completed/step-final-summary`, and on the step5c `failed-publish-tail` path fall back to `_step5c_render_final_summary` when upsert fails after centralized publish succeeds.
