### FINDING_1: Hard-trigger overrides must record oversize override
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Gate B and retained Step 2b.5 Override paths still only write completion, so an oversized plan can be approved by the operator but never record `oversize_override: operator`, causing Step 5c to refuse finalization as if no override existed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Teach every size Override branch (initial _postplan_rc=12, step2b5-rc-handling retained hard-trigger, settle-rc-dispatch gate-b-hard-size, and Step 5c recovery Override) to invoke plan set-oversize-override before continuing; update approval-gates.md if it documents Override semantics.
  - From Cursor-Innovation: For every Split/Override/Cancel site (initial Step 2b, discussion merged, Gate B retained): on Override call `plan set-oversize-override` then completion write; add `### UPDATED: skills/design/references/approval-gates.md` for Gate B hard-trigger text and Override flow.
  - From Cursor-Pragmatic: Make Gate B (and matching approval-gates / retained step2b5 Override text) call plan set-oversize-override before continuing, mirroring the new initial Step 2b.5 Override path.
  - From Cursor-Requirements: Plan adds a fail-closed Step 5c guard on composed-plan.md, but retained hard-size Override (Gate B, discussion, Override-after-defects) still only runs design step2b-postplan --write-completion-only. Post-review growth can trip SIZE_TRIGGER_FIRED at Gate B; Override continues without writing oversize_override: operator, so Step 5c refuses publish even after operator Override. For every retained Split/Override/Cancel hard-trigger site, make Override invoke plan set-oversize-override (plan.txt at minimum; composed-plan.md when present) before write-completion-only/continue; update settle-rc-dispatch.md, step2b5-rc-handling.md (retained vs initial site split), and approval-gates.md Gate B hard-size prose—not only the initial Step 2b SKILL.md prompt.


### FINDING_2: Compose/publish paths lose oversize_override
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Step 5c auto-compose and publish provenance splicing do not consistently treat `oversize_override: operator` as trailer metadata, so it can land in the body, be dropped from sidecar rebuilds, or be separated from `diff_lines:` before the final size check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Teach design_step5c.py from MAY_UPDATE to firm UPDATED: extend both helpers to treat oversize_override: operator as metadata; add/extend test_step5c_auto_compose_preserves_optional_trailers coverage.
  - From Codex-Arch: Teach both composition paths to treat oversize_override: operator as an optional trailer, and add a round-trip test that composes and republishes an overridden plan.
  - From Cursor-Innovation: Add `### UPDATED: python/larch/design/design_step5c.py`: extend all compose-side trailer regexes and sidecar rebuild to include `oversize_override: operator`, and add auto-compose tests mirroring `test_step5c_auto_compose_preserves_optional_trailers`.
  - From Cursor-Innovation: Extend the same-file `design_publish.py` work: add `oversize_override: operator` to `_OPTIONAL_TRAILER_RE` / `_is_trailer_region_line` handling and preserve it through `_splice_plan_provenance`; cover with `test_design_publish` splice/compose cases.
  - From Codex-Innovation: Teach _OPTIONAL_TRAILER_RE and _is_trailer_region_line() to treat oversize_override: operator as trailer text before the provenance splice
  - From Cursor-Pragmatic: Add oversize_override to _OPTIONAL_TRAILER_RE (and any trailer-region helper), include a publish splice round-trip test, and list design_publish.py in the firm file sweep.
  - From Cursor-Pragmatic: Promote design_step5c.py from MAY_UPDATE to UPDATED: extend both composition helpers for oversize_override: operator and add composition coverage.
  - From Cursor-Pragmatic: Make oversize_override: operator a recognized trailer in Step 5c auto-compose and publish provenance splicing, and add the planned composed-plan round-trip test on the actual auto-compose path.
  - From Cursor-Requirements: Extend _OPTIONAL_TRAILER_RE and _is_trailer_region_line for oversize_override: operator; keep splice behavior aligned with parse_optional_metadata; add/extend test_publish_splices_provenance (or equivalent) to assert the trailer survives publish-time provenance insertion.
  - From Codex-Requirements: Make design_step5c.py a firm update: include oversize_override: operator in trailer splitting, peeling, and sidecar value reconstruction, with a lifecycle test that an overridden plan.txt produces an overridden composed-plan.md.


### FINDING_3: Step 5c size check uses the wrong invocation
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: The Step 5c finalization size check is wired to the composed artifact and/or is missing required arguments, so it can reject a plan because of envelope lines or exit before seeing the intended plan file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Run publish finalization check-size against design_tmpdir/plan.txt (same artifact as Step 2b.5), or add a publish-site mode that excludes composed-only envelope lines from PLAN_LINES; keep firm-heading/surface/diff signals on the authoritative plan.txt body.
  - From Codex-Innovation: Invoke plan check-size with both --design-tmpdir "$DESIGN_TMPDIR" and --plan-file "$DESIGN_TMPDIR/composed-plan.md"


### FINDING_4: Gate B optional-trailer keys drift
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The Gate B optional-trailer snapshot/dedup path does not include the new size-related keys, so `oversize_override` and the emitted plan-size signals can drift between Step 2b.5 and Step 5c.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add FIRM_HEADINGS/SURFACES_TOUCHED/OVERSIZE_OVERRIDE to POSTPLAN_EMIT_KEYS and step2b5 direct-entry allowlists; add oversize_override to OPTIONAL_TRAILER_KEYS used by gate-b-dedup _trailer_map.
  - From Cursor-Innovation: Add `### UPDATED: python/larch/review/plan_review_common.py` (and `POSTPLAN_EMIT_KEYS` if passthrough is filtered) to include `oversize_override`, or import the canonical `OPTIONAL_KEYS` set from `_plan_quality_commands.py`.
  - From Cursor-Pragmatic: Add oversize_override to OPTIONAL_TRAILER_KEYS (and sync gate-b snapshot tests) alongside _plan_quality_commands OPTIONAL_KEYS.
  - From Cursor-Requirements: OPTIONAL_TRAILER_KEYS is a second source of truth beside OPTIONAL_KEYS; gate-b-dedup _trailer_map and .gate-b-optional-trailer-keys.values only snapshot diff_added/diff_deleted/mechanical_churn. Step 5c compose fallback reads that values file, so an override present only in plan metadata may be omitted from composed-plan.md after Gate B rewrites. Add oversize_override to plan_review_common.OPTIONAL_TRAILER_KEYS (or import shared OPTIONAL_KEYS); extend gate-b snapshot/dedup tests; document the key in approval-gates.md optional-trailer guard alongside the existing three keys.


### FINDING_5: Downstream metadata scanners stop early
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Other metadata consumers—difficulty parsing, bootstrap, and implement preflight—treat the new trailer as the end of the metadata block, so review_status/rounds_completed/difficulty can become invisible after publication or materialization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/larch/calibration/difficulty.py` to recognize `oversize_override: operator` in `_PLAN_TRAILER_LINE_RE` (and extend `test_difficulty.py` trailer-span cases).
  - From Cursor-Innovation: Add `### UPDATED: python/larch/state/bootstrap.py` (and the matching allowed-prefix scan in `python/larch/implement/preflight.py` if metadata is read there) so `oversize_override: operator` is treated like other optional size trailers.
  - From Codex-Pragmatic: Add oversize_override to the existing trailer allowlists, or centralize the trailer grammar, and cover an overridden plan through Gate B preservation plus /implement preflight metadata parsing.
  - From Codex-Requirements: Teach the publish trailer regex and the implement preflight allowed metadata scan to accept `oversize_override: operator`, and add a preflight test that review metadata remains visible when the override trailer is present.


### FINDING_6: Oversize refusal is misrouted
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Oversize publish refusals are indistinguishable from review-provenance refusals because `PUBLISH_REFUSE_REASON` is stripped or unkeyed, so `finalize-step5` sends oversized plans to the wrong recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update finalize-step5.md and insert the new SKILL.md special case before the review-provenance block, keyed on PUBLISH_REFUSE_REASON=oversize-no-override (and parse that KV from `.design-publish-result.env`).
  - From Codex-Innovation: Add PUBLISH_REFUSE_REASON to STEP5C_PUBLISH_RESULT_ALLOW_KEYS and emit it through the Step 5c status rows
  - From Cursor-Pragmatic: Add PUBLISH_REFUSE_REASON to STEP5C_PUBLISH_RESULT_ALLOW_KEYS and assert it in the finalization-guard test path.
  - From Cursor-Pragmatic: Both oversize refusal and review-provenance use VALIDATE_STATUS=defects-found with an empty VALIDATE_LOG_FILE. finalize-step5.md still maps that pattern only to review-provenance. Without an earlier PUBLISH_REFUSE_REASON=oversize-no-override branch, operators get Fix-and-retry/Cancel (re-run /design) instead of Decompose/Override/Cancel. Insert the oversize special case before review-provenance in SKILL.md and finalize-step5.md, keyed on PUBLISH_REFUSE_REASON=oversize-no-override.
  - From Cursor-Requirements: Both the new publish refusal and review-provenance refusal use return 4, VALIDATE_STATUS=defects-found, and an empty VALIDATE_LOG_FILE. finalize-step5.md routes that pattern to review-provenance recovery (re-run /design from Step 3), not Decompose/Override/Cancel. SKILL.md adds a PUBLISH_REFUSE_REASON special case, but finalize-step5.md is not in the plan file list. UPDATED: skills/design/references/finalize-step5.md—before the review-provenance branch, branch on PUBLISH_REFUSE_REASON=oversize-no-override to the Decompose/Override/Cancel flow; keep SKILL.md and finalize-step5.md in sync.
  - From Codex-Requirements: Add PUBLISH_REFUSE_REASON to STEP5C_PUBLISH_RESULT_ALLOW_KEYS, emit it in the Step 5c rows, and test the oversize refusal result-env path.


### FINDING_7: Step 5c recovery writes the wrong target file
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-Requirements
- **Severity**: major
- **Concern**: The oversize-refusal recovery branch updates `plan.txt` but re-runs against a pre-existing non-empty `composed-plan.md`, so the override does not affect the artifact being checked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Pass --plan-file "$DESIGN_TMPDIR/composed-plan.md" in the Step 5c Override branch, or delete/recompose that file before rerunning
  - From Codex-Pragmatic: In the Step 5c oversize refusal branch, write the override to composed-plan.md with --plan-file or delete and recompose composed-plan.md after updating plan.txt, then re-run design-step5c.sh; test the refusal-to-override retry.
  - From Codex-Requirements: In the Step 5c oversize refusal branch, write the override to composed-plan.md with --plan-file, or delete/recompose it after updating plan.txt; cover the retry path.
  - From Cursor-Requirements: Promote design_step5c.py from MAY_UPDATE to UPDATED: teach all compose/peel paths oversize_override: operator; in the Step 5c oversize recovery contract, run set-oversize-override against composed-plan.md or delete/force-recompose composed-plan.md from plan.txt before re-invoking design-step5c.sh; extend test_step5c_auto_compose_* and publish guard tests accordingly.


### FINDING_8: Split path lacks part issue data
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The oversize plan Split path still doesn't reliably emit per-part firm-heading inventories, acceptance criteria, or a pinned test for hard-trigger routing to decomposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Extend the decompose proposal schema and prepare output with per-piece firm-heading inventory and acceptance criteria, and add a focused prepare/decompose test; do not auto-generate reviewed plan blocks unless separately required.
  - From Cursor-Requirements: Add a focused test in python/tests/design/test_decompose.py or test_design_lifecycle.py: oversized fixture → SIZE_TRIGGER_FIRED/hard-trigger → Split-path prepare/annotate contracts (blocked-by edges, per-part inventory), or document a harness case if orchestrator-only.


### FINDING_1: Split path can emit non-implementable part issues
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The split/decompose path can still produce part issues that lack per-piece acceptance criteria, consistent scope matching, valid part-plan provenance, or serial blocked-by edges, so the filed pieces are not reliably implement-ready.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Add a fail-closed or deterministic fallback: derive per-piece acceptance from the parent plan (for example a scoped slice of Testing strategy / acceptance prose matched to the piece inventory), or return a prepare error when either bullet is missing after the aggregator contract update.
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/scripts/decompose-prompts/_common-tail.txt and extend the aggregate_partition merge schema in python/larch/design/decompose.py (lines 605-611) with - firm-headings: and - acceptance: bullets; keep decompose-panel.md in sync.
  - From Cursor-Pragmatic: Specify acceptance fallback in prepare_partition_issues (for example slice Testing strategy bullets for in-scope firm headings, or a bounded default tied to each piece scope) and pin it in python/tests/design/test_decompose.py.
  - From Cursor-Pragmatic: Reuse issue_wire.extract_scope_paths(..., include_optional=False) for the parent plan; match each heading to a piece when it equals or is under a scope path token; document the rule in prepare_partition_issues and test_decompose.py.
  - From Codex-Pragmatic: Add skills/design/scripts/decompose-prompts/_common-tail.txt as a firm UPDATED file and extend its required Piece schema with firm-headings and acceptance bullets, matching decompose.py and decompose-panel.md.
  - From Codex-Requirements: Update the Split path workflow to generate and review each per-part plan through the normal approval provenance path before marking parts implement-ready; tests should assert each filed part has a valid larch:plan block and unchanged preflight-readable metadata.
  - From Codex-Requirements: Treat partition order as execution order or topologically sort it, then emit adjacent blocked-by edges for every Part N to depend on Part N-1; keep extra panel dependencies only if they do not break the serial chain and pin the TSV in tests.


### FINDING_2: Oversize override is missing from the drafting contract
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The oversized-plan override contract is not fully exposed through the Step 2b drafter/prompt path, so operator override cannot be selected or recorded consistently.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Arch: Add python/larch/design/design_step2b.py to the UPDATED list and extend both prompt strings to mention `oversize_override: operator` as an allowed trailer before `diff_lines:`.
  - From Cursor-Requirements: Add `skills/design/SKILL.md` `postplan-rc12-split` handling (and any drafter-sidecar prompt text) to the same Split / Override / Cancel contract: on Override call `plan set-oversize-override` on `plan.txt`, then continue per `step2b5-rc-handling.md`.


### FINDING_3: Publish gating can fail open on stale or invalid composed plans
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: major
- **Concern**: The Step 5c publish flow can still finalize a stale or oversized composed plan when size checks fail or when plan.txt and composed-plan.md diverge.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Innovation: In publish_core, treat plan check-size subprocess non-zero exit or any PLAN_SIZE_STATUS other than a successful ok path as publish refusal (return 4 with PUBLISH_REFUSE_REASON=oversize-no-override or a distinct size-check-failed KV) before named-block write; only treat SIZE_TRIGGER_FIRED=false as pass when check-size succeeded
  - From Codex-Innovation: Make every Override path delete `composed-plan.md` or rewrite it immediately before continuing, not only the Step 5c recovery branch.
  - From Codex-Innovation: Remove the in-place composed-plan alternative, or make the retry path update `plan.txt` too and keep the authoritative guard/file pair aligned.


