### FINDING_13: risk-integration: skills/implement/scripts/test-post-tracking-issue.sh:41-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No --run-id or precedence-chain tests for post-tracking-issue.sh change. A regression in --run-id handling could ship while CI stays green; bootstrap would write wrong RUN_ID into parent-issue.md. Add harness cases for --run-id override invalid --run-id and missing RUN_ID; update test-post-tracking-issue.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] security: scripts/get-issue-state.sh:46-57
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] get-issue-state.sh does not validate --issue as numeric. Direct invocation with metacharacters in --issue could reach gh if a future caller drops quoting. Mirror post-tracking-issue numeric validation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] security: scripts/tracking-issue-read.sh:269-278
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Sentinel parser does not validate ISSUE_NUMBER or RUN_ID format. Malformed sentinel values reach new phase_tracking logic until downstream tools fail. Add newline and charset validation in tracking-issue-read sentinel branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] code-quality: scripts/implement-bootstrap.md:237
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale note claims tracking breadcrumbs are future work. Misleading operators reading contract doc only. Update breadcrumb section to list emitted tracking lines.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_31: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Removed Step 0 tracking token-ledger mark when collapsing tracking bash. Token reports may attribute Step 0 tracking work to preflight bucket only. Re-add mark inside phase_tracking or document intentional boundary shift.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] **Bash 3.2 portability (scout checklist):** The new `[[ "$UPSTREAM_REPO_OPT" =~ ... ]]` check at `scripts/implement-bootstrap.sh:603` is acceptable on the macOS Bash 3.2 target (`=~` in `[[ ]]` since 3.0; not listed in `BASH_AUTHORING.md` / `scripts/lint-bash32.sh` forbidden constructs). No Bash 4+ tokens (`declare -A`, `mapfile`, `${var,,}`, `&>>`, etc.) appear in the new/changed bodies of `scripts/implement-bootstrap.sh`, `scripts/write-session-env.sh`, or `skills/implement/scripts/post-tracking-issue.sh`.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **Bash 3.2 portability (scout checklist):** The new `[[ "$UPSTREAM_REPO_OPT" =~ ... ]]` check at `scripts/implement-bootstrap.sh:603` is acceptable on the macOS Bash 3.2 target (`=~` in `[[ ]]` since 3.0; not listed in `BASH_AUTHORING.md` / `scripts/lint-bash32.sh` forbidden constructs). No Bash 4+ tokens (`declare -A`, `mapfile`, `${var,,}`, `&>>`, etc.) appear in the new/changed bodies of `scripts/implement-bootstrap.sh`, `scripts/write-session-env.sh`, or `skills/implement/scripts/post-tracking-issue.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] **`run_larch_log_init` temp hygiene:** `init_err` from `mktemp` is removed on both failure (159) and success (163) paths before `tracking_init_failed` / `return`; `rename_to_implementing` uses a fixed `$IMPLEMENT_TMPDIR/tracking-rename.stderr.log` path (no `mktemp` leak despite plan prose mentioning a temp rename log).
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **`run_larch_log_init` temp hygiene:** `init_err` from `mktemp` is removed on both failure (159) and success (163) paths before `tracking_init_failed` / `return`; `rename_to_implementing` uses a fixed `$IMPLEMENT_TMPDIR/tracking-rename.stderr.log` path (no `mktemp` leak despite plan prose mentioning a temp rename log).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] **Exit-code capture:** `init_rc=$?` immediately follows the `init_out=$(... 2>"$init_err")` assignment with no intervening commands; stdout and stderr are not mixed in that call (stderr goes to `init_err` only).
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **Exit-code capture:** `init_rc=$?` immediately follows the `init_out=$(... 2>"$init_err")` assignment with no intervening commands; stdout and stderr are not mixed in that call (stderr goes to `init_err` only).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_40: [OUT_OF_SCOPE] **Pre-existing patterns in the same files:** `phase_infra` already uses the same `mktemp` + `rm -f` pattern for `gate_err` (203–226) without checking `mktemp` success; `write-session-env.sh` already uses multiple `[[ =~ ]]` validators unchanged by this branch’s `--forked-target` addition.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **Pre-existing patterns in the same files:** `phase_infra` already uses the same `mktemp` + `rm -f` pattern for `gate_err` (203–226) without checking `mktemp` success; `write-session-env.sh` already uses multiple `[[ =~ ]]` validators unchanged by this branch’s `--forked-target` addition.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_43: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-kv-protocol-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:336-353` — Exit-2 handling in the bootstrap Bash block still only special-cases `session-entry-gate`, `session-setup`, and `get-issue-state`; `scripts/implement-bootstrap.sh` can also exit 2 with `STEP_FAILED=create-branch` or `STEP_FAILED=write-session-env` (`198-199`, `318-319`). That predates the tracking phase and is unchanged by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_44: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-kv-protocol-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:30` — Load-bearing invariant #4 still describes `deferred=true` in prose while the wire protocol exports uppercase `DEFERRED`; the bootstrap behavior map uses `DEFERRED=true`. Harmless if the orchestrator uses parsed `DEFERRED`, but the mixed naming predates this branch’s table work.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] architecture: docs/linting.md:238
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] test-implement-bootstrap doc still says calls 1-5 only. Operators misread harness coverage after Phase 2. Update linting.md when touching docs (not in this PR file list).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

