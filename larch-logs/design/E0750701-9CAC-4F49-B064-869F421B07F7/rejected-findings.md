### [Plan Review] FINDING_3

### FINDING_3: Detached-marker age must be pinned to a fixed field
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Orphan-timeout logic is underspecified unless both Step 3 and Step 5 read a stable age field from the detached-marker KV file; relying on mtime or an incomplete key set can drift across rewrite/reattach and fire early or late.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror Step 3 _step3_review_write_detached_marker fields in the Step 5 helper and document that Python reads DETACHED_AT_EPOCH first with mtime fallback in both plan_review.py and review_and_fix.py.
  - From Cursor-Pragmatic: Pin orphan checks to parse `DETACHED_AT_EPOCH=` from the detached-marker KV file (fallback to mtime only when the field is absent); require Step 5’s detached-marker writer to emit the same KV shape as Step 3 (`PID`, `SIGNAL`, `STDOUT_FILE`, `DETACHED_AT_EPOCH`).
  - From Cursor-Requirements: Specify the Step 5 detached-marker write/read contract to match Step 3 (`PID`, `SIGNAL`, `STDOUT_FILE`, `DETACHED_AT_EPOCH`), have Python orphan checks prefer `DETACHED_AT_EPOCH`, and add a harness assertion for the field.


