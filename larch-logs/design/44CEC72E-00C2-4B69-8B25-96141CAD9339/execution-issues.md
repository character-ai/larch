### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-arch-output.txt)

Reviewing the plan and tracing cited code paths for architecture and contract gaps.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/plan_review.py:run_plan_review_round	The port-source list names review-design-step3-loop.sh and run-step3-review.sh but not the gzip-only plan-review-loop.sh per-round body that run_plan_review_round still executes today	Collector STATUS gating, aggregation, prune-nit, panel dispatch, and single-round terminal mapping live in embedded plan-review-loop.sh, not only in the on-disk loop driver. An implementer can port the outer driver and miss per-round behavior that tests still pin via test_embedded_plan_review_loop_uses_migrated_collector	Name plan-review-loop.sh explicitly as a port source for run_plan_review_round; list its subprocess seams (collect-results, aggregation, prune-nit, panel-dispatch, tally handoff) and map each to native Python or a retained injectable boundary
2	in_scope	important	correctness	skills/design/scripts/review-design-step3-loop.sh:529-534	The plan omits scripts/write-design-round-meta.sh from retained loop subprocesses and RUN_STEP3_* seams	After successful revise-waterfall the live loop refreshes plan-review/round-N/round-meta.json via write-design-round-meta.sh. Without that call, revise tier/status and panel metadata stay missing and design final-summary / Review Phase Detail consumers regress	Add WRITE_DESIGN_ROUND_META_SH (default scripts/write-design-round-meta.sh) to the native post-revise path and to docs/python-migration.md RUN_STEP3 survivors; port or stub the call in pytest
3	in_scope	important	correctness	skills/design/scripts/review-design-step3-loop.sh:822	Auto-continuation still shells out to the retired embedded design-step3-state.sh path instead of the native step3-state verb	The on-disk loop calls skills/design/scripts/design-step3-state.sh on PLAN_REVIEW_CONTINUE=true. That file exists only in gzip assets. A native loop that copies the string breaks multi-round continuation and Gate C deferral	In the native continuation branch call python3 .../cli.py plan-review step3-state --auto-continuation-entry --design-tmpdir ... (same flags as design-step3-continuation-entry.sh); add a pytest continuation-chain case
4	in_scope	important	risk-integration	python/test_plan_review.py:288	The plan keeps RUN_STEP3_PLAN_REVIEW_LOOP_SH but does not define how an in-process loop honors per-round stubs	Harnesses (test_plan_review.py, test-step3-review-cap.sh, test-design-multi-round-integration.sh) inject loop behavior through RUN_STEP3_PLAN_REVIEW_LOOP_SH overriding plan-review-loop.sh only. If the native port inlines the round body with no subprocess escape hatch, cap/rollback/continuation tests lose their seam or falsely pass	Pin that RUN_STEP3_PLAN_REVIEW_LOOP_SH still overrides only the per-round body (not the multi-round driver), default unset means in-process run_plan_review_round, and document the native default in docs/python-migration.md
5	in_scope	important	security	python/plan_review.py:run_main	validate_design_tmpdir is required before tmpdir mutation but the plan does not pin validate-before-quiet_init ordering for non-preview run paths	Embedded run-step3-review.sh validates DESIGN_TMPDIR before larch_quiet_init in both single and loop branches (pinned by test_embedded_run_step3_review_round_paths_validate_before_quiet). Porting validate only inside later helpers can recreate allowlist bypass via quiet logging on disallowed tmpdirs	In run_main, call validate_design_tmpdir on --design-tmpdir before any quiet_init/contract_stream setup on all non-preview paths; add a pytest that fails if quiet_init precedes validate
6	in_scope	important	completeness	python/plan_review.py:run_plan_review_round	Per-round aggregation and prune-nit subprocess seams are not specified beyond a vague aggregation bullet	Embedded plan-review-loop.sh orchestrates aggregation (respecting LARCH_AGGREGATOR_DISABLED) and prune-nit-findings.sh with fail-open prune-nit.env persistence between collection and tally. Omitting them changes findings fed to tally and vote thresholds	Document and implement the same aggregation and prune-nit hooks in run_plan_review_round with injectable overrides and parity tests migrated from retired loop harnesses

**1. Missing explicit `plan-review-loop.sh` port source** (`completeness`, `python/plan_review.py:run_plan_review_round`)

The plan lists `run_plan_review_round` but its port-source bullets only name `review-design-step3-loop.sh`, `run-step3-review.sh`, and `plan-review-continuation.sh`. Today the per-round body still lives in gzip-only `plan-review-loop.sh` (`_DESIGN_REVIEW_LOOP`). Collector STATUS gating, aggregation, prune-nit, and single-round terminal mapping are there. Without naming that asset, the port can ship a multi-round driver that never reproduces per-round behavior.

**2. `write-design-round-meta.sh` omitted from loop seams** (`correctness`, `skills/design/scripts/review-design-step3-loop.sh:529-534`)

After a successful `plan revise-waterfall`, the live loop calls `scripts/write-design-round-meta.sh` via `WRITE_DESIGN_ROUND_META_SH`. The plan’s `RUN_STEP3_*` list and subprocess inventory do not include it. Skipping that call leaves `round-meta.json` / `panel-manifest.ndjson` stale or missing and breaks Review Phase Detail and design final-summary consumers.

**3. Auto-continuation still targets retired `design-step3-state.sh`** (`correctness`, `skills/design/scripts/review-design-step3-loop.sh:822`)

On `PLAN_REVIEW_CONTINUE=true`, the loop invokes `skills/design/scripts/design-step3-state.sh --auto-continuation-entry`. That script is embedded-only (not on disk). The plan updates `design-step3-continuation-entry.sh` but does not pin the inline loop call. A literal port of line 822 fails after gzip removal.

**4. `RUN_STEP3_PLAN_REVIEW_LOOP_SH` harness contract undefined for in-process loop** (`risk-integration`, `python/test_plan_review.py:288`)

Multiple harnesses stub only the per-round body through `RUN_STEP3_PLAN_REVIEW_LOOP_SH`. The plan preserves the env name but not how an in-process `run_plan_review_round` honors it. Without a subprocess escape hatch when the env is set, cap/rollback/continuation tests lose their injection point or give false confidence.

**5. `validate_design_tmpdir` before `quiet_init` not pinned** (`security`, `python/plan_review.py:run_main`)

The plan requires `validate_design_tmpdir` before tmpdir mutation. Embedded bash also requires validate before `larch_quiet_init` on both single and loop paths (`test_embedded_run_step3_review_round_paths_validate_before_quiet`). SECURITY.md still documents validation-before-quiet-init. A Python port that initializes quiet logging first can recreate allowlist bypass on direct `plan-review run`.

**6. Aggregation and prune-nit seams underspecified** (`completeness`, `python/plan_review.py:run_plan_review_round`)

The plan mentions “collection and aggregation calls” but not `prune-nit-findings.sh`, `prune-nit.env`, or `LARCH_AGGREGATOR_DISABLED` behavior from embedded `plan-review-loop.sh`. Dropping those steps changes findings before tally and alters vote outcomes relative to today’s loop.
## Reviewer stderr (<TMPDIR>/cursor-plan-arch-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-arch-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 7668 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	skills/design/scripts/review-design-step3-loop.sh:530-535	Plan omits the per-round `write-design-round-meta.sh` hook when porting loop round-body mechanics	Native `run_plan_review_round` can finish apply/dedup/tally without calling `WRITE_DESIGN_ROUND_META_SH` / `scripts/write-design-round-meta.sh`, so round renderer metadata stops being synthesized and run-log Review Phase Detail rows lose accepted/rejected/OOS counts	Add an explicit port step: after each round body, best-effort invoke `WRITE_DESIGN_ROUND_META_SH` defaulting to `scripts/write-design-round-meta.sh --round-dir "$DESIGN_TMPDIR/plan-review/round-${N}"`; add a pytest parity check
2	in_scope	important	correctness	skills/design/scripts/review-design-step3-loop.sh:333-342	Plan is silent on `step3_loop_refresh_issue_from_source_env` before pause-save exits	Post-apply `design postplan-emit` rc `11` execs `design pause-save`; when `ISSUE_NUMBER` is unset in the loop process, pause-save can run without the issue binding the bash path recovers from `$DESIGN_TMPDIR/source-env.sh`	Port `step3_loop_refresh_issue_from_source_env` (or equivalent) immediately before every pause-save handoff in the native loop; cover rc `11` in pytest
3	in_scope	important	correctness	python/test_plan_review.py:273-295	Cap-reached completion-sentinel tests do not require `.completed/step-3.5` even though bash writes both sentinels on `cap-reached`	Bash calls `step3_loop_write_completed_step3` before emitting `cap-hit` (review-design-step3-loop.sh:678-683). A native port that only writes `step-3`, or tests that never assert `step-3.5`, can regress the #4489 split-sentinel contract and stall or early-unlock Gate B polling	Extend the cap-reached pytest case to assert both `.completed/step-3` and `.completed/step-3.5`; state explicitly in the plan that `cap-reached` is a dual-sentinel terminal path
4	in_scope	important	risk-integration	python/test_plan_review.py:288	skills/design/scripts/test-step3-orchestrator-fence.sh:232	scripts/test-design-multi-round-integration.sh:135	Plan retargets Step 3 harnesses but does not define the post-port contract for `RUN_STEP3_PLAN_REVIEW_LOOP_SH`	After the loop moves in-process, stubbing `RUN_STEP3_PLAN_REVIEW_LOOP_SH` no longer intercepts round behavior; `make test-step3-orchestrator-fence` and `make test-design-multi-round-integration` can pass vacuously or fail unless the seam is replaced	Pick one contract and document it: either keep `RUN_STEP3_PLAN_REVIEW_LOOP_SH` as an optional external loop subprocess override with a native default, or delete the env gate and migrate every stub harness to pytest/native `plan-review run` mocks; do not leave an "or migrate" fork untested
5	out_of_scope	nit	architecture	python/design_lifecycle.py	[SCOPE-REDUCTION] New shared JSON-bool helper in `design_lifecycle.py` expands the blast radius beyond Step 3 bodies	`design_postplan.py` already shells out to `plan-review json-get-bool`; adding `design_lifecycle.py` is not required to finish the port	Implement `json-get-bool` in `plan_review.py` (or an existing shared module already used by postplan) and skip a new `design_lifecycle.py` surface unless a second consumer already exists on main

**Findings**

1. **completeness** — `skills/design/scripts/review-design-step3-loop.sh:530-535`: the plan ports the Step 3 loop but never carries forward the best-effort `write-design-round-meta.sh` call at the end of each round body. Without it, round metadata for run logs can disappear.

2. **correctness** — `skills/design/scripts/review-design-step3-loop.sh:333-342`: pause-save on postplan rc `11` depends on refreshing `ISSUE_NUMBER` from `source-env.sh`. The plan mentions pause handoff in tests but not this refresh step.

3. **correctness** — `python/test_plan_review.py:273-295`: cap-hit is a dual-sentinel path in bash (`step-3` and `step-3.5`). The planned tests call out cap short-circuit but not `step-3.5`, which weakens the pinned #4489 contract.

4. **risk-integration** — harness files still stub `RUN_STEP3_PLAN_REVIEW_LOOP_SH`, but the plan does not say whether native code will honor that env gate or replace it. That ambiguity can break `make test-step3-orchestrator-fence` and `make test-design-multi-round-integration`.

5. **[OUT_OF_SCOPE]** — `python/design_lifecycle.py`: the extra module for `json-get-bool` is optional; the verb can live in `plan_review.py` with less churn.
## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 4914 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-arch-output.txt)

Reading the plan and tracing the cited codebase paths to validate contracts and integration points.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/plan_review.py:1010-1073	Non-Step-3 gzip bodies (emit-plan finalize-plan emit-design-plan-preview tail gate-b-dedup-plan persist-retally design-step3-state record-round-timing) are listed for in-process replacement but given no port steps tests or delete ordering	The plan deletes all _LEGACY_ASSETS yet only documents Step-3 loop mechanics. Removing blobs before native emit/finalize/preview/gate-b-dedup/retally/state/timing land breaks Step 3b FINALIZE Gate C preview and MAV retally paths	Add per-verb subsections with bash source authority acceptance criteria and an explicit gate: do not remove remaining _LEGACY_ASSETS entries until each verb has native coverage
2	in_scope	important	correctness	python/plan_review.py:1091-1092	run_plan_review_round port omits explicit .step3-plan-review-result.env writer and SCOPE_ANCHOR_FILE relay gating	MAV reads .step3-plan-review-result.env first; SECURITY.md omits SCOPE_ANCHOR_FILE on tally-error. persist_envelope details only cover .step3-review-result.env	In run_plan_review_round pin a dedicated writer for .step3-plan-review-result.env mirroring embedded plan-review-loop.sh including tally-status scope-anchor omission and stdout relay
3	in_scope	important	architecture	skills/design/scripts/design-step3b-tail.sh:93-130	design-step3b-tail ownership is ambiguous between wrapper-retained FINALIZE rejected-findings SKIP_APPROVE_REQUESTED_GATEC step-4 and native plan-review step3b-tail	A thin wrapper that delegates preview-only drops Step 4 prerequisites before Gate C	Mandate one owner: implement full tail in native step3b-tail then shrink wrapper to env pause-check and CLI delegation only
4	in_scope	important	correctness	skills/design/scripts/design-step3-mav.sh:137-140	Native step3-mav port does not pin dual result-env merge order	Wrapper reads .step3-plan-review-result.env then .step3-review-result.env with the second file winning on duplicate keys. Unspecified Python merge can pick wrong SCOPE_ANCHOR_FILE or LOOP_STATUS	In plan-review step3-mav spec require the same read order and allowlist via design_lifecycle.phase_driver_read_result_env or design read-result-env
5	in_scope	important	risk-integration	python/design_postplan.py:122	python/cli.py plan-review json-get-bool is already called but not registered	Native Step 3.5 settle paths that hit design_postplan fail closed if json-get-bool is not registered before those verbs ship	Register and test json-get-bool early in the slice or have design_postplan call the shared stdlib reader directly until the CLI verb exists
6	out_of_scope	important	architecture	plan.txt:53-67	[SCOPE-REDUCTION] Full _LEGACY_ASSETS removal bundles emit/finalize and other non-Step-3 blobs beyond the issue bodies list (~3.7k Step-3 bash only)	Expands an already ~8500-line mechanical port without issue-scoped acceptance boundaries	If minimum-change is preferred narrow DoD to Step-3 loop panel voter MAV and related blobs; leave emit/finalize/retally blobs on _run_legacy until a follow-up slice
## Reviewer stderr (<TMPDIR>/cursor-plan-arch-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-arch-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
✓ cursor agent: completed (exit code 0, output 3607 bytes)
  ```
