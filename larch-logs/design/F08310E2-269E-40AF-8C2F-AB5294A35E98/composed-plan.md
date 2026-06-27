## Plan

## Approach

- Keep the change narrow.
- Move the sanitizer’s mechanical promote, skip, warning, and `.completed/step-5b.5` write into the Step 5c Python path.
- Keep `design-step3b-entry.sh --mode diagram` unchanged.
- Keep `python/cli.py mermaid sanitize` unchanged.
- Remove prompt-side dead fallback routing for missing `NEXT_ACTION`.
- Preserve fail-closed behavior for unknown OOS status and Step 5 ordering.

## Files to modify/create

### UPDATED: python/design_publish.py

- Add `_sanitize_diagram_candidate(...)`.
- Port the current `design-step3b-sanitize.sh` behavior:
  - If `architecture-diagram.candidate.md` is missing or unreadable:
    - remove stale accepted and candidate files,
    - write `architecture-diagram.skipped`,
    - write `architecture-diagram-sanitizer.failure.log`,
    - append a bounded `Warnings` entry,
    - touch `.completed/step-5b.5`,
    - return success.
  - If `python/cli.py mermaid sanitize --input <candidate> --from-md --warnings-step 5b.5` succeeds and does not emit `STATUS=rejected`:
    - remove stale skip and failure artifacts,
    - promote candidate to `architecture-diagram.md`,
    - touch `.completed/step-5b.5`.
  - If sanitizer rejects or exits non-zero:
    - parse `REASON_TOKEN`,
    - remove accepted and candidate files,
    - write `architecture-diagram.skipped`,
    - write a bounded failure log,
    - append a bounded `Warnings` entry,
    - touch `.completed/step-5b.5`.
- Replace the `publish_core` `.completed/step-5b.5` hard precondition with this helper.
- Keep the `.completed/step-5b` precondition.
- Do not emit diagram bodies to stdout or logs.
- Prefer `design_diagram_log` and `run_logs.append_execution_issue` over shelling out to `run-log append-failure`.

### UPDATED: python/larch/design/design_lifecycle.py

- Remove the early `step5c_core` refusal on missing `.completed/step-5b.5`.
- Keep the `.completed/step-5b` refusal before publish.
- Let the in-process publish preamble perform sanitizer completion.
- Ensure pause-save still runs before sanitizer work.
- Keep `_bg_wait_marker_context` around publish plus sanitizer so Step 5c completion and WARN replay stay in the existing background flow.
- In `_step5b_emit_prepare_success`, compare any upstream `NEXT_ACTION=` from prepare stdout with the status-derived action.
- If upstream `NEXT_ACTION` exists and disagrees:
  - emit `STEP5B_STATUS=unknown-oos-status`,
  - emit `NEXT_ACTION=unknown-oos-status`,
  - write the same values to `oos-filing-prepare.env`,
  - return the existing unknown-status rc path.

### UPDATED: skills/design/SKILL.md

- In the wrapper inventory, remove `design-step3b-sanitize.sh` and its prompt doc as primary Step 5 surfaces.
- In Step 5b, remove the mandatory read of `oos-step5b-dispatch.md`.
- Replace the “derive on missing `NEXT_ACTION`” fallback prose with “parse `NEXT_ACTION`; missing, unknown, or `unknown-oos-status` stops for repair.”
- In Step 5b.5, remove the standalone `design-step3b-sanitize.sh` fence.
- State that diagram-required runs write a candidate, then Step 5c sanitizes, promotes, or skips it.
- Update the Step 5 invariant to say Step 5c completes the Step 5b.5 sanitize gate before publish.
- Replace the `_publish_rc` abort wall with a one-line pointer to `finalize-step5.md`.
- Keep the final-summary binding block and Step 5d footer rules intact.

### UPDATED: skills/design/references/finalize-step5.md

- Update the Ordering contract:
  - Step 5b prepare emits `NEXT_ACTION`.
  - Step 5c owns diagram sanitize completion before publish.
  - `readability-style.md` is read once at Step 5 entry before diagram or final plan prose composition.
- Remove the fallback-table dependency.
- Move the `_publish_rc=2`, `_publish_rc=3`, `_publish_rc=5`, and unexpected non-zero abort guidance from `SKILL.md`.
- Keep the existing `_publish_rc=4` validator-defect guidance.
- Keep `PLAN_WRITE_OK` success and failure branches as the source of truth.
- Update diagram prose so sanitizer rejection warnings are replayed through the Step 5c warning path, not a separate Step 5b.5 fence.

### REWRITTEN: skills/design/references/oos-step5b-dispatch.md

- Replace the fallback table with a short legacy note.
- State that current `python/cli.py design step5b-prepare` must emit `NEXT_ACTION`.
- State that missing `NEXT_ACTION` or disagreement with `FILE_DESIGN_OOS_STATUS` is a repair stop.
- Keep enough detail for historical context, but do not require prompt-side derivation.

### UPDATED: skills/design/scripts/design-step3b-sanitize.md

- Change “Primary callers” from `skills/design/SKILL.md` to legacy/manual compatibility, if the wrapper stays.
- State that Step 5c Python now owns normal sanitizer execution.
- Keep invariants that remain true for the script.
- Do not describe it as the primary happy-path sanitizer.

### MAY_UPDATE: skills/design/scripts/design-step3b-sanitize.sh

- Leave the wrapper in place unless tests or script inventory require retirement.
- If touched, keep behavior byte-compatible or convert it to a thin call into the new Python helper.
- Do not add new Bash logic.

### UPDATED: scripts/test-design-structure.sh

- Remove pins that require the Step 5b OOS dispatch mandatory read.
- Remove pins that require the standalone Step 5b.5 sanitizer fence.
- Add pins that require:
  - Step 5c owns sanitize before publish,
  - `SKILL.md` points rare `_publish_rc` handling to `finalize-step5.md`,
  - `finalize-step5.md` contains the `_publish_rc=2/3/5` abort guidance,
  - `oos-step5b-dispatch.md` is no longer mandatory-read from `SKILL.md`,
  - `readability-style.md` is not required twice in Step 5.
- Update `EXPECTED_OLD` / `EXPECTED_NEW` if this harness pins old/new Step 5 fence shape.

### UPDATED: python/test_design_publish.py

- Replace `test_publish_main_requires_step5b5_sentinel`.
- Add coverage for publish-time sanitizer behavior:
  - valid candidate is promoted and upsert uses `architecture-diagram.md`,
  - missing candidate writes skip marker and clears architecture,
  - sanitizer rejection writes skip marker, logs a bounded warning, and clears architecture,
  - no diagram content appears in stdout or `execution-issues.md`.
- Keep existing publish-tail result-env and architecture upsert tests passing.

### UPDATED: python/test_design_lifecycle.py

- Update Step 5c tests that currently require pre-existing `.completed/step-5b.5`.
- Add a test proving `step5c_core` can proceed when Step 5b is complete, Step 5b.5 is absent, and publish-time sanitizer creates the Step 5b.5 sentinel.
- Keep tests that require `.completed/step-5b`.
- Keep pause-save tests proving sanitizer and publish do not run after pause.

### UPDATED: python/test_design_oos.py

- Add coverage for an upstream prepare stdout disagreement:
  - `FILE_DESIGN_OOS_STATUS=ready`,
  - upstream `NEXT_ACTION=skip-pipeline`,
  - wrapper emits `NEXT_ACTION=unknown-oos-status`,
  - wrapper returns the existing repair-stop rc.
- Keep current ready, skip, already-filed, unknown, and prepare-failure tests.

## Edge cases

- Missing candidate after `DIAGRAM_REQUIRED=true` must not block publish.
- Sanitizer rejection must not block publish.
- Sanitizer output may contain unsafe diagram content. Store only bounded redacted diagnostics.
- Existing accepted diagram must be removed on rejection or missing candidate.
- Existing issue diagram must only be cleared when `architecture-diagram.skipped` exists.
- Pause request before Step 5c must still pause before sanitizer or publish.
- Direct `python/cli.py design publish` should still sanitize or skip before publish when Step 5b is complete.

## Failure modes

- If the sanitizer helper raises unexpectedly, fail closed by writing `architecture-diagram.skipped`, appending a bounded warning, touching `.completed/step-5b.5`, and continuing unless the filesystem operation itself fails.
- If writing `.completed/step-5b.5` fails, publish should fail with the existing publish-tail failure path.
- If OOS prepare emits a malformed or disagreeing envelope, stop before Step 5b.5.
- If result-env parsing fails after `_publish_rc=3`, keep the relocated stdout fallback guidance from `finalize-step5.md`.

## Testing strategy

- Run `bash scripts/test-design-structure.sh`.
- Run `bash skills/design/scripts/test-design-step5c.sh`.
- Run `python3 -m pytest python/test_design_publish.py python/test_design_lifecycle.py python/test_design_oos.py`.
- If structure pins expose related CLI-port drift, also run `python3 -m pytest python/test_design_cli_ports.py`.
- Run `make test-design-structure` if available in the local Makefile.

## Acceptance

- Run `bash scripts/test-design-structure.sh`.
- Run `bash skills/design/scripts/test-design-step5c.sh`.
- Run `python3 -m pytest python/test_design_publish.py python/test_design_lifecycle.py python/test_design_oos.py`.
- If structure pins expose related CLI-port drift, also run `python3 -m pytest python/test_design_cli_ports.py`.
- Run `make test-design-structure` if available in the local Makefile.

review_status: panel-failed
rounds_completed: 1
diff_added: 220
diff_deleted: 170
mechanical_churn: false
diff_lines: 390
