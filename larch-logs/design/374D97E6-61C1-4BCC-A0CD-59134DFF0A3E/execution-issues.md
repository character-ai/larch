### Warnings

- **Step design Step 2b.5 — check-plan-size.sh failed (exit 2)**:
  ```
PLAN_SIZE_STATUS=invalid-mechanical-churn
invalid-mechanical-churn: 900
  ```
### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	scripts/launch-codex-drafter.sh:275 scripts/launch-claude-drafter.sh:294	Approved outline call sites omit drafter filter-manifest cutover	Both drafters invoke scout-plan-archetypes-wrapper.sh --filter-manifest which is deleted; Step 2b scout filtering breaks	Add ### UPDATED entries for scripts/launch-codex-drafter.sh and scripts/launch-claude-drafter.sh cut to python3 cli.py scout filter-manifest preserving || true capture and SCOUT_STATUS parse-failed vs ok/empty gating
2	in_scope	important	correctness	skills/design/scripts/plan-review-loop.sh:234-241	[SCOPE-REDUCTION] Stale PLAN_REVIEW_SCOUT_SH default change	plan-review-loop.sh no longer invokes scout (#4061); bullet adds dead wiring or misleads implementers	Remove the PLAN_REVIEW_SCOUT_SH retarget bullet; limit plan-review-loop.sh changes to findings-classification header and scope-anchor CLI replacements plus guard/source removal
3	in_scope	important	correctness	skills/design/scripts/plan-review-loop.sh:11-43 skills/design/scripts/run-step3-review.sh:165-171	Missing explicit removal of lib-scope-anchor-handoff source guards	After deleting scripts/lib-scope-anchor-handoff.sh sourced helpers and file-existence checks fail at startup	Specify removing the lib-scope-anchor-handoff.sh presence guard and source lines in both scripts when switching to python cli.py scope-anchor verbs
4	in_scope	important	completeness	skills/design/references/plan-review.md:38-42	plan-review.md update retargets Step 3 scout without reconciling Step 2b ownership	Section 1 still describes per-round scout-plan-archetypes-wrapper invocation while lines 54-60 say manifest is Step 2b materialized; Python path swap alone preserves doc/behavior drift	Revise Dynamic plan-review archetypes step 1 to state Step 2b writes scout-plan-manifest.json and Step 3 consumes it; document filter-manifest only on drafter launchers via python cli.py scout filter-manifest
5	in_scope	important	risk-integration	scripts/test-dispatch-plan-voters.sh:141	Harness still copies deleted lib-scope-anchor-handoff.sh	cp fails once scripts/lib-scope-anchor-handoff.sh is deleted; make test-harnesses-19 / make lint fails	Add ### UPDATED scripts/test-dispatch-plan-voters.sh to stop copying the retired library and stub scope-anchor CLI behavior instead

### FINDING_1: completeness — `scripts/launch-codex-drafter.sh:275`, `scripts/launch-claude-drafter.sh:294`
Approved outline lists both drafters as call sites, but the plan has no `### UPDATED` entries for them. They are the live `--filter-manifest` consumers after Step 2b (#4061). Deleting `scout-plan-archetypes-wrapper.sh` without retargeting them breaks drafter scout filtering.

**Suggested revision:** Add cutover entries pointing at `python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest`, preserving the existing `|| true` capture and `SCOUT_STATUS` parsing (treat only `parse-failed` as failure).

### FINDING_2: correctness — `skills/design/scripts/plan-review-loop.sh:234-241`
**[SCOPE-REDUCTION]** The plan retargets `$PLAN_REVIEW_SCOUT_SH` to the Python CLI, but current `plan-review-loop.sh` has no scout invocation (removed in #4061). This is stale scope, not a required cutover.

**Suggested revision:** Drop the `PLAN_REVIEW_SCOUT_SH` bullet; keep only findings-header and scope-anchor CLI changes for this file.

### FINDING_3: correctness — `skills/design/scripts/plan-review-loop.sh:11-43`, `skills/design/scripts/run-step3-review.sh:165-171`
The plan replaces handoff *calls* but does not require removing the `lib-scope-anchor-handoff.sh` file-existence guard or `source` lines. After deletion, both scripts fail before Step 3 runs.

**Suggested revision:** Explicitly require removing the guard and `source` statements when wiring `python/cli.py scope-anchor ...`.

### FINDING_4: completeness — `skills/design/references/plan-review.md:38-42`
The plan updates scout references to Python CLI paths without reconciling the doc split: §1 still describes per-round wrapper scouting, while §54-60 documents Step 2b manifest ownership. A path-only swap can leave Step 3 documented as still running scout.

**Suggested revision:** Rewrite §1 to match Step 2b manifest production and Step 3 consumption; reserve `scout filter-manifest` for drafter launchers only.

### FINDING_5: risk-integration — `scripts/test-dispatch-plan-voters.sh:141`
The harness copies `scripts/lib-scope-anchor-handoff.sh` into a plugin stub. That file is deleted in this slice. `make test-harnesses-19` (part of `make lint`) will fail.

**Suggested revision:** Add an `### UPDATED` entry for `scripts/test-dispatch-plan-voters.sh` to stub the Python scope-anchor surface instead of copying the retired shell library.

[OUT_OF_SCOPE] `skills/design/scripts/plan-review-loop.md:29` still documents `$PLAN_REVIEW_SCOUT_SH` per-round scouting; should be cleaned during the stale-reference sweep or a follow-up doc fix, not by reintroducing scout into the loop.

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

timing: WARNING: unknown task-kind: cursor-phase1-cursor-plan-requirements
  ```
