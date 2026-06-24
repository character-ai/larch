## Decision 1: Scope of Part 1 (OOS skip breadcrumb)
- **Question**: Does OOS_SKIP_BREADCRUMB cover all skip-* statuses, including skip-already-filed-sentinel (which also runs annotate)?
- **Resolution**: Yes. All skip-* statuses get NEXT_ACTION=skip-pipeline and OOS_SKIP_BREADCRUMB=... The skip-already-filed-sentinel annotate path is controlled by the existing STEP5B_NEEDS_ANNOTATE=true key, not by NEXT_ACTION. The orchestrator re-emits the breadcrumb, then checks STEP5B_NEEDS_ANNOTATE for annotate routing.
- **Source**: codebase

## Decision 2: Settle NEXT_ACTION emission site
- **Question**: Should SETTLE_NEXT_ACTION be emitted from design-step35-settle.sh (Bash) or from design step2b-postplan (Python)?
- **Resolution**: Emit from design-step35-settle.sh. The settle wrapper already knows both POSTPLAN_MACHINE_RC and SITE, so the (rc, site) → action mapping is a natural addition there. The Python callee does not know the site, so having the callee emit a fully site-keyed value would require passing --site through, adding complexity to postplan. The Bash addition is minimal (one printf per exit arm).
- **Source**: codebase
