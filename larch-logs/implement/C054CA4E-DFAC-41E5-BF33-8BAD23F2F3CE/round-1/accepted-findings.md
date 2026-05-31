### FINDING_1: Step 0b route handoff duplicates WARN/ERROR breadcrumbs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 0b route handoff in `skills/design/SKILL.md` prints WARN/ERROR during the file-loop stdout merge and again from `_route_warn_lines` / `_route_error_lines` (and related pre-ROUTE re-emit loops). The same tokens can appear multiple times in chat (e.g. pause-load fallthrough with one WARN → up to 3–4×). Collect or dedupe before emitting once, or print only in merge branches OR only in final array loops—not both.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_13: Router-flag jq recovery harness diverges from driver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-step0b-router-flag-recovery.sh` duplicates driver logic; append-tool-failure path not executed, so driver jq-failure logging could break while recovery harness and filter grep still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


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


### FINDING_3: Init driver jq/run-params warnings bypass quiet contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: In `design-init-runparams.sh`, jq-unavailable and missing run-params paths use `printf` instead of `emit` / `emit_kv WARN` after `larch_quiet_init`. Warnings may not reach FD3, `_init_out`, or the orchestrator (e.g. `/design` with `--partition` / `--brainstorm` / `--manual` and no jq: merge skipped, flags may not persist, no operator-visible **⚠ 0b:** banner).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


