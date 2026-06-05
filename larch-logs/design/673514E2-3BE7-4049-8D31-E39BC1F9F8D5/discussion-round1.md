## Decision 1: What moves into design-route.sh (route fence thinning)

- **Question**: Which inline route-consumption logic moves into the driver?
- **Resolution**: Move cancel-* summary rendering (the `render-final-summary.sh --post-publish-only` invocations for `cancel-title-filter` and `cancel-reentry-guard`), the reentry-guard message composition (MARKER_REMAINING math + the "refusing spurious re-entry" banner), and the resume env-refresh (`write-design-current-env.sh` call in the `resume@*` branch) into `design-route.sh`. The driver emits a single STATUS + exit code; the SKILL.md route fence collapses to capture → emit driver output → branch only into the genuinely-LLM routes (proceed/tier, clarify loop, already-planned AskUserQuestion, resume continuation).
- **Source**: issue body + user (Step 1c)

## Decision 2: Init failure banners (init fence thinning)

- **Question**: Should the init consumption fence's two failure banners (contract-drift, env-refresh-failed) also move into design-init-runparams.sh?
- **Resolution**: Yes — move both into `design-init-runparams.sh`. The driver prints the contract-drift / env-refresh-failed operator messages itself; the orchestrator fence reduces to capture → surface STATUS+exit → propagate. Symmetric with the route cancel-banner ownership; maximal thinning.
- **Source**: user (Step 1c, "Move into the driver")

## Decision 3: Banner text fidelity

- **Question**: Must relocated cancel/reentry/resume banner strings and the "🔓 resumed from STEP=" line stay byte-identical?
- **Resolution**: Equivalent rewording is permitted while relocating. The driver may tidy wording/format of the moved banners; exact byte-identity is NOT required. Functional behavior (routing outcomes, exit codes, which artifacts are written) must still be preserved.
- **Source**: user (Step 1c, "Allow equivalent rewording")

## Decision 4: Test/verification strategy

- **Question**: How is behavior-preservation guaranteed in tests?
- **Resolution**: Reframe existing pins only — update `test-design-structure.sh` FINDING_2-family structural pins and `scripts/test-step0b-router-flag-recovery.sh` to assert the thin shape and driver ownership. Do NOT add new dedicated driver harness files. Done-bar = those harnesses + `make lint` green.
- **Source**: user (Step 1c, "Reframe existing pins only") + issue acceptance

## Decision 5: Out-of-scope / non-goals (hard constraints)

- **Question**: What must NOT change?
- **Resolution**:
  - Do NOT change the clarify-loop logic (sub-step 3), the already-planned AskUserQuestion (sub-step 4), or the resume-continuation routing — they remain LLM routes in the thinned fence.
  - Do NOT change the `ROUTE` verdict set (proceed/clarify/already-planned/cancel-title-filter/cancel-reentry-guard/cancel-pause-load/resume@<STEP>) or driver exit-code contract (0 routing, 1 result-env refusal, 2 config error).
  - Do NOT change run-params.json schema or tier mapping.
  - Preserve the FINDING_2 thin-fence primitives that STAY in SKILL.md: `_route_out=` / `_init_out=` captures, `.design-route-result.env` / `.design-init-runparams-result.env` file-first reads, and the "must not call phase_driver_read_result_env" invariant.
  - Preserve Check 24 ordering: `cancel-title-filter` and `cancel-reentry-guard` case tokens must still appear in SKILL.md Step 0b before the Clarify loop (their branch *bodies* shrink; the labels remain).
  - Preserve exit-2 / operational-failure abort prose that the orchestrator still owns (FINDING_3, FINDING_9 generic exit-code aborts).
  - The brainstorm-prefix info banner stays orchestrator-side (it mutates the mental `brainstorm_requested` flag; not a cancel route).
- **Source**: codebase (test-design-structure.sh pins) + issue scope

## Decision 6: Behavior preservation surface

- **Question**: Which runtime behaviors must be byte/semantically preserved?
- **Resolution**: All seven routing outcomes and their side effects: proceed (tier→run-params), clarify (plan write + publish + label/rename), already-planned (3-option prompt), cancel-title-filter (summary + lifecycle/archival banner + exit 1), cancel-reentry-guard (summary + reentry banner + exit 1), cancel-pause-load (banner + exit 1), resume@<STEP> (env-refresh + "resumed" line + jump to step). The orchestrator must still emit final-summary.md verbatim at top chat on cancel routes that render a summary.
- **Source**: codebase + issue ("cancel/resume/clarify paths behavior-preserved")

## Note: design-route.sh gains a `--session-id` input

- Moving `render-final-summary.sh` into the driver for cancel routes requires the driver to have SESSION_ID (currently only the orchestrator holds it pre-resume). The plan adds `--session-id` to design-route.sh argv. (Implementation detail; confirmed via codebase, not a user decision.)
