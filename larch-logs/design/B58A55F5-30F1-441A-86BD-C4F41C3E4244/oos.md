### OOS_1: [OUT_OF_SCOPE] `_render_inflight_gantt` still calls `_progress_vendor_rows` without `require_complete_status=False`, so live inflight charts can keep hiding non-complete phase2/phase3 fallbacks even after the phase-detail fix.
- **Description**: [OUT_OF_SCOPE] `_render_inflight_gantt` still calls `_progress_vendor_rows` without `require_complete_status=False`, so live inflight charts can keep hiding non-complete phase2/phase3 fallbacks even after the phase-detail fix.. Scenario: Operators watching an in-flight Step 5 round may still not see phase2 fallback timing until the final summary, which was not part of the C9457B68 final-summary repro.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:1121
- **Phase**: design

Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

