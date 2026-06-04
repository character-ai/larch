### [Plan Review] FINDING_4

### FINDING_4: Pre-Invoke phantom-probe lead-in still names only ship-pr.sh
- **Reviewer(s)**: Cursor-dyn-selector-routing
- **Severity**: latent
- **Concern**: The lead-in immediately before the Invoke fence still says the next foreground call is `ship-pr.sh`. With Python as default, that wording can imply the wrong driver even though the selector should choose `python/ship.py` unless `LARCH_SHIP_PR_IMPL=bash`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-selector-routing: Reword line 957 to a driver-neutral lead-in (before the Step 8+ foreground driver: Python per selector unless LARCH_SHIP_PR_IMPL=bash) in the same SKILL edit hunk; no change to the fenced argv block.


### [Plan Review] FINDING_5

### FINDING_5: Security-helper prose still describes Python scrub path as in-progress parity
- **Reviewer(s)**: Codex-dyn-stale-reference-sweep
- **Severity**: latent
- **Concern**: `scripts/scrub-log-secrets.md` still implies the Python ship-pr scrub path is not live. Since the default Python ship driver relies on that path, stale wording can mislead security review of run-log secret scrubbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stale-reference-sweep: Add scripts/scrub-log-secrets.md to the update list and reword this sentence to describe the default Python ship driver scrub path rather than in-progress parity


