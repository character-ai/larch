### OOS_1: Offline larch-log.sh stub defaults unknown batch paths to `.json`
- **Description**: `scripts/test-larch-logs-batches.sh` (or related offline harnesses) may have stub code that maps unknown batch slugs to `.json` extensions. Adding `final-bail-reason .txt` would expose this latent default behavior if the harness ever runs with the slug absent from the table.
- **Reviewers**: Cursor-dyn-batch-registration
- **Severity**: latent


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### OOS_2: Archived design text references "five vendor attempts"
- **Description**: Some archived/superseded design text mentions five vendor attempts for `fix-attempts-exhausted` whereas the current code uses 10 (FIX_ATTEMPTS >= 10 from `ci-decide.sh`). Cleanup pass on archived docs.
- **Reviewers**: Cursor-dyn-exit-contract
- **Severity**: nit


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

### OOS_3: REFRESH_COMMITTED detection uses loose stdout heuristics
- **Description**: `larch-log.sh commit` success detection relies on stdout-heuristic parsing in callers. A more robust contract (explicit exit code or KV envelope) would harden the commit pipeline.
- **Reviewers**: Cursor-Innovation
- **Severity**: latent

Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

