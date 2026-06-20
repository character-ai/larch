## Decision 1: Scope — consolidate the publish tail into the Step 5c entrypoint
- **Question**: Port the `design-step5c.sh` wrapper only, or also fold `design_publish.py`'s publish tail into the new Step 5c entrypoint?
- **Resolution**: Consolidate. Port the `design-step5c.sh` orchestration into a new `step5c` entrypoint in `python/design_lifecycle.py` AND run the publish tail in-process (collapse the subprocess hop to `design publish`). The larger change is accepted; the already-ported, tested publish module may be re-touched. `design-step5c.sh` becomes a thin delegation wrapper.
- **Source**: user

## Decision 2 (hard constraint): Preserve the orchestrator stdout / marker / sentinel contract
- **Question**: What must not break in the port?
- **Resolution**: The new Python entrypoint MUST preserve the exact contract the `SKILL.md` orchestrator parses: machine rows (`PUBLISH_RC`, `PLAN_WRITE_OK`, `PUBLISH_OK`, `VALIDATE_*`, `FINAL_SUMMARY_PATH`, `UPSERT_STATUS`, `ARCHITECTURE_SOURCE`, `CLEANUP_ELIGIBLE`, `STEP5C_STATUS`), the `LARCH_FINAL_SUMMARY_BEGIN`/`END` body emission, `REPORT_GATE_SIDECARS_FILE=` emission, sentinels (`.completed/step-5c` gated on `PLAN_WRITE_OK=true`; `.completed/step-5c-terminal` always), `.design-step5c-status.env`, and all publish exit-code semantics (0/1/3/4 continue; 2 and unexpected non-zero → abort + stage `failed-publish-tail`). The immediate-background `.bg-wait-active` marker (`STEP=design-step5c`) must be created on entry and removed on every exit via try/finally, mirroring `step_final_summary_core`. Preconditions (`.completed/step-5b` gate) and `.pause-requested` pause-save exec must be preserved.
- **Source**: codebase (`design-step5c.sh`, `SKILL.md` Step 5c, `python/design_lifecycle.py` `step_final_summary_main`)

## Decision 3 (hard constraint): Preserve `review_provenance` and publish wire format for downstream consumers
- **Question**: Does folding `design_publish.py` break other consumers?
- **Resolution**: `python/design_summary.py:14` imports `review_provenance` from `design_publish`; it must stay importable. The publish-tail behavior and wire format (provenance splicing, secret redaction, `named-block write --marker plan`, diagrams upsert, `[DESIGNED]` rename, `log-publish`, secret-scrub rotation warning) must be preserved exactly. Any relocation of `design_publish.py` must keep `review_provenance` importable and update `python/checks.py:466` (direct-target pairing) and the `cli.py` allowlist accordingly. `test_design_publish.py` coverage (14 tests) must be preserved — migrated or retained.
- **Source**: codebase (`design_summary.py:14`, `python/checks.py:466`, `python/test_design_publish.py`)
