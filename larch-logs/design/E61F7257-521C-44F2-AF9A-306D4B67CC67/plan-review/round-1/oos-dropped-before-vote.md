### OOS_3: LiveRunHealth dataclass may be over-engineered
- **Description**: LiveRunHealth dataclass may be over-engineered. Scenario: Statusline gating needs only whether a candidate has live registry evidence; state/reason/source fields add API surface without a consumer
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/report/_progress_report_live.py
- **Phase**: design

