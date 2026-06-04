### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: SessionStart sparse probe does not mechanically isolate lib-sparse-dirs
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: important
- **Concern**: The sparse-cone probe sources `lib-sparse-dirs.sh` in the parent shell before calling `append_msg` with a fixed literal. A tampered or buggy library (or future edit) could redefine `append_msg`, assign `MSG` at top level, or run code inside `normalize_sparse_dirs`, allowing attacker-controlled text into SessionStart context despite the call site appearing safe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Isolate allowlist loading (subshell or helper that prints the normalized list on stdout only), or snapshot/restore `append_msg`/`MSG` around a minimal source block; add a harness fixture lib that defines a hostile `append_msg` and assert the emitted `additionalContext` stays exactly the fixed sparse-drift string.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: LARCH_RESTART_REQUIRED=true emitted twice in one branch combination
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: When `MARKETPLACE_CONE_WILL_RECONCILE=true` and `LATEST_STABLE=""`, `LARCH_RESTART_REQUIRED=true` is emitted twice (cone-reconcile branch and unconditional `LATEST_STABLE=""` block). Harmless for substring-match callers today but obscures intent and could confuse future deduplicating consumers; no production test covers this combination.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: In the `LATEST_STABLE=""` block, guard with `if [ "$MARKETPLACE_CONE_WILL_RECONCILE" != true ]` or hoist `LARCH_RESTART_REQUIRED=true` to a single emission point.
  - From cursor-specialist-testing-output.txt: Guard the `[ -z "$LATEST_STABLE" ]` block at line 529 with `[ "$MARKETPLACE_CONE_WILL_RECONCILE" != true ]` (or an equivalent single-emission flag) so `LARCH_RESTART_REQUIRED=true` is emitted exactly once per run.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: RESOLVED_ROOT= parsing corrupts paths containing =
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `release-step7.env` writes `RESOLVED_ROOT=<path>` and Step 8 reads with `awk -F=`, truncating at embedded `=` characters in filesystem paths (e.g. `/Users/a=b/...`). Diagnostic corruption only—Step 8 does not use `RESOLVED_ROOT` for control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Either strip `RESOLVED_ROOT` from the state file (it is not consumed in Step 8), or use a delimiter that cannot appear in a filesystem path (`|`, `\t`) or write/read it as the last field taking the rest of the line with `awk -F= 'NR==FNR && $1=="RESOLVED_ROOT"{print substr($0, index($0,"=")+1); exit}'`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Harness inline source permanently overrides upgrade-larch function namespace
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: `resolve_release_step7_root_for_test` sources `release-step7-root.sh` inline, overriding helper definitions in the harness process. Test ordering is now load-bearing; a future case calling root resolution between unit tests and `source_upgrade_for_case` could silently use the wrong `is_cache_shaped_larch_root` implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Run `resolve_release_step7_root` in a subprocess (`bash -c "source ...; resolve_release_step7_root ..."`) rather than sourcing into the harness namespace, or add an explicit `source_upgrade_for_case` guard after the root-resolution block to restore `upgrade-larch.sh` function definitions before proceeding.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: gh stubs in production tests do not validate subcommand shape
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: All `gh` stubs match any arguments and print `v9.0.0`; a refactor from `gh api` to `gh release list` would still pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Add a minimal argument check inside each `gh` stub: `case "$1 $2" in "api "*)` to verify the `api` subcommand is reached, and `exit 1` on mismatch, so a command-shape regression is caught.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: probe_sparse_cone_drift duplicates shell-opt restore on each early return
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `probe_sparse_cone_drift` restores `set -e`/`set -u` with identical blocks before each of three early `return 0` paths. A future early-exit path that omits restore could leave errexit/nounset disabled for the rest of the hook.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Move the restore into a `trap ... RETURN` set at function entry, or extract a single helper function (`restore_shell_opts`) called by all exit paths.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Sparse cone compare logic duplicated between SessionStart and upgrade-larch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Sparse cone comparison logic is duplicated between `sessionstart-health.sh` and `upgrade-larch.sh`. Allowlist normalization changes may require two edits to keep warnings and reconciliation aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a shared compare helper to lib-sparse-dirs.sh


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Test helpers duplicate release Step 7/8 flag parsing from SKILL.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-upgrade-larch-retention.sh` duplicates release Step 7/8 flag parsing and state-file logic from `release/SKILL.md`. Future release prompt edits can pass harness tests while diverging from actual orchestrator behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared helpers into release-step7-root.sh or a small release-step7-state module


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

