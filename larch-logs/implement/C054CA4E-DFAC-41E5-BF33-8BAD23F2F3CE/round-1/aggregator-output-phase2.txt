Normalized aggregator output from the supplied reviewer findings:

### FINDING_1: Step 0b route handoff duplicates WARN/ERROR breadcrumbs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 0b route handoff in `skills/design/SKILL.md` prints WARN/ERROR during the file-loop stdout merge and again from `_route_warn_lines` / `_route_error_lines` (and related pre-ROUTE re-emit loops). The same tokens can appear multiple times in chat (e.g. pause-load fallthrough with one WARN → up to 3–4×). Collect or dedupe before emitting once, or print only in merge branches OR only in final array loops—not both.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Duplicated scalar/repo validators across design drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_plain_scalar` and `validate_repo` are duplicated in `design-route.sh` and `design-init-runparams.sh`; future `--repo` rule changes require two edits and risk drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Init driver jq/run-params warnings bypass quiet contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: In `design-init-runparams.sh`, jq-unavailable and missing run-params paths use `printf` instead of `emit` / `emit_kv WARN` after `larch_quiet_init`. Warnings may not reach FD3, `_init_out`, or the orchestrator (e.g. `/design` with `--partition` / `--brainstorm` / `--manual` and no jq: merge skipped, flags may not persist, no operator-visible **⚠ 0b:** banner).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Duplicated large Step 3–shaped handoff fences in SKILL.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Dual large Step 3–shaped handoff fences (~120 lines) in `skills/design/SKILL.md` (Step 3 vs Step 0b route/init); Step 3 tweaks may not mirror Step 0b fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Re-entry helper exit 2 stdout not surfaced as WARN
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Re-entry helper exit 2 stdout is no longer surfaced as WARN in `design-route.sh`. Unset `HOME` or invalid-input paths can continue design without the old Step 2.6 `MARKER_HIT=false REASON=invalid-input` breadcrumb.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Branch mixes unrelated hunks beyond Step 0b
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Branch mixes #3245 with version bump, lint-literal-counts, and plan-review-loop poll defaults; reviewers must filter unrelated hunks when judging Step 0b only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Clarify sub-step re-resolves REPO redundantly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Clarify sub-step 3.2 still re-resolves `REPO` after sub-step 2’s single resolve, adding an extra `gh`/resolve-repo call on the clarify path only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Re-entry guard mis-parses space-separated KV output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-route.sh` parses `design_reentry_marker_hit` output line-by-line, but the helper emits one space-separated KV line per `lib-design-reentry-guard.md`. Second `/design` within TTL on same issue+PPID can leave `_marker_hit` as `"true MARKER_AGE=N MARKER_TTL=M"`, so cancel-reentry-guard never fires and the run proceeds to clarify/already-planned/proceed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Structure test missing operational driver abort banner greps
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` omits plan-required greps for operational driver abort banners. Removing SKILL.md `_route_rc -ne 0` / `_init_rc` not-in-{0,1} abort blocks while leaving exit-2 strings could pass CI and allow empty `ROUTE` or silent gate skip. Harness only pins exit-2 configuration errors, not **design-route.sh failed** / **design-init-runparams.sh failed** abort prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: `plan_block_present` logic untested beyond marker strings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `plan_block_present` in `design-route.sh` is untested beyond `MARK_START`/`MARK_END` presence; malformed bodies could mis-route already-planned vs proceed; `test-plan-block.sh` does not cover the driver copy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: No hermetic Step 0b orchestrator-fence harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No hermetic Step 0b orchestrator-fence harness (unlike `test-step3-orchestrator-fence.sh`); fence regressions (file-only WARN/ERROR, exit guards) can ship without offline reproduction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Structure checks no longer pin driver predicate ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Checks 20/24 no longer pin driver-internal title/reentry/verdict ordering; predicate reorder inside `design-route.sh` (e.g. archival before lifecycle) would not fail structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Router-flag jq recovery harness diverges from driver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-step0b-router-flag-recovery.sh` duplicates driver logic; append-tool-failure path not executed, so driver jq-failure logging could break while recovery harness and filter grep still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Tier/jq-warning pins weakened to SKILL OR driver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Tier/jq-warning pins weakened to SKILL OR driver; both copies could drift together with CI still green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Route/init drivers write result env without tmpdir validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` writes `.design-route-result.env` without `larch_design_tmpdir_validate` on paths that skip `design-pause-load.sh`. A buggy `--design-tmpdir` outside `~/.cache/larch/sessions`, `$TMPDIR`, or `/tmp` could write route result files to an unintended writable directory before any validating child runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Init driver exit 1 / env-refresh failure mishandled vs contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-design-current-env.sh` failure exits 1 without `INIT_STATUS=contract-drift`; orchestrator only aborts init on contract-drift, so env refresh failures (`_init_rc=1`, empty `INIT_STATUS`) let `/design` continue without refreshed source-env/issue binding. Exit code 1 is documented only for contract drift in `design-init-runparams.md` but used for other failures; SKILL treats `rc=1` as non-fatal unless contract-drift, misleading harness/reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: `design-pause-load` errors masked (stderr / `|| true`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: In `design-route.sh`, `design-pause-load.sh` is invoked with `2>/dev/null || true`, masking hard failures and stderr-only pause-load/`gh` failures. Empty/crash output can route fresh proceed without ERROR; operator loses pause corruption signal while fallthrough still proceeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: `LOAD_OK=true` without `STEP` allows partial resume fallthrough
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `LOAD_OK=true` without `STEP` falls through with partial resume KVs in final emit; corrupt pause stdout can yield proceed/clarify plus stale `SESSION_ID`, so clarify publish targets the wrong run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Init bash fence not gated on `ROUTE=proceed`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Init bash fence in `skills/design/SKILL.md` is not gated on `ROUTE=proceed` (prose-only guard). Orchestrator can run `design-init-runparams` on clarify/already-planned, renaming issue and writing run-params on the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

**Merge notes (brief):** 27 raw slots → **19** aggregated findings. Merged groups: duplicate WARN/ERROR (1/10/23/26), jq/`printf` quiet contract (3/9/24), structure-test abort greps (11/25), init exit-1/env-refresh contract (18/19), pause-load masking (20/27). Kept separate: re-entry WARN breadcrumb (5) vs KV parse bug (8); all `[OUT_OF_SCOPE]` items (6/7) retain the tag. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).
