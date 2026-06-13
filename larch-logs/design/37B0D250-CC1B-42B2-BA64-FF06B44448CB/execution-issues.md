### Warnings

- **Step design Step 2b.5 — python plan check-size failed (exit 2)**:
  ```
PLAN_SIZE_STATUS=invalid-mechanical-churn
  ```

- **Step design Step 5c — design-log-publish.sh failed (exit 1)**:
  ```
design-log-publish: staging failed for <TMPDIR>/aggregator-output.txt.json
  ```
### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=file missing or not readable: <TMPDIR>/cursor-plan-arch-output.txt

## Reviewer output (<TMPDIR>/cursor-plan-arch-output.txt)

Reviewing the plan and tracing cited codebase paths for architecture and contract alignment.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	architecture	python/plan_review.py:run_step3_loop	`run_step3_loop` omits `plan-review-continuation.sh` and `approve_requested` wiring	The absorbed `review-design-step3-loop.sh` calls `plan-review-continuation.sh --approve-requested "$APPROVE_REQUESTED"` at `awaiting-continuation` and then `plan-review step3-state --auto-continuation-entry` before the next round. The plan ports the loop script but never names continuation, run-params binding, or the follow-on state helper. Multi-round Step 3 can stop after one round or mis-handle `--per-round-approval`.	Add an explicit step: keep `skills/design/scripts/plan-review-continuation.sh` as a subprocess from `run_step3_loop`, read `approve_requested` from `run-params.json`, preserve `REASON`/`PANEL_PRUNED_EMPTY` in `.step3-review-result.env`, and retain the `--auto-continuation-entry` call. Add pytest (or retarget `test-step3-review-cap.sh`) for ballot-items-lost and pruned-empty continuation.
1	in_scope	important	correctness	skills/design/scripts/design-step3-review.sh:291-293	Wrapper still sources deleted `review-design-step3-loop.sh` on env-read failure	The plan only swaps the inner launch to `plan-review run`. Today, when `read-result-env.sh` fails, the wrapper sources `review-design-step3-loop.sh` solely to call `step3_record_report_evidence`. Retiring that script without a replacement drops escalation ledger writes on degraded paths.	Move `step3_record_report_evidence` (and postplan-failed staging) into `plan_review.py` or a small shared helper invoked from both `plan-review run` and the wrapper failure path; delete the `source review-design-step3-loop.sh` block. Extend `test-design-step3-review` coverage to target the new surface.
1	in_scope	important	completeness	python/plan_review.py:run_plan_review_round	Single-pass round port omits collector/aggregator/prune-nit subprocess seams	`plan-review-loop.sh` (listed for retirement) still orchestrates `collect-agent-results.sh`, optional `aggregate-findings.sh` (`LARCH_AGGREGATOR_DISABLED`), and `prune-nit-findings.sh` between panel dispatch and tally. The plan documents panel/voter dispatch and tally but not these three calls. A ported round can launch reviewers yet fail to collect, aggregate, or prune before tally.	Document and implement the same injectable subprocess hooks in `run_plan_review_round`, including fail-open prune-nit behavior and aggregator disable semantics. Port the relevant cases from `test-plan-review-loop.sh`.
1	in_scope	important	risk-integration	python/plan_review.py:run_step3_loop	Loop post-apply pipeline subprocesses not pinned	The absorbed loop still shells out to `design-postplan-emit.sh --with-plan-size`, `gate-b-dedup-plan.sh`, `design-pause-save.sh` (postplan rc 11), and `write-design-round-meta.sh` after revise. The plan ports Gate B dedup to Python but does not state that postplan emit, pause, and round-meta refresh stay bash subprocesses. An implementer may reimplement postplan in Python and break the shared post-apply contract.	Under `run_step3_loop`, list retained bash subprocesses explicitly (postplan emit, pause-save, write-design-round-meta) versus in-process `plan_quality` / `plan-review gate-b-dedup` calls. Add loop tests for postplan-operator, pause, and revise tier metadata.
1	in_scope	important	correctness	skills/design/scripts/test-design-step3-review.sh	Surviving harness still hard-depends on deleted loop script	`test-design-step3-review.sh` greps and sources `review-design-step3-loop.sh` for escalation and postplan-failed contracts. It is still a `make test-harnesses-4` / `make test-design-step3-review` target but is absent from the plan’s retire/retarget lists. Cutover leaves `make lint` red while claiming harness parity.	Retarget the harness to `python/plan_review.py` / `plan-review run` (or fold into `python/test_plan_review.py`) and drop static greps of the retired script. Update Makefile shard docs in the same change.
1	out_of_scope	latent	architecture	docs/SECURITY.md:97-167	Stale-reference sweep omits SECURITY.md	The plan updates many docs but not `SECURITY.md`, which still names `run-step3-review.sh`, `emit-design-plan-preview.sh`, and `lib-design-round-artifacts.sh`. This does not block the port but can leave security-boundary prose wrong after deletion.	Add `SECURITY.md` to the stale-reference sweep in a follow-up issue.

## Reviewer stderr (<TMPDIR>/cursor-plan-arch-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-arch-output.txt.launch-stderr)

timing: WARNING: unknown task-kind: cursor-phase1-cursor-plan-arch
  ```

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/design/scripts/review-design-step3-loop.sh:539-565	Retiring review-design-step3-loop.sh without a plan-review-continuation contract	run_step3_loop loses awaiting-continuation; auto multi-round review stops after round 1 or mis-routes phase resumes	Document that run_step3_loop subprocesses the existing plan-review-continuation.sh (or ports its KV contract verbatim); add pytest coverage for continuation-failed and ballot-items-lost branches
2	in_scope	important	correctness	skills/design/scripts/design-step3-review.sh:291-293	step3_record_report_evidence lives only in the deleted loop script	Env-read failure path sources review-design-step3-loop.sh for escalation recording; after deletion panel-failed loses ledger evidence and may miss escalation-success filing	Move step3_record_report_evidence into design-step3-review.sh (or a tiny helper kept alongside the wrapper); mirror the same call from the Python loop envelope path
3	in_scope	important	correctness	skills/design/scripts/design-step3-entry-preview.sh:90-92	skills/design/scripts/run-step3-review.sh:119-150	Step 3 preview sentinel .step3-entry-plan-printed is owned by run-step3-review --preview-only, not the pure preview renderer	Swapping the wrapper to plan-review preview alone drops sentinel write/skip; every Step 3 re-entry reprints the plan candidate	Keep sentinel logic in design-step3-entry-preview.sh: skip when sentinel exists, call plan-review preview --variant step3, touch sentinel only when output contains ## Plan Candidate for Review
4	in_scope	important	risk-integration	skills/design/scripts/test-design-step3-review.sh:43-63	Harness still sources review-design-step3-loop.sh at runtime but plan neither updates nor retires it	make lint runs test-design-step3-review via test-harnesses-4; after loop deletion the harness fails even if pytest passes	Retarget the harness to the Python loop/CLI surface or fold its runtime ledger checks into python/test_plan_review.py; drop Makefile routing if absorbed
5	in_scope	important	risk-integration	skills/design/scripts/plan-review-loop.sh:17-21	skills/design/scripts/persist-retally-step3-env.sh:223	Loop port plan omits bash subprocess seams the absorbed scripts still call via env overrides	plan_review.py may ship without collection, aggregation, prune-nit, round-meta, or postplan wiring; rounds terminate early or publish incomplete round-meta.json	List retained subprocesses explicitly in plan_review.py (collect-agent-results.sh, aggregate-findings.sh, prune-nit-findings.sh, write-design-round-meta.sh, design-postplan-emit.sh) with the same injectable override env vars
6	in_scope	important	correctness	python/plan_review.py:76	[SCOPE-REDUCTION] Blanket in-process C3a2 rule conflicts with loop post-apply behavior	Implementer may re-port design-postplan-emit into Python, expanding scope and duplicating design-postplan-emit.sh cutover already planned	Clarify run_step3_loop post-apply keeps subprocessing design-postplan-emit.sh --with-plan-size; reserve in-process plan_quality only for revise-waterfall and gate-b dedup paths
1	in_scope	important	correctness	skills/design/scripts/review-design-step3-loop.sh:539-565 — **plan-review-continuation.sh** is invoked at `awaiting-continuation` but the plan retires `review-design-step3-loop.sh` without naming continuation. **Suggested revision:** subprocess the existing `plan-review-continuation.sh` from `run_step3_loop` (minimum change) or port its KV contract; cover `continuation-failed`, `ballot-items-lost`, and `pruned-empty` in pytest.

2	in_scope	important	correctness	skills/design/scripts/design-step3-review.sh:291-293 — **`step3_record_report_evidence`** is defined only in the loop script the plan deletes, yet the wrapper still sources that file on env-read failure. **Suggested revision:** relocate the helper next to `design-step3-review.sh` and call it from both the wrapper failure path and the Python loop terminal statuses.

3	in_scope	important	correctness	skills/design/scripts/design-step3-entry-preview.sh:90-92 — **`.step3-entry-plan-printed`** sentinel logic lives in `run-step3-review.sh --preview-only`, not in the pure preview renderer. **Suggested revision:** re-home sentinel skip/touch in `design-step3-entry-preview.sh` when switching to `plan-review preview --variant step3`.

4	in_scope	important	risk-integration	skills/design/scripts/test-design-step3-review.sh:43-63 — runtime harness **sources the deleted loop**; it is absent from both the pytest port list and the harness deletion list while `Makefile` `test-harnesses-4` still runs it. **Suggested revision:** migrate runtime ledger checks into `python/test_plan_review.py` or update the harness before deleting `review-design-step3-loop.sh`.

5	in_scope	important	risk-integration	skills/design/scripts/plan-review-loop.sh:17-21 — **collection/aggregation/prune/round-meta/postplan** subprocess seams are not listed for the Python loop port. **Suggested revision:** document retained bash calls (`collect-agent-results.sh`, `aggregate-findings.sh`, `prune-nit-findings.sh`, `write-design-round-meta.sh`, `design-postplan-emit.sh`) with the same `LARCH_*_SH` override pattern to avoid silent wiring gaps.

6	in_scope	important	architecture	python/plan_review.py:76 — **[SCOPE-REDUCTION]** “Do not shell out to retired C3a2 surfaces” is too broad for the loop body, which today shells to `design-postplan-emit.sh`. **Suggested revision:** narrow the rule to revision/dedup in-process only; keep post-apply on the existing bash wrapper to avoid duplicating `design-postplan-emit.sh` migration work.

[OUT_OF_SCOPE] latent risk-integration scripts/test-step3-orchestrator-fence.sh:39-40 — comment still mirrors `run-step3-review.sh --mode loop` handoff strings; update when SKILL.md paths change (cosmetic drift only).

## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-pragmatic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-pragmatic-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-pragmatic-output.txt.launch-stderr)

timing: WARNING: unknown task-kind: cursor-phase1-cursor-plan-pragmatic
  ```

- **Step design Step 3 — collect-agent-results.sh codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-plan-generic-output.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=file missing or not readable: <TMPDIR>/codex-plan-generic-output.txt

## Reviewer output (<TMPDIR>/codex-plan-generic-output.txt)

(file missing: <TMPDIR>/codex-plan-generic-output.txt)

## Reviewer stderr (<TMPDIR>/codex-plan-generic-output.txt.diag)

(file missing: <TMPDIR>/codex-plan-generic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-plan-generic-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-plan-generic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-plan-generic-output.txt.launch-stderr)

(empty: <TMPDIR>/codex-plan-generic-output.txt.launch-stderr)
  ```
