### OOS_1:
- **Description**: [SCOPE-REDUCTION] Six new *_cli.py companions vs in-module CLI entrypoints. Scenario: ship.py registers main inside the domain module; report_tokens_cli.py is the exception for a large pipeline. Six thin wrappers add files and registry indirection without changing runtime behavior
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:110-117
- **Phase**: design


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### OOS_2:
- **Description**: `rebase_and_push` is ship-oriented (conflict launch, `Stalled`/`TransientNetworkError`) and is not the `rebase-push.sh` primitive the checkpoint row needs.. Scenario: Not a B1 correctness bug if the plan keeps `push rebase`/`push checkpoint-probe` as **gap**; relevant only if someone tries to satisfy those verbs by thin-wrapping `rebase_and_push`.
- **Reviewer**: Cursor-dyn-parity-map
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/rebase.py:312-397
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

