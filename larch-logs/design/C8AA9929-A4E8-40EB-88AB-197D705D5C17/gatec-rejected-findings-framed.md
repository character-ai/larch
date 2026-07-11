---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_3

### FINDING_3: Keep fallback sidecar persistence in compute_coverage
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan requires plan-path-only sidecar persistence and unioning, but `touched_paths_since_baseline` has no plan context. Implementing those requirements there could thread plan state through the helper or persist unfiltered porcelain, expanding the API without changing coverage JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Move sidecar persistence into compute_coverage immediately after _firm_plan_paths and the plan_set intersection: on frozen fallback, intersect porcelain with plan_set, union with stored sidecar plan paths, write back the merged plan-only set, then build touched from that union. Keep touched_paths_since_baseline responsible only for raw committed/porcelain attribution and baseline mode selection.


### [Plan Review] FINDING_4

### FINDING_4: Retain sidecar paths across later live-base recomputation
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: If an initial frozen-fallback computation writes the sidecar, a later fetch or rebase may make the remote symbolic ref resolve. If recomputation then ignores the sidecar and porcelain is clean, touched paths can be cleared after dispatcher commit, causing stale-coverage validation to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify that once the fallback sidecar exists in the implement tmpdir, every later recompute in that run unions sidecar plan paths with porcelain (plus live committed paths when trustworthy), even if symbolic-ref later succeeds. Add a regression test: frozen fallback compute, symref recovery, clean porcelain, record_disposition still matches persisted coverage.


### [Plan Review] FINDING_5

### FINDING_5: Authenticate or safely initialize the fallback sidecar
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A trusted-tmpdir sidecar is path-safe but not necessarily author-authenticated. A pre-seeded sidecar containing all firm plan paths could cause the first frozen-fallback computation to mark unimplemented paths covered and bypass disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: On the first coverage computation, ignore and atomically replace any pre-existing sidecar using only current porcelain plan paths. On later recomputation, accept sidecar paths only when an existing larch-generated coverage artifact binds them to the prior fallback result; otherwise ignore them or fail closed. Add the pre-seeded-sidecar case to the mandated fallback tests.


### [Plan Review] FINDING_6

### FINDING_6: Support phase-specific porcelain in the regression harness
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The required post-commit fallback regression needs porcelain to be non-empty during the first coverage computation and clean during recomputation, but the current FakeRunner returns fixed status output for every git status call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify that FakeRunner accept per-call or phase-specific porcelain output (or allow swapping runners between calls) so the post-commit sidecar-retention test can model uncommitted plan paths first and an empty status on recomputation.


---LARCH-REJECTED-END---
