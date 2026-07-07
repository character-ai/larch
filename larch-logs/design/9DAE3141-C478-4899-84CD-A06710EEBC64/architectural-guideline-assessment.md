## Architectural guideline deviation assessment (Gate C, #6527)

### G-Fix-1 / DRY (mild): parallel firm-heading/surface parsers
- Plan adds `_firm_heading_count`, `_plan_surface`, `_plan_surfaces` in plan_quality.py and separate scope-path matching in prepare_partition_issues, rather than reusing `issue_wire.extract_scope_paths(..., include_optional=False)`.
- Reviewer FINDING_5 raised this as a [SCOPE-REDUCTION] drift risk vs /implement coverage diagnostics; the coder considered and rejected it in favor of a self-contained detector.
- Severity: mild. Deliberate, reviewer-considered choice; not blocking. Follow-up could unify on extract_scope_paths if drift appears.

### Otherwise aligns
- G-Cfg-1: new PLAN_SIZE_* thresholds and OVERSIZE_OVERRIDE_OPERATOR added as Final constants in config.py; detector references them.
- G-Wire-1 / G-Wire-2: `oversize_override: operator` is a multi-consumer grammar change; plan updates every consumer (publish, step5c, difficulty, bootstrap, preflight, plan_review_common, decompose) and keeps readers tolerant of plans without the trailer.
- G-Py-4: fail-closed Step 5c finalization guard (return 4 on size-check non-zero / missing PLAN_SIZE_STATUS / SIZE_TRIGGER_FIRED=true).
- G-Idem-1: set_oversize_override_main is idempotent and symlink/CRLF-safe.
