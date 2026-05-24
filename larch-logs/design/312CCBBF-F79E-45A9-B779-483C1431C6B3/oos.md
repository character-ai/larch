### OOS_1: [docs/linting.md and scripts/token-report.md] — operator-facing docs still describe the OLD cost-line contract
- **Reviewers**: Cursor-Arch, Cursor-Edge, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Description**: `docs/linting.md:272-279` lists the `test-token-report-summary-format` row describing it as pinning the dollar-primary `--summary` one-liner. `scripts/token-report.md:7-18` and `scripts/token-cost.md:3-6` similarly describe the old contract. After this PR these become stale. Affected file paths: `docs/linting.md`, `scripts/token-report.md`, `scripts/token-cost.md`.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [skills/implement/scripts/write-final-report.md] — outcome enumeration becomes stale
- **Reviewers**: Cursor-Plan-Pragmatic
- **Description**: Sibling doc at `skills/implement/scripts/write-final-report.md:5-36` still states Outcome bullets only fire for `bailed*` and `stalled`. After `render-run-summary.sh` extends the outcome pattern to `cancelled-*|failed-*`, the doc drifts. Affected file paths: `skills/implement/scripts/write-final-report.md`.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [docs/run-logs.md] — narrative still implies /implement-only sentinel semantics
- **Reviewers**: Cursor-Innovation
- **Description**: `docs/run-logs.md:182-214` describes outcome and sentinel semantics in /implement-only terms. After /design shares `larch:final-summary`, the doc should be updated to acknowledge both skills. Affected file paths: `docs/run-logs.md`.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [skills/shared/topology.tsv] — potential missing projection rows for new design scripts
- **Reviewers**: Cursor-Innovation
- **Description**: If repo topology policy treats new `skills/design/scripts/*.sh` as projection authorities, `skills/shared/topology.tsv` may need new rows when the scripts land to avoid doc-sync drift. Affected file paths: `skills/shared/topology.tsv`.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_5: [scripts/refresh-run-logs.sh and lib-larch-log.sh] — confirmation audit for committed batch dollar-line emission
- **Reviewers**: Cursor-Plan-Requirements
- **Description**: This PR's plan says committed `token-report.md` log batches must not duplicate the dollar line. `scripts/refresh-run-logs.sh:74-80` uses `--full --format json` (not markdown), so the audit is likely a no-op. A one-line confirmation in a follow-up issue (or a regression assertion) would close traceability. Affected file paths: `scripts/refresh-run-logs.sh`, `scripts/lib-larch-log.sh`.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

