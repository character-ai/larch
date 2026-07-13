---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Live projection shape is underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Baseline-active runs do not define how `Finding` optional fields map to generic versus symbol-metric projections, allowing partial or inconsistent identities.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define and test live projection rules: generic only when both qualified_symbol and metric are absent; symbol-metric only when both are present; exit 2 when exactly one is set. Apply the pairing check only on baseline-active paths so scan-only behavior stays unchanged
  - From Cursor-Requirements: Spell out the positive mapping in Approach/engine bullets: generic projection only when both optional fields are absent; symbol-metric only when both are present; any partial presence is exit 2 before comparison. Require the same homogeneous shape for every live row and every baseline row in a run.


### [Plan Review] FINDING_2

### FINDING_2: Canonical baseline JSON serialization is unspecified
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Exact read-back byte validation is not deterministic without a pinned serializer, ordering, field order, indentation, and newline contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin serialization to sorted projected rows plus json.dumps(ordered, indent=2) + "\n", matching existing lint serialize_baseline helpers; test the exact bytes
  - From Cursor-Requirements: Add one serialization contract: sort rows by the projected identity tuple, emit json.dumps(rows, indent=2) + "\n" with fixed per-schema field order, and compare read-back text byte-for-byte to that serializer output.


### [Plan Review] FINDING_3

### FINDING_3: Mixed-schema baseline arrays are not rejected
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Per-row validation can accept a baseline containing both generic and symbol-metric rows, leaving comparison and write behavior undefined.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After per-row validation, require all baseline rows share one projection kind; exit `2` on mixed arrays; add an explicit mixed-array test.
  - From Cursor-Requirements: Spell out the positive mapping in Approach/engine bullets: generic projection only when both optional fields are absent; symbol-metric only when both are present; any partial presence is exit 2 before comparison. Require the same homogeneous shape for every live row and every baseline row in a run.


### [Plan Review] FINDING_4

### FINDING_4: Strict-stale precedence with new findings is undefined
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The plan does not define whether strict-stale exit `2` takes precedence when new or regressed findings also produce exit `1`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Document one precedence rule in Approach item 4 and Failure modes: when strict_stale is active and any in-scope stale row exists, return exit 2 even if new or regressed findings also exist; otherwise stale warnings alone keep exit 1 when findings are present.


### [Plan Review] FINDING_5

### FINDING_5: Trusted baseline I/O failures may escape exit-2 handling
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: `OSError` and `ValueError` from trusted baseline reads, writes, or read-back may bypass `ScanError` conversion and violate the promised exit-code and buffered-output contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Wrap baseline read, write, and read-back calls in a narrow converter to ScanError (or a single outer except) so every trusted I/O failure surfaces on stderr and returns EXIT_ERROR without bypassing the buffered-output contract.


---LARCH-REJECTED-END---
