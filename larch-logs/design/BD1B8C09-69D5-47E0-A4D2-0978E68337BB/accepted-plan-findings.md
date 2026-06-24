### FINDING_1: _step5_resume_commit_phase must fail-closed on NEXT_ACTION=stall when commit-route rc is 0
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `_step5_resume_commit_phase` lacks an explicit `NEXT_ACTION=stall` fail-closed return when the commit-route process rc is 0. After refactor, `commit_route` can return 0 with `NEXT_ACTION=stall` (mirroring `step8_oos_checkpoint`). If success is mapped only to `commit_rc==0`, the phase returns `None` and `step5_resume_main` proceeds to review-and-fix step5 after a seeded commit-phase stall. That violates the plan and breaks Python parity with the shell wrapper, which exits before step5 on `NEXT_ACTION=stall`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify that _step5_resume_commit_phase (and step5_resume_main) treat NEXT_ACTION=stall as a terminal commit-phase failure: relay commit KVs and NEXT_ACTION=stall, return a non-zero exit (e.g. 1) without calling review-and-fix step5, even when the shared commit-route helper returned process rc 0. Extend test_step5_resume_* to assert NEXT_ACTION=stall, no step5 relaunch, and non-zero step5_resume_main rc.


### FINDING_2: step-5-resume.sh commit-route delegation omits errexit-safe stdout capture
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned commit-route delegation replaces the inline commit-fixes block with a bare `implement commit-route` call but does not carry forward the `set +e` / capture / `set -e` guard under `set -euo pipefail`. On a non-zero commit-route return without `NEXT_ACTION` (stall-seed failure, usage error, invalid envelope), errexit can abort the wrapper before stdout is captured or `NEXT_ACTION`/`COMMIT_OUTCOME` are relayed, so the orchestrator cannot reach lacks-envelope branch 3 and may mis-route to generic preflight failure. The structure harness drops the pin at `scripts/test-implement-structure.sh:369` without adding an errexit-safe commit-route replacement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit step-5-resume.sh requirement: wrap commit-route invocation in set +e, capture commit_output and commit_rc, then set -e before parsing NEXT_ACTION; relay stdout on all paths. Add a matching scripts/test-implement-structure.sh pin for that capture block (or forbid bare unguarded commit-route substitution).
  - From Cursor-Pragmatic: In step-5-resume.sh require the same set +e commit_output capture / commit_rc / set -e guard around implement commit-route; parse NEXT_ACTION from captured stdout. In scripts/test-implement-structure.sh replace the retired commit-fixes errexit needle with a pin requiring that guard around commit-route.
  - From Cursor-Pragmatic: Wrap `implement commit-route` in the same errexit-safe capture pattern; parse `NEXT_ACTION` from captured stdout. Update `scripts/test-implement-structure.sh` to pin that guard (replacing the obsolete line-369 `commit-fixes` needle).
  - From Cursor-Requirements: Add set +e around commit-route capture in step-5-resume.sh (mirror today's commit-fixes block). Migrate scripts/test-implement-structure.sh:369 to require the same guard around implement commit-route --site step5-resume-handoff when dropping the commit-fixes errexit pin.


### FINDING_3: Self-review and Step 7 invalid-envelope paths omit Step 18 stall teardown routing
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Planned self-review and Step 7 invalid commit-route envelope handling says log to Warnings and do not proceed, but unlike resume-handoff lacks-envelope branch 3 it never sets `STALL_TRACKING=true` or skips to Step 18. On seed failure or malformed stdout (no `NEXT_ACTION`), foreground fences can halt mid-Step-5/7 without the teardown/stall-recovery path that `COMMIT_OUTCOME` failures and resume-handoff invalid envelopes use, stranding the session without Step 18 cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Align self-review and Step 7 invalid-envelope handling with resume branch 3: after logging Warnings, set STALL_TRACKING=true with the site stall_step, skip to Step 18 (durable bail may be absent when seed failed), and add matching structure-harness pins so invalid-envelope prose is not only do-not-proceed.
  - From Cursor-Pragmatic: Align self-review and Step 7 invalid-envelope handling with resume branch 3: after logging, set prompt-side STALL_TRACKING/STALL_STEP when durable seed is absent, then skip to Step 18; do not fall through or end the turn silently.
  - From Cursor-Pragmatic: Mirror resume branch 3 on self-review and Step 7: invalid envelope → log, set `STALL_TRACKING` / `STALL_STEP` when durable seed is absent, skip to Step 18.
  - From Cursor-Requirements: Align self-review and Step 7 invalid-envelope prose with resume branch 3: log Warnings, set STALL_TRACKING=true and site-appropriate STALL_STEP, skip to Step 18. Add matching structure-harness pins alongside the planned invalid-envelope fail-closed needles.


### FINDING_4: Resume-handoff porcelain failure may omit Tool Failures log before NEXT_ACTION=stall
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Moving the whole commit-failure tree into commit-route includes execution-issues logging. The plan's ok/noop porcelain branch seeds durable stall and emits `NEXT_ACTION=stall`, but only the `COMMIT_OUTCOME` failure branch calls `_commit_route_log_failure`; porcelain tests assert only state. A dirty/probe-failed resume handoff can reach Step 18 with durable state but no committed failure log.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Route the resume-handoff porcelain failure through the same bounded diagnostic and _commit_route_log_failure --redact path before emitting NEXT_ACTION=stall, and pin that in the porcelain failure tests.
```

**Merge notes**

- **FINDING_3/5/7** and the errexit portion of **FINDING_6** → **FINDING_2** (same behavioral risk: wrapper abort before envelope relay).
- **FINDING_4/6/8** → **FINDING_3** (same behavioral risk: missing Step 18 on invalid envelope at self-review/Step 7).
- **FINDING_2** (Arch) and **FINDING_9** (Codex-Generic) stay separate: different code paths and fixes (Python stall return vs porcelain logging).
- No `[OUT_OF_SCOPE]` tags in inputs; none emitted.
- Input items marked “not re-raised” in **FINDING_6** were excluded as already covered by the plan.


