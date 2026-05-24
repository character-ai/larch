### OOS_1: [docs/linting.md and scripts/token-report.md] — operator-facing docs still describe the OLD cost-line contract
- **Reviewers**: Cursor-Arch, Cursor-Edge, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Description**: `docs/linting.md:272-279` lists the `test-token-report-summary-format` row describing it as pinning the dollar-primary `--summary` one-liner. `scripts/token-report.md:7-18` and `scripts/token-cost.md:3-6` similarly describe the old contract. After this PR these become stale. Affected file paths: `docs/linting.md`, `scripts/token-report.md`, `scripts/token-cost.md`.
- **Filed URL**: https://github.com/character-ai/larch/issues/2726
### OOS_2: [skills/implement/scripts/write-final-report.md] — outcome enumeration becomes stale
- **Reviewers**: Cursor-Plan-Pragmatic
- **Description**: Sibling doc at `skills/implement/scripts/write-final-report.md:5-36` still states Outcome bullets only fire for `bailed*` and `stalled`. After `render-run-summary.sh` extends the outcome pattern to `cancelled-*|failed-*`, the doc drifts. Affected file paths: `skills/implement/scripts/write-final-report.md`.
- **Filed URL**: https://github.com/character-ai/larch/issues/2727
### OOS_3: [docs/run-logs.md] — narrative still implies /implement-only sentinel semantics
- **Reviewers**: Cursor-Innovation
- **Description**: `docs/run-logs.md:182-214` describes outcome and sentinel semantics in /implement-only terms. After /design shares `larch:final-summary`, the doc should be updated to acknowledge both skills. Affected file paths: `docs/run-logs.md`.
- **Filed URL**: https://github.com/character-ai/larch/issues/2728
