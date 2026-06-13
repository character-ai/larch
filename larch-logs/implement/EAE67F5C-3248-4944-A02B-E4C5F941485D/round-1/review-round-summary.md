# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_5: `clear-stall` skips dangling symlink layers (`-e` before `-L`)
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-stall-state-auditor-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/stall-recovery-report.sh:251-267` gates preflight/write loops on `[ -e "$path" ]`, so dangling symlinks (`-L` true, `-e` false) are skipped. The old single-file `clear-stall` failed closed on dangling `ship-pr-state.sh` via `ship_pr_state_is_dangling_symlink`; that guard was removed. A recovery path with `finalize-state.sh` pointing at a missing target and stale `ship-pr-state.sh` can emit `CLEARED=true` after clearing only `ship-pr-state.sh`, leaving untrusted layer paths behind. If the only state artifact is a dangling symlink, `present` stays false or those layers are ignored and the command can emit `CLEARED=true` without clearing stall keys, letting Step 18a.5 treat recovery as successful when durable stall state still exists off-path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Check -L before the -e skip and add dangling symlink tests for each durable layer.
  - From codex-specialist-edge-cases-output.txt: Reject -L paths before the -e skip for every durable layer
  - From dyn-stall-state-auditor-output.txt: Treat dangling symlinks like regular symlinks: fail preflight with `CLEARED=false` and exit 3 (reuse `ship_pr_state_is_dangling_symlink` or `[ -L "$path" ] && [ ! -e "$path" ]` for each layer), and do not emit `CLEARED=true` when any expected layer path is a dangling symlink.


### FINDING_6: `ci-wait` trap publishes `ACTION=wait` with non-empty `BAIL_REASON`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-ci-token-parity-output.txt
- **Severity**: important
- **Concern**: `scripts/ci-wait.sh:249-255` backfills `BAIL_REASON=ci-wait-unexpected-exit` on the normal `ACTION=wait` path, violating the header contract (`scripts/ci-wait.sh:44`) that `BAIL_REASON` must be empty unless `ACTION=bail`. After at least one wait iteration, a trap-delivered exit (SIGTERM mid-poll; `scripts/test-ci-wait-exit-trap.sh` sub-test A) publishes `ACTION=wait` with a non-empty bail token, so `ship-pr`'s `ACTION=bail` classifier does not run. Shell/Python interrupt parity is broken for file-mode CI wait: `python/ci.py:223-246` publishes `ACTION=bail` on the same class of mid-poll interrupt because `poll_ci` has not returned yet. Consumers that key off `ACTION` (not only `BAIL_REASON`) can treat the same failure differently on the bash ship path vs the Python `ci wait --output-file` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: On trap-delivered non-zero exits set ACTION=bail with the unexpected-exit token, or keep BAIL_REASON empty for ACTION=wait; assert both fields in tests.
  - From dyn-ci-token-parity-output.txt: Drop the wait-path backfill. Keep `BAIL_REASON` empty for non-`bail` actions. On abnormal trap exit during the wait loop, coerce `ACTION=bail` and `BAIL_REASON=ci-wait-unexpected-exit` before `emit_output`, matching the Python trap defaults.
  - From dyn-ci-token-parity-output.txt: In the EXIT trap (or immediately before `emit_output` on non-zero trap exit), if the script is terminating abnormally while `ACTION=wait`, rewrite to `ACTION=bail` with `BAIL_REASON=ci-wait-unexpected-exit`. Add an assertion in sub-test A for `ACTION=bail` on the SIGTERM path.


