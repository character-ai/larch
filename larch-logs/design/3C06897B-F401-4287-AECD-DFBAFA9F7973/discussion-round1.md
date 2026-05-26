## Decision 1: PREFLIGHT_TMPDIR delivery mechanism
- **Question**: How should phase_plan_materialize receive PREFLIGHT_TMPDIR (where plan-from-issue.txt lives)?
- **Resolution**: Add explicit `--preflight-tmpdir <path>` argv flag to implement-bootstrap.sh. Required when `--up-to-phase` is `plan`, `coder`, or `all`; missing flag → `die_usage`. SKILL.md Step 0 invocation appends `--preflight-tmpdir "$PREFLIGHT_TMPDIR"`.
- **Source**: user

## Decision 2: Test coverage scope
- **Question**: What test cases beyond B6/B7/green-path BRANCH_NAME must test-implement-bootstrap.sh cover?
- **Resolution**: Add B8 (forked_target=true → no branch creation, snapshot-untracked still runs), B9 (IS_USER_BRANCH=true → no branch creation), plus slug-edge-case assertions within the existing green-path B-case (uppercase title, special chars, 40+ char title — three assertions on derived BRANCH_NAME).
- **Source**: user

## Decision 3: snapshot-untracked placement
- **Question**: Where exactly does snapshot-untracked.sh fit in phase_plan_materialize?
- **Resolution**: First operation inside phase_plan_materialize, before #10 gh-issue-view compose. Best-effort (always exits 0), so failure cannot bail the phase.
- **Source**: user

## Decision 4: Scope boundaries (in-scope vs out-of-scope)
- **Question**: What is in-scope vs out-of-scope per the issue body?
- **Resolution**: **In-scope**: `phase_plan_materialize` function body, replace fenced Bash blocks in SKILL.md covering calls #10–#16 + snapshot-untracked, add B6/B7/B8/B9 + slug-edge-case test coverage, update `scripts/implement-bootstrap.md` phase-mapping + bail-reason enum. **Out-of-scope**: Phase 4 (phase_coder_select waterfall implementation, #2738), structural pin, aggressive SKILL.md collapse beyond replacing #10–#16 blocks.
- **Source**: codebase (issue body)

## Decision 5: Hard constraints
- **Question**: What invariants must NOT break?
- **Resolution**: (a) `should_run_post_tracking_phase` guard (Phase 2 F7 finding) must remain intact — phase_plan_materialize bail-reason settings must not bypass this guard. (b) `tracking-issue-summary.sh upsert-summary --marker "<!-- larch:plan v1 runid=$RUN_ID -->"` contract preserved. (c) Slug derivation `tr | sed | cut` pipeline byte-identical to current SKILL.md. (d) `POST_PLAN_WORKFLOW_PATH=HARD` binding via `timing-ledger.sh workflow-path "HARD"` matches current SKILL.md #3 sub-section.
- **Source**: codebase

## Decision 6: Workflow-path binding
- **Question**: Hard-coded HARD or derived from plan.txt?
- **Resolution**: Hard-coded HARD per issue body and current SKILL.md #3 ("Step 5's `run-step5-review.sh` does not branch on this key"). No diff-lines-based selection.
- **Source**: codebase (issue body confirms intent)
