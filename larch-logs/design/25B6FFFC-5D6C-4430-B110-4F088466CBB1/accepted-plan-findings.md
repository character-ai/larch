### FINDING_1: Harden mav-apply post-coder-head creation
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `review_and_fix.py` mav-apply mode still creates `post-coder-head.txt` through an unlink followed by bare `_write_text`, bypassing the exclusive no-follow trusted-write contract, final-path revalidation, and permission hardening used by `round_runner.py`. A same-UID symlink or partial replacement can therefore poison the diff base and staging inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add review_and_fix.py to the firm write hardening list and route mav-apply post-coder-head creation through the same snapshot trusted-write helper used in round_runner.py, including chmod 0444 hardening.
  - From Cursor-Pragmatic: A same-UID symlink or partial file in the round directory can redirect or poison the mav-apply post-coder head before later trusted validation runs, so diff-base and stage-path collection can diverge from the validated snapshot contract. Add review_and_fix.py to the post-coder-head write hardening step: route mav-apply creation through the same snapshot trusted-write helper used in round_runner.py, with final-path revalidation and permission hardening; extend test_review_and_fix.py to cover the mav-apply writer.


### FINDING_2: Make snapshot validation the sole cleanup mode authority
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Cleanup paths still re-derive snapshot mode through the legacy `_snapshot_mode` heuristic. Tracked-only directories can be classified as full before patch inventory validation, allowing validated snapshots with incomplete patch data to enter full cleanup and stale-HEAD handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make the complete validator the sole mode authority: replace _snapshot_mode classification with validator output and pass the validated mode into cleanup/restoration (or have cleanup call only validator-backed APIs). Update coder_runner stale-HEAD gating to use the same validated snapshot contract.


### FINDING_3: Require live validation before recording disposition
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: `record_disposition` and its CLI action can load or fingerprint persisted coverage without `repo_root` or live recomputation. Stale, partial, symlinked, unsafe, or mismatched coverage can therefore be frozen into `scope-disposition.json` before downstream consumers validate it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add repo_root (or a pre-validated live coverage object) to record_disposition, recompute/validate coverage before persisting disposition, and fail closed when artifacts are partial, unsafe, or live-mismatched.
  - From Cursor-Innovation: Add repo_root to record_disposition (and its CLI action), load coverage only through the hardened live-validating API, and fail closed when recompute or containment checks fail


### FINDING_4: Remove unvalidated disposition wrapper reads
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: `disposition_link_kind` and `disposition_deferred_inventory` still permit legacy or repeated raw reads without a validated `repo_root` and live artifact check. PR-body and finalization paths can consequently treat invalid disposition as `closes`, empty inventory, or otherwise render data that was replaced after an earlier validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make the trusted loaders the only read path inside these helpers (require repo_root or fail closed), raise on invalid present artifacts, and keep absent-only None semantics for optional flows.
  - From Codex-Arch: Change the wrapper APIs to require or derive a validated repository root, route them through the live-validating coverage/disposition loader, and update all callers to propagate failure instead of defaulting to empty inventory or `closes`.
  - From Codex-Innovation: Return the validated coverage/disposition result from the hardened validation call and pass it through rendering and finalization, or require these helpers to receive repo_root and perform the same trusted live validation themselves.


### FINDING_5: Harden scope-disposition artifact writes
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: `record_disposition` publishes `scope-disposition.json` through default atomic writing to a predictable destination. A same-UID symlink at that path can redirect the write outside `tmpdir`, while later readers may treat the invalid artifact as absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the plan's trusted-write contract to disposition artifacts: random exclusive no-follow temp creation, final-path revalidation, and safe temp cleanup for record_disposition and any other scope-disposition writers


### FINDING_6: Fail closed on invalid disposition in final-report summaries
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: `_plan_coverage_summary_line` can still receive `None` from `load_disposition` for malformed, symlinked, or fingerprint-invalid `scope-disposition.json`, causing final reports to render `disposition: none` and mask corruption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Apply the same three-state disposition contract in final_report: wholly absent stays none, valid-present renders as today, invalid-present raises ShipError or returns an explicit bounded failure instead of masking corruption


### FINDING_7: Validate disposition before finalize teardown gating
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Finalize teardown selects the done-rename branch through `disposition_link_kind` before resolving `repo_root`. This ordering can leave the partial-disposition gate on legacy unvalidated loading rather than the required live-validation contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reorder finalize teardown (or add an explicit pre-check): resolve repo_root first, run trusted disposition validation, then decide whether proceed-partial suppresses the done rename


### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/snapshot.py:672-691
- **Concern**: [SCOPE-REDUCTION] Preserve safe reuse of an existing snapshot root instead of requiring every root creation to be exclusive. Scenario: `_write_pre_coder_snapshot` currently clears and rewrites the deterministic per-round directory. After an interrupted attempt leaves a valid directory, literal exclusive root creation makes the next attempt fail before it can replace stale or partial artifacts, breaking existing recovery and requiring manual cleanup.
- **Proposed resolution**: Create the directory exclusively only when absent. When it already exists, validate the directory and every ancestor without following symlinks, then safely clear and republish the snapshot artifacts.


