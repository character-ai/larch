### FINDING_2: Step 5c publish fence lacks pause-check
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-pause-protocol-safety
- **Severity**: important
- **Concern**: The surviving Step 5c `design-publish.sh` source-env bash fence is brought into structure extraction but still lacks the canonical pause-check before publishing work. A pause requested before publish can be ignored until after plan write, issue rename, and log publishing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the canonical pause-check immediately after the source-env line and before set +e/design-publish.sh, and have the updated structure test cover this indented fence.
  - From Codex-Innovation: Add the canonical design-pause-save check immediately after the source-env line in the Step 5c design-publish.sh fence, before set +e / _publish_out, and keep the gated step-5c write after PLAN_WRITE_OK=true
  - From Codex-dyn-pause-protocol-safety: Add the canonical .pause-requested design-pause-save.sh line immediately after the Step 5c source-env line and before set +e / design-publish.sh, and make the widened pause-check assertion cover indented fences


### FINDING_4: Deferring step-1d.5 until Step 2a breaks intermediate and terminal routes
- **Reviewer(s)**: Cursor-Innovation, Codex-dyn-pause-protocol-safety
- **Severity**: important
- **Concern**: Moving `step-1d.5` completion from the Step 1d.5 success boundary to Step 2a leaves routes that pause or exit before Step 2a with `step-1d.5` missing. Those snapshots can resume by replaying brainstorm/Q&A work instead of continuing or terminating correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep the existing Step 1d.5 success-boundary write (one line, no timing prelude); fold only `step-1c`, `step-1d`, `step-1d.7`, and `step-1e`. Drop `step-1d.5` from the Step 2a folded batch and from the `step-1d.5 → Step 2a entry` row in `assert_folded_sentinel_writes`
  - From Codex-dyn-pause-protocol-safety: Keep a boundary-local step-1d.5 write for the Step 0b already-planned Q&A-only terminal branch, or explicitly write it before that branch runs the Final summary block


### FINDING_5: Architecture diagram skipped marker must be branch-specific and asserted
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-test-claim-mapping
- **Severity**: important
- **Concern**: The `architecture-diagram.skipped` marker must not be written unguarded at a shared Step 3b completion/finalize boundary used by sanitizer rejection, generation failure, and success paths. Otherwise Step 5c can treat failures as intentional non-architectural skips and clear Architecture content; tests also need to assert the intended branch-local placement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep architecture-diagram.skipped branch-local to the non-architectural path, or make the boundary write it only under an explicit skip-only flag; add the structure assertion against that branch-specific placement rather than the whole shared boundary.
  - From Cursor-dyn-test-claim-mapping: Co-located skip write could move back to orchestrator prose while structure tests still pass Extend assert_step3b_finalize_boundary (or assert_folded) to require architecture-diagram.skipped in the same bash fence as ACTION=FINALIZE before step-3b


### FINDING_6: Step-local sentinel assertion will conflict with folded host fences
- **Reviewer(s)**: Cursor-dyn-sentinel-chain
- **Severity**: important
- **Concern**: `assert_step_completion_sentinels` still expects each `.completed/step-*` token inside that step’s own anchor slice, but the plan intentionally folds many sentinels into foreign host fences. The test can fail valid folded placements or encourage weakening the folded-order checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sentinel-chain: Update `assert_step_completion_sentinels` to skip host-absorbed steps (delegate to `assert_folded_sentinel_writes`) or resolve tokens via the plan’s host map; keep step-local grep only for steps that still self-write (5b, 3b, Gate-B-bypass triple writes, postplan `step-2b`/`step-2b.5`, etc.)


### FINDING_7: No-brainstorm Step 1d path can bypass folded step-1c/step-1d writes
- **Reviewer(s)**: Codex-dyn-sentinel-chain
- **Severity**: important
- **Concern**: The no-brainstorm route still sends Step 1d directly to Step 1d.7, while the plan folds `step-1c` and `step-1d` only into the Step 1d.5 prelude and deletes the Step 1d.7 prelude. That route can reach Step 2a with prior sentinels missing and resume too far back.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sentinel-chain: Add step-1c and step-1d as idempotent folded writes in the Step 2a entry fence too, or change the Step 1d no-brainstorm route to always pass through the retained Step 1d.5 skip/prelude host before Step 1d.7.


### FINDING_8: Step 2b folded sentinel test omits step-2a
- **Reviewer(s)**: Cursor-dyn-test-claim-mapping, Codex-dyn-test-claim-mapping
- **Severity**: important
- **Concern**: The plan says Step 2b idempotently writes both `step-2a` and `step-2a.5`, but the proposed `assert_folded_sentinel_writes` mapping covers only `step-2a.5`. An implementation could omit the `step-2a` repair and still pass tests, causing resume routing to fall back by registry order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-claim-mapping: Add step-2a → Step 2b prelude (before pause-check) to the assert_folded_sentinel_writes host table alongside step-2a.5
  - From Codex-dyn-test-claim-mapping: Add step-2a to the Step 2b prelude assertion alongside step-2a.5, before pause-check.


### FINDING_10: Step 0c pause-check coverage is missing
- **Reviewer(s)**: Cursor-dyn-test-claim-mapping
- **Severity**: latent
- **Concern**: Step 0c gains a bash fence with a pause-check, but the existing pause-check structure assertion starts at Step 1c. A regression in the new Step 0c fence would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-claim-mapping: Pause-check regression in the new Step 0c fence would not be caught Extend assert_bash_fences_have_pause_check (or add a Step 0c-specific guard) to cover the Step 0c fence


### FINDING_11: HARD zero-sketch degraded fence lacks canonical pause-check
- **Reviewer(s)**: Cursor-dyn-pause-protocol-safety
- **Severity**: important
- **Concern**: The proposed HARD zero-sketch degraded bash fence writes `step-2a`/`step-2a.5` but does not run the canonical pause-check. A pause request on the 2a→2b short-circuit can be ignored until a later boundary, and widened structure tests may flag the fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-pause-protocol-safety: Add the standard two-line prelude (source-env then pause-check) to the zero-sketch fence spec; place step-2a/step-2a.5 writes after source-env and before pause-check; extend `assert_folded_sentinel_writes` mapping line 61 to require pause-check ordering like the other host fences

