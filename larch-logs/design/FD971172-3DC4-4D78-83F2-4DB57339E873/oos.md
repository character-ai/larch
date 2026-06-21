### OOS_1: [OUT_OF_SCOPE] After porting parity into file_oos.py oos_filer could call file_conflict_deps_main in-process instead of spawning python/cli.py oos file-conflict-deps
- **Description**: [OUT_OF_SCOPE] After porting parity into file_oos.py oos_filer could call file_conflict_deps_main in-process instead of spawning python/cli.py oos file-conflict-deps. Scenario: Issue scope and Step 9a.1 contract require the producer to exercise the same CLI exit-code and atomic-output cleanup path as oos-pipeline.md; in-process calls bypass that boundary
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/oos_filer.py:788-794
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

