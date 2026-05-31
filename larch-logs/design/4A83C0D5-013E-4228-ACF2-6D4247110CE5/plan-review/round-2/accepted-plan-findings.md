### FINDING_1: ERROR breadcrumb only on cancel-title-filter path
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: After pause-load failure (`LOAD_OK=false`), the ERROR breadcrumb is scoped under the cancel-title-filter ROUTE bullet instead of a global pre-branch step. On proceed, clarify, or already-planned paths the orchestrator may skip re-emitting ERROR, diverging from current Step 0b sub-step 2.5-bis and the Edge cases section that warn on any fresh-run path after failed pause load.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Move ERROR re-emit to the same level as the BRAINSTORM_PREFIX pre-branch bullet (before any ROUTE branch); keep cancel-title-filter bullet exit-only
  - From Cursor-Edge: In SKILL.md: immediately after reading .design-route-result.env, if ERROR is non-empty print it once as a warning breadcrumb before the ROUTE branch (not only on cancel-title-filter)


### FINDING_2: Harness misses env-before-rename ordering
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: FINDING_13 harness checks env refresh before `write-run-params` but not before rename. Reordering to rename → env → write-run-params could still pass the harness while breaking Decision 1 `ISSUE_NUMBER` binding before pause-save.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add line-order assert in test-design-structure.sh: write-design-current-env.sh precedes tracking-issue-write.sh rename in design-init-runparams.sh


### FINDING_3: No contract for design-route.sh non-zero exits
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan does not specify orchestrator handling for `design-route.sh` non-zero exits. Exit 2 (argv/body-file) or exit 1 (e.g. `set -e` after `phase_driver_write_result_env` failure) can leave `ROUTE` unset and allow fallthrough past gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Specify SKILL.md handling: on design-route exit 2 print config error and exit 1; treat unexpected non-zero like run-step3-review exit 2 (do not branch on empty ROUTE)


### FINDING_4: Verdict step 4 plan-block detection unspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Verdict step 4 does not define how to detect a `larch:plan` block in `issue-body.txt`. A loose substring grep could mis-route (false already-planned) or miss valid blocks, diverging from `plan-block-read.sh` marker rules used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin detection to the same start/end marker regexes as scripts/plan-block-read.sh (lines 20-21) on the body file; treat only well-formed single start+end pairs as present (no extra gh fetch)

---

**Merge notes (optional):** Input FINDING_1 and FINDING_2 were merged into aggregator FINDING_1 (same behavioral risk: ERROR re-emit placement). Input FINDING_3–5 map to aggregator FINDING_2–4 unchanged. No `[OUT_OF_SCOPE]` inputs; empty-merge attestation not used.

