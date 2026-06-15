# Review Round 1

- Mode: `diff`
- 4 accepted, 14 rejected (1 neutral)

## Accepted Findings

### FINDING_1: correctness: scripts/rebase-checkpoint-probe.sh:95-104
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] _resolve_trivial_conflict_file falls back to git rm on any checkout --ours failure Transient checkout failure on an existing larch-logs conflict can be mis-resolved as deletion instead of surfacing conflict Narrow rm fallback to true upstream-delete cases or return 1 on unexpected checkout failure
- **Suggested revision**: Address the concern above.


### FINDING_24: **correctness** `scripts/rebase-checkpoint-probe.sh:95-104` — `_resolve_trivial_conflict_file` treats any `git checkout --ours` failure as “upstream deleted the file” and immediately runs `git rm -f`. Checkout can fail for other reasons (transient git errors, index corruption, permission problems, or a path that is not a normal modify/modify conflict). In those cases the fallback can stage a deletion of a `larch-logs/*` file that should have been kept from upstream, leaving the rebase in a worse state than surfacing the conflict. `ship-pr.sh` marks checkout failures as unresolved instead of deleting. **Suggested fix:** On checkout failure, inspect unmerged stages (`git ls-files -u` / `git-conflict-files.sh`) and only run `git rm -f` when stage 2 (upstream/base) is absent; otherwise return failure and let the loop re-derive `CONFLICT_FILES` from `git diff --name-only --diff-filter=U`, matching the resolve-failure path at lines 231-234.
- **Reviewer**: dyn-rebase-state-output.txt
- **Concern**: - **correctness** `scripts/rebase-checkpoint-probe.sh:95-104` — `_resolve_trivial_conflict_file` treats any `git checkout --ours` failure as “upstream deleted the file” and immediately runs `git rm -f`. Checkout can fail for other reasons (transient git errors, index corruption, permission problems, or a path that is not a normal modify/modify conflict). In those cases the fallback can stage a deletion of a `larch-logs/*` file that should have been kept from upstream, leaving the rebase in a worse state than surfacing the conflict. `ship-pr.sh` marks checkout failures as unresolved instead of deleting. **Suggested fix:** On checkout failure, inspect unmerged stages (`git ls-files -u` / `git-conflict-files.sh`) and only run `git rm -f` when stage 2 (upstream/base) is absent; otherwise return failure and let the loop re-derive `CONFLICT_FILES` from `git diff --name-only --diff-filter=U`, matching the resolve-failure path at lines 231-234.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: python/agents.py:3536-3552
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Unclassified-empty bonus retry increments auth_attempt and consumes explicit auth retry budget. With LARCH_EXTERNAL_AUTH_RETRIES=2, an empty exit-1 first attempt sets auth_attempt to 2, then a second auth-classified failure does not retry because auth_attempt < max_auth is false. Track unclassified bonus retries separately from auth-budget state, or increment only a telemetry counter that does not drive the auth retry gate.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/rebase-checkpoint-probe.sh:95-104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Any git checkout --ours failure triggers git rm -f as upstream-deletion handling. Checkout failure from permissions or index issues causes git rm on a conflicted larch-log file; rebase may continue with wrong or missing run-log state. Detect true upstream deletion before git rm; return 1 without rm on other checkout failures.
- **Suggested revision**: Address the concern above.


