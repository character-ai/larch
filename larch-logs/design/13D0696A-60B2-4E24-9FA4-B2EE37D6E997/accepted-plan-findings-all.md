### FINDING_1: Stale Step 2b token sidecar can be re-ingested
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements, Codex-dyn-ledger-dedup
- **Severity**: important
- **Concern**: Step 2b cleanup omits the stable `.token-record` sidecar. A retry in the same `DESIGN_TMPDIR` can append a previous `codex_plan_draft` sidecar when the current launch fails before producing a fresh one, causing stale or duplicate ledger records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `step2b-drafter-status.txt.token-record` to the pre-launch cleanup list (or gate append on a launcher freshness marker / non-empty sidecar written this invocation).
  - From Codex-Innovation: Add $DESIGN_TMPDIR/step2b-drafter-status.txt.token-record to pre-run cleanup, and only append a sidecar produced by the current launch or an empty freshly-created sidecar
  - From Cursor-Pragmatic: Add `"$DESIGN_TMPDIR/step2b-drafter-status.txt.token-record"` to the preflight `rm -f` list (or guard ingestion with a one-shot sentinel after successful append)
  - From Codex-Requirements: Add `$DESIGN_TMPDIR/step2b-drafter-status.txt.token-record` to the existing cleanup list before launch, then append only the sidecar produced by the current Codex drafter attempt
  - From Codex-dyn-ledger-dedup: Add the stable .token-record to prelaunch cleanup in launch-codex-drafter.sh or design-step2b-drafter.sh before launch, then append only the fresh stable sidecar. Add the planned drafter test case for absent sidecar at append time: no ledger row, no Step 2b failure, and no stale reappend.


### FINDING_2: Step 2b sidecar ingestion misses the active token ledger
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned `token append-record` path writes `token-report.ndjson`, but live `/design` pricing reads the active `larch-tokens-*.jsonl` ledger. Step 2b `codex_plan_draft` usage can remain absent from final token reports and cost lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend the ingestion helper or add a sidecar-to-TokenLedger path so the Step 2b sidecar writes a type=vendor ledger row as well as any batch ndjson; keep it best-effort and use the same helper at sidecar ingestion sites.
  - From Cursor-Innovation, Cursor-Requirements: In design-step2b-drafter.sh mirror scripts/lint-fix-loop.sh:393-403: parse the stable .token-record sidecar and call python3 cli.py token record-vendor codex input=... cache_read=... output=... total=... raw=codex_plan_draft (warn-not-fail). Keep append-record only if a separate run-log consumer truly needs ndjson; do not treat ndjson alone as ledger completeness for /design


### FINDING_3: Codex plan-autofix sidecar ingestion is omitted
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan audits several Codex sidecar paths but omits the `auto-fix-plan-commands.sh` `launch-codex-exec.sh` call site. Its `codex_plan_autofix` sidecar can be written but never ingested, leaving usage outside the design ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Codex-Innovation: Add best-effort exactly-once ingestion after this launcher returns, before returning parsed_exit, and update the sibling contract/test to assert codex_plan_autofix reaches the ledger.
  - From Codex-Pragmatic: Add skills/design/scripts/auto-fix-plan-commands.sh and its md sibling to the plan; after the Codex launch, best-effort append run_dir/codex.log.token-record to DESIGN_TMPDIR with token append-record, preserving warn-not-fail behavior and avoiding duplicate direct record-vendor writes
  - From Codex-Requirements: Add an UPDATED step for `skills/design/scripts/auto-fix-plan-commands.sh`; after Codex launcher return, best-effort append `${run_dir}/codex.log.token-record` to `$DESIGN_TMPDIR` with `python3 "$PLUGIN_ROOT/python/cli.py" token append-record --input ... --tmpdir "$DESIGN_TMPDIR"` when non-empty, and add a focused harness assertion


### FINDING_4: Model-basis drift test is affected by override env vars
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The drift test may compare default pricing models against `agent-model-args.sh` output that has been changed by documented override environment variables, causing false failures for users running checks with overrides set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Run the drift test under a sanitized environment that unsets those four override vars, then parse the emitted model token and compare it to DEFAULT_VENDOR_MODEL.


### FINDING_5: Drafter failure paths can drop emitted token sidecars
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-ledger-dedup
- **Severity**: important
- **Concern**: The drafter launcher can delete raw Codex output on failure paths before copying `${_codex_raw}.token-record` to the stable sidecar. Failed drafter runs may emit usage but never expose it for Step 2b ingestion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `launch-codex-drafter.sh`, immediately after `launch-codex-exec.sh` returns, copy `${_codex_raw}.token-record` to `${OUTPUT_CANON}.token-record` when non-empty on all paths (CODEX_EXEC_FAILED, CODEX_EMPTY_OUTPUT, DELIMITER_EXTRACTION_INVALID, and success) before any `rm` of `_codex_raw`
  - From Cursor-dyn-ledger-dedup: Mirror test-launch-codex-ci.sh failed-runtime token-record assertions in test-launch-codex-drafter.sh for CODEX_EXEC_FAILED with usage


### FINDING_7: Sidecar NDJSON append drops the model field
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds optional `model=` support to vendor records, but does not require `append_token_record_from_sidecar` to preserve `MODEL=` into NDJSON. The primary sidecar append path can lose the recorded model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: When `MODEL=` is present in the sidecar, include `"model": "<value>"` in the `append_token_record_from_sidecar` payload (omit when absent)


### FINDING_9: Claude blended fallback derivation is undefined
- **Reviewer(s)**: Cursor-dyn-blended-override-chain
- **Severity**: important
- **Concern**: The plan defines a 3-bucket fleet mix for blended defaults, but Claude has five pricing buckets. Without an explicit rule, implementation can unintentionally change Claude blended fallback pricing or apply the wrong formula.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-blended-override-chain: State explicitly how Claude blended is derived (exclude cache-write from mix, separate weights, or leave legacy blended unchanged) and add an acceptance check or snapshot expectation for Claude blended if it changes.


### FINDING_10: Env override ladder and legacy aliases are underspecified
- **Reviewer(s)**: Cursor-dyn-blended-override-chain, Codex-dyn-blended-override-chain
- **Severity**: important
- **Concern**: The pricing-authority refactor does not pin the current full environment override ladder, including legacy aliases and `LARCH_TOKEN_RATE_PER_M`. Existing operator overrides can be dropped, or partial overrides can fall through incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-blended-override-chain: Add an explicit plan bullet: preserve every `env_rate()` key tuple in `display_rates()` byte-for-byte (or list all names in docs + a regression test importing `display_rates()` with legacy env keys).
  - From Cursor-dyn-blended-override-chain: Add to `python/test_report_tokens_cost.py`: `display_rates(environ={"LARCH_TOKEN_RATE_PER_M": "9"})` yields `claude_blended==9` when `LARCH_CLAUDE_RATE_PER_M` is unset; keep after moving `env_rate` tests off `report_tokens_models.py`.
  - From Codex-dyn-blended-override-chain: Revise the plan to define one explicit env-ladder mapping copied from python/report_tokens_cost.py:66-79, and add one focused partial-override test asserting bucket env beats blended env, missing buckets use blended fallback, and Claude LARCH_TOKEN_RATE_PER_M remains an alias.




### FINDING_1: Model threading misses negotiation and review-fix Codex helpers
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: The plan omits active Codex usage helper call sites that already resolve Codex model args. `codex_negotiation` and `codex_review_fix` rows may still be recorded without model metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these two scripts and sibling docs/tests to the model-threading work: extract the resolved model from the args and pass it to external_launcher_record_usage_from_events or codex_launcher_record_usage_from_events
  - From Codex-Innovation: Add run-negotiation-round.sh and review-and-fix.sh to the plan, extract the Codex model from their model arg arrays, pass it to external_launcher_record_usage_from_events/codex_launcher_record_usage_from_events, and update sibling docs plus focused tests


### FINDING_3: Optional model argument collides with optional token record path
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-sidecar-wire-format
- **Severity**: important
- **Concern**: Adding model as a trailing optional positional argument makes helper arity ambiguous. Existing direct-ledger and sidecar-mode callers can misroute a model string as a token-record path, or a token-record path as a model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Define an unambiguous contract: e.g. empty fifth arg when only model is needed, named --model flag, or MODEL= only when arg5 ends with .token-record; update lib-external-launcher-common.md and every direct-record caller
  - From Cursor-dyn-sidecar-wire-format: Fix arity in the plan: always pass token_record_path (use "" for direct-ledger mode) before model, or add an explicit named model parameter/env; document the 6-arg contract and update every caller matrix


### FINDING_4: launch-codex-exec sidecar audit does not cover prompt-side call sites
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan does not finish the promised audit of `launch-codex-exec` sidecars. Prompt-side Codex judge or research calls may still write `.token-record` files without active-ledger ingestion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Extend the audit to these runtime prompt call sites and add exactly-once sidecar ingestion after collection, or centralize active-ledger recording in launch-codex-exec and remove duplicate per-call active ingestion


### FINDING_5: TOKEN_RECORD can point at a stale sidecar after preflight failure
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: `launch-codex-exec.sh` can emit a `TOKEN_RECORD` path before the sidecar is truncated. A reused output path plus preflight failure may expose prior usage for stale ledger append.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Truncate or remove ${OUTPUT}.token-record immediately after OUTPUT validation and before any preflight failure path, then emit TOKEN_RECORD only after that cleanup


### FINDING_6: Render golden fixtures keep extra copies of default rates
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan regenerates golden markdown fixtures that still pin shipped default rate tables. That violates the intended single-authority plus one snapshot acceptance rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Change the render golden tests or fixtures so shipped default rates are pinned only by the one display_rates snapshot, for example inject non-authoritative test rates or scrub the rates legend before golden comparison


### FINDING_7: Step 2b ingestion tests target the wrong wrapper
- **Reviewer(s)**: Cursor-dyn-ingestion-choreography
- **Severity**: important
- **Concern**: The proposed stale-sidecar and active-ledger tests are placed in `test-design-driver.sh`, which may not exercise `design-step2b-drafter.sh`. The real wrapper behavior may remain untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ingestion-choreography: Add a dedicated skills/design/scripts/test-design-step2b-drafter.sh (stub launch-codex-drafter.sh) or extend an existing design-step2b wrapper harness; keep test-launch-codex-drafter.sh for launcher-only copy semantics


### FINDING_8: Autofix sidecar ingestion is planned inside the tmpdir mutation guard
- **Reviewer(s)**: Codex-dyn-ingestion-choreography
- **Severity**: important
- **Concern**: The plan places Codex autofix sidecar ingestion before the tmpdir guard completes. The guard may treat ledger mutations as non-target changes and restore or remove them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-ingestion-choreography: Move autofix sidecar ingestion until after the tmpdir guard and restore block completes, before the `dispatch_rc` branch decides success or fallback. Keep the launcher sidecar-only.


### FINDING_9: lint-fix sidecar ingestion may remain success-only
- **Reviewer(s)**: Codex-dyn-ingestion-choreography
- **Severity**: important
- **Concern**: The plan does not explicitly remove the current `parsed_exit == 0` gate for `codex_lint_fix` sidecar ingestion. Failed Codex attempts with parseable usage may remain uncounted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-ingestion-choreography: Direct the lint-fix change to ingest any non-empty `${run_dir}/codex.log.token-record` after the launcher returns, regardless of `parsed_exit`, warn-not-fail, then preserve the existing waterfall return behavior.


### FINDING_12:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:27-29
- **Concern**: [SCOPE-REDUCTION] Plan re-derives Claude blended fallback from the 3-bucket fleet mix instead of only Codex/Cursor. Scenario: Issue authorizes new blended defaults for Codex (~$1.10/M) and Cursor (~$0.25/M) only; Claude per-bucket Opus 4.8 rates stay unchanged. Deriving Claude blended from 7%/92%/1% over input/cache-read/output yields ~$1.06/M versus today's $0.80/M. Aggregate-only Claude and claude_sub rows without BUCKETS_* would reprice on unrelated runs
- **Proposed resolution**: Limit fleet-mix derivation to Codex and Cursor blended defaults; keep the existing Claude blended default (or document an explicit issue-approved change with acceptance dollars)



### FINDING_1: launch-codex-ci sidecars can hardcode the wrong model
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan conflicts on whether `launch-codex-ci.sh` records the resolved Codex model or hardcoded `gpt-5.5`. Overrides can produce sidecars with false model metadata while drift checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the hardcode bullet with "write MODEL=<resolved model from MODEL_ARGS>"; keep gpt-5.5 only as the default-harness test expectation
  - From Cursor-Requirements: Replace line 137 with: write MODEL= from the resolved model variable in the sidecar (expect gpt-5.5 only under sanitized defaults); keep gpt-5.5 pinning in test-launch-codex-ci.sh assertions only.


### FINDING_3: model-basis drift parser is underspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The drift test may parse `agent-model-args.sh` output incorrectly because the script emits argv flag pairs, not a single model token. Extra flags can hide real default-model drift or cause false failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Spell out parsing: read MODEL_ARGS lines from a sanitized subprocess and extract the value after -m (Codex) or --model (Cursor); assert against DEFAULT_VENDOR_MODEL only


### FINDING_4: live Python ship-pr Codex lint-fix path lacks model capture
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The default Python ship-pr driver still launches Codex lint-fix outside the planned model-capture path. A live vendor row can remain unmodeled and outside the drift guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update python/checks.py to resolve the Codex model or route through launch-codex-exec, then pass the resolved model to codex_launcher_record_usage_from_events using the new empty arg-5 direct-ledger convention


### FINDING_7: new shell harness lacks a sibling contract doc
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan creates `skills/design/scripts/test-design-step2b-drafter.sh` without the required sibling `.md` contract for new or touched scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add ### NEW: skills/design/scripts/test-design-step2b-drafter.md with a short harness contract, Makefile or relevant-check wiring if applicable, and edit-in-sync notes.


### FINDING_9: collector retry sidecars can be missed
- **Reviewer(s)**: Codex-dyn-sidecar-lifecycle, Codex-dyn-prompt-site-coverage
- **Severity**: important
- **Concern**: Prompt-side Codex sidecar ingestion targets the original output path, but `collect-agent-results.sh` can relaunch into retry output basenames and make those retry files the active reviewer output. The active ledger can miss billable retry usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sidecar-lifecycle: In each collection site, parse the Codex REVIEWER_FILE from collector output and ingest ${REVIEWER_FILE}.token-record exactly once; keep absent or empty sidecars as no-op and skip Claude fallback outputs
  - From Codex-dyn-prompt-site-coverage: Update the plan for each prompt-side launch-codex-exec collection site to ingest every existing non-empty Codex sidecar for the original output plus collector retry variants, for example ${output}.token-record, ${output%.txt}-retry.txt.token-record, and where substantive validation is enabled ${output%.txt}-ns-retry.txt.token-record, exactly once after collection settles


### FINDING_10: judge sidecar ingestion has two possible owners
- **Reviewer(s)**: Codex-dyn-sidecar-lifecycle
- **Severity**: important
- **Concern**: The plan assigns Codex judge sidecar ingestion to both the shared dialectic protocol and the `/design` caller layer. If both implement ingestion, the same sidecar can be counted twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sidecar-lifecycle: Make exactly one layer own judge sidecar ingestion; in the other layer, reference that owner and explicitly say not to ingest the same sidecar again


### FINDING_11: launch-cursor-ci can append stale sidecars
- **Reviewer(s)**: Codex-dyn-sidecar-lifecycle
- **Severity**: important
- **Concern**: Cursor CI sidecars gain `MODEL`, but the normal path still does not clear `${OUTPUT}.token-record` before launch. Reused output paths can append stale usage when current usage parsing emits no fresh sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sidecar-lifecycle: Add rm -f or truncation of ${OUTPUT}.token-record immediately after OUTPUT validation and before any Cursor preflight or launch branch can emit TOKEN_RECORD; leave no-usage runs with an empty sidecar


### FINDING_13: env override ladder tests are incomplete after env_rate move
- **Reviewer(s)**: Cursor-dyn-env-override-chain
- **Severity**: important
- **Concern**: The plan deletes the duplicate `env_rate()` but does not require complete tests for every legacy alias, alias precedence, and malformed-value handling in the new authority. The env override ladder can regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-env-override-chain: Add one parametrized `display_rates(environ=...)` test over each ladder tuple (primary unset, each secondary alias set alone) asserting the resolved bucket/blended field; port generic `env_rate()` precedence/malformed-value cases to `python/test_report_tokens_cost.py`.
  - From Cursor-dyn-env-override-chain: A port `test_env_rate_alias_precedence` (and zero/negative/malformed skip cases) into `python/test_report_tokens_cost.py` against the sole authority `env_rate()`.


### FINDING_15: failed research Codex lanes may be replaced before usage ingest
- **Reviewer(s)**: Cursor-dyn-prompt-site-coverage
- **Severity**: important
- **Concern**: The research-phase plan does not explicitly ingest Codex sidecars for failed lanes before runtime Claude replacement. Failed Codex launches can still emit usage, but replacement can hide that billable sidecar from the ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-prompt-site-coverage: Add explicit instructions: for every Codex lane launched when codex_available=true, ingest $RESEARCH_TMPDIR/codex-research-{arch,edge,ext,sec}-output.txt.token-record once immediately after section 1.4 collection parsing and before section 1.4 runtime-timeout replacement; warn-not-fail; do not gate on STATUS=OK


### FINDING_16: failed Codex judge sidecars may be skipped
- **Reviewer(s)**: Cursor-dyn-prompt-site-coverage
- **Severity**: important
- **Concern**: The dialectic judge plan says to ingest after collection, but does not require best-effort ingestion when the Codex judge fails and is marked ineligible. Failed judge runs can still emit billable usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-prompt-site-coverage: Add: after external judge collection, ingest $DIALECTIC_TMPDIR/codex-judge-output.txt.token-record (or $DESIGN_TMPDIR when bound) exactly once via shared append-record plus record-vendor-sidecar helpers; warn-not-fail; ingest even when judge STATUS!=OK if sidecar has usage




### FINDING_1: Codex retry sidecar candidates miss nested NOT_SUBSTANTIVE retry outputs
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Codex sidecar ingestion can miss nested NOT_SUBSTANTIVE retry outputs. If a retry output later launches an `*-ns-retry.txt` attempt, the sidecar candidate set may omit that nested retry token record, so billable Codex usage is not appended or recorded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Build NS retry sidecar candidates from every collected output path, including retry outputs, or glob and de-duplicate matching *-ns-retry.txt.token-record paths for the lane before ingestion.


### FINDING_2: launch-codex-ci can ingest stale sidecars after model preflight failure
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-ingestion-ownership
- **Severity**: important
- **Concern**: `launch-codex-ci.sh` does not require early cleanup of `${OUTPUT}.token-record` before model/auth preflight. A reused output path plus a failing model-args preflight can leave an old token-record in place, which later append-record callers may ingest as current usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move the ${OUTPUT}.token-record truncation to immediately after OUTPUT validation, before model resolution and auth prep, and cover that preflight stale-sidecar case
  - From Codex-dyn-ingestion-ownership: Add launch-codex-ci cleanup immediately after OUTPUT validation and before prompt/model/auth preflight, and cover the stale-sidecar preflight path in the existing launch-codex-ci test updates.


### FINDING_5: ship-pr recovery waterfall sidecars are not appended to the ledger
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan omits a `launch-*-ci` call site from the sidecar ingestion audit. `run_recovery_waterfall` can launch Codex or Cursor CI recovery runs and return success without appending `${output}.token-record`, so billable recovery usage can be absent from `token-report.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add scripts/ship-pr.sh to the plan and ingest each recovery waterfall ${output}.token-record exactly once with the shared helper, warn-not-fail, before continue or successful return; add a focused regression for a successful waterfall tier


### FINDING_6: Makefile is planned but absent from declared scope
- **Reviewer(s)**: Cursor-dyn-undeclared-scope-files, Codex-dyn-undeclared-scope-files
- **Severity**: important
- **Concern**: The plan proposes Makefile changes for test wiring, but `Makefile` is absent from `scope-files.txt`. Implementers following the declared scope may miss or be unable to complete the planned CI or harness wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-undeclared-scope-files: Add Makefile to scope-files.txt or drop the Makefile subsection and rely solely on scripts/relevant-checks.sh wiring already planned at plan.txt:553-561
  - From Codex-dyn-undeclared-scope-files: Declare `Makefile` in scope if the standalone harness remains; otherwise fold the Step 2b assertions into an existing in-scope harness and remove the Makefile target/test-strategy lines


### FINDING_7: lint-fix-loop sidecar ingestion may omit IMPLEMENT_TMPDIR
- **Reviewer(s)**: Cursor-dyn-ingestion-ownership
- **Severity**: important
- **Concern**: The lint-fix-loop plan switches to `token record-vendor-sidecar` but does not require exporting `IMPLEMENT_TMPDIR` into the subprocess environment. Without it, ledger resolution can return no ledger and exit successfully without recording Codex usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ingestion-ownership: Specify in `scripts/lint-fix-loop.md` / `lint-fix-loop.sh` that the shared sidecar helper is invoked as `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" python3 … token record-vendor-sidecar --input "${run_dir}/codex.log.token-record"` (and keep warn-not-fail).




### FINDING_1: Preserve drafter sidecar before cleanup
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The drafter sidecar copy or ingestion must happen before any branch deletes the raw Codex output or its `.token-record`, including failure, delimiter-error, empty-output, and success paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Implement copy of `${_codex_raw}.token-record` to `${OUTPUT_CANON}.token-record` immediately after `launch-codex-exec.sh` returns and before any `rm -f "$_codex_raw"`; add harness assertions on all three failure branches plus success (plan’s new tests should pin this ordering explicitly).


### FINDING_2: Python CI and conflict tiers still drop vendor sidecars
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Codex-dyn-ingestion-ownership
- **Severity**: important
- **Concern**: The default Python ship and rebase paths launch Codex/Cursor CI tiers through `agents.py`, `ci_monitor.py`, and `rebase.py`, but the plan targets bash paths and `python/checks.py`. Those Python tiers can still emit `.token-record` sidecars that never reach the run ledger or active cost ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add exactly-once sidecar ingestion after each tier launch in the Python waterfall (e.g. in `ci_monitor.py` `launch_fn` and the `rebase.py` conflict fixer launch path, or centrally in `python/agents.py:run_waterfall`), using the shared `token record-vendor-sidecar` helper with `IMPLEMENT_TMPDIR` exported; add focused tests in `python/test_ci_monitor.py` / `python/test_agents.py`.
  - From Cursor-Pragmatic: Retarget recovery sidecar ingestion and tests to `python/ci_monitor.py` / `python/agents.py` (and `python/rebase.py` if conflict fixer tiers bill tokens). Drop or narrow `python/checks.py` recovery-waterfall sections to lint-fix model threading only.
  - From Codex-Pragmatic: Add a plan step for the shared Python launcher path or its ci_monitor/rebase callers to ingest TOKEN_RECORD or ${output}.token-record exactly once, before rollback/continue/success returns, using the same append-record plus active-ledger helper with IMPLEMENT_TMPDIR.
  - From Codex-dyn-ingestion-ownership: Add `python/ci_monitor.py`, `python/rebase.py`, and focused tests to the plan; after each Codex or Cursor tier returns, ingest `${output}.token-record` exactly once with `token append-record` and `token record-vendor-sidecar` before rollback, short-circuit, or success handling can skip accounting.


### FINDING_3: Acceptance repricing is not pinned by a test
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The required 4B3C1A5A repricing result is only a manual acceptance check. A wrong rate table or bucket mapping could pass the planned synthetic fixture tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add one parametrized price_run (or token cost CLI) test using those bucket counts and default shipped rates, asserting Codex and Cursor costs within a small tolerance


### FINDING_5: Bash primary CI-fix path misses active-ledger ingestion
- **Reviewer(s)**: Cursor-dyn-ingestion-ownership
- **Severity**: important
- **Concern**: The bash `ship-pr.sh` winning-tier CI-fix path appends the token record to `token-report.ndjson` but does not also call `record-vendor-sidecar`, so live `/implement` cost lines can omit the main CI-fix tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ingestion-ownership: Add an explicit `### UPDATED` `_stage_and_push_ci_fixes` step: after `append-record`, call `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" python3 … token record-vendor-sidecar --input "$token_record_input"` (warn-not-fail, skip empty), matching the recovery-waterfall contract


### FINDING_6: Codex implement model threading needs empty arg 5
- **Reviewer(s)**: Cursor-dyn-contract-doc-sync, Codex-dyn-contract-doc-sync
- **Severity**: important
- **Concern**: The new 6-argument `codex_launcher_record_usage_from_events` contract reserves argument 5 for a token-record path and argument 6 for model. The direct-ledger `launch-codex-implement.sh` caller must pass an empty argument 5 or it may misrecord the model or switch into sidecar behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-doc-sync: Add the same explicit contract used elsewhere: pass `""` as arg 5 and the resolved model as arg 6; mirror it in `scripts/launch-codex-implement.md`
  - From Codex-dyn-contract-doc-sync: Update the launch-codex-implement.sh and .md plan bullets to require codex_launcher_record_usage_from_events "$PLUGIN_ROOT" "$CODEX_EVENTS" "$SIDECAR_LOG" "codex_implement" "" "$resolved_model" and document the empty arg-5 direct-ledger contract.


### FINDING_7: Step 2b tests must assert appended run-log row
- **Reviewer(s)**: Codex-dyn-contract-doc-sync
- **Severity**: important
- **Concern**: The planned drafter-sidecar tests only assert active-ledger recording. They do not pin the required `token append-record` row in `$DESIGN_TMPDIR/token-report.ndjson`, so committed run logs could still miss `codex_plan_draft`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-doc-sync: Add the matching test and sibling contract assertion: successful Codex Step 2b writes exactly one $DESIGN_TMPDIR/token-report.ndjson row with raw=codex_plan_draft, and the stale-sidecar case writes none.


### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:401-447
- **Concern**: [SCOPE-REDUCTION] Prompt-side Codex sidecar ingestion is expanded into research validation and voter markdown orchestrator docs. Scenario: Those paths are not launcher call sites and are not enforced by scripts or CI. A rates-and-drafter fix can ship while research validation and judge lanes still omit retry sidecars. The plan adds ~400 lines of orchestrator prose beyond the approved outline surfaces.
- **Proposed resolution**: Limit ledger-completeness edits to script-owned call sites named in the issue audit (launch-codex-exec launch-codex-ci launch-codex-drafter design-step2b-drafter ship-pr lint-fix auto-fix). File follow-up issues for prompt-side retry matrices.


### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:37-43
- **Concern**: [SCOPE-REDUCTION] Plan treats scope-files.txt as a repo file to update, but no such repo file exists. Scenario: Implementer may create or edit a bogus root file instead of updating the design scope manifest, leaving the actual implementation scope declaration wrong
- **Proposed resolution**: Remove the ### UPDATED: scope-files.txt file entry. Keep scope-manifest updates as design metadata, or name the real staged-context scope artifact outside the repo file list


### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:120-255
- **Concern**: [SCOPE-REDUCTION] `MODEL=` threading through every Codex/Cursor launcher is prep for out-of-scope per-record pricing, not required to fix wrong defaults or the drafter gap.. Scenario: The issue needs `DEFAULT_VENDOR_MODEL` aligned with `agent-model-args.sh` and optional model on new sidecars; touching `launch-review.sh`, `launch-codex-implement.sh`, `run-negotiation-round.sh`, `review-and-fix.sh`, etc. multiplies review risk without changing repriced totals today.
- **Proposed resolution**: Limit model capture to new sidecar producers/consumers (drafter, autofix, CI sidecars, shared helper) plus the sanitized drift test; skip retroactive model fields on direct-ledger paths until per-record pricing is in scope.


### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:401-467
- **Concern**: [SCOPE-REDUCTION] Prompt-only Codex sidecar ingestion across research/validation/voting/judge docs is not mechanically enforced. Scenario: Updates to `skills/research/references/*.md`, `skills/shared/voting-protocol.md`, and `skills/shared/dialectic-protocol.md` rely on the orchestrator following prose. Missed ingestion or double-ingestion will not fail CI; `#3689` acceptance only requires `/design` `codex_plan_draft` plus rate authority.
- **Proposed resolution**: Limit this PR to shell/Python hooks with harness coverage (Step 2b drafter, autofix, lint-fix, ship recovery). File follow-up issues for prompt-side collector ingestion, or add a single shared ingestion helper invoked from existing wrapper scripts instead of markdown-only instructions.



