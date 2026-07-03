# design-step5c.sh

## Purpose

Thin wrapper for the `/design` Step 5c Python entrypoint.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Delegates directly to `python/cli.py design step5c` after deriving and exporting `CLAUDE_PLUGIN_ROOT` when needed.
- The Python entrypoint owns source-env rehydration, pause-save handling, publish-tail orchestration, and all Step 5c status artifacts.
- The Python entrypoint writes `$DESIGN_TMPDIR/.bg-wait-active` after publish preconditions and pause-save checks, copies `CLONE_PATH` from `.larch-keepalive` when available, then removes it on exit so hook enforcement covers publish/result parsing.
- It accepts `--session-env-path`, `--claude-pid`, `--plugin-root`, `--mode`, and `--skip-validate` from the prompt-side launcher.
- It calls the publish tail in-process through `design_publish.publish_core`, while `python/cli.py design publish` remains the legacy/internal publish-tail verb.
- It parses publish rc `0` from `.design-publish-result.env` first with stdout fallback.
- It forces stdout authority for rc `1`, `3`, and `4` by using a guaranteed-absent primary result env. This prevents stale primary success data from masking current plan-write failures, result-env write failures, or validator defects.
- It stages rc `2` and unexpected non-zero exits as `failed-publish-tail`, renders the failed-publish-tail summary, emits marked summary output, emits sidecar handoff, writes status, and returns failure.
- It captures `render-final-summary` stdout to `render-final-summary.*.stdout.log` before disk-based marker emission, so unmarked render text does not leak to the Step 5c contract stream.
- It emits non-empty `final-summary.md` between `LARCH_FINAL_SUMMARY_BEGIN` and `LARCH_FINAL_SUMMARY_END` markers on normal publish handoff and failed publish-tail staging.
- It does not render or emit final-summary markers for rc `4`; it emits `STEP5C_STATUS=validator-defects` and `REPORT_GATE_SIDECARS_FILE=` when sidecars exist.
- It emits `REPORT_GATE_SIDECARS_FILE=` after marked summary output on success and abort paths, and without markers on rc `4`.
- It writes `.completed/step-5c` only when `PLAN_WRITE_OK=true`.
- It writes `.completed/step-5c-terminal` in a `finally` path after `DESIGN_TMPDIR` is known, including publish-tail abort paths.
- It writes `.design-step5c-status.env` with publish rc, stdout-fallback, cleanup eligibility, and publish/plan status.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step5c.sh`, and `python/test_design_lifecycle.py`.
