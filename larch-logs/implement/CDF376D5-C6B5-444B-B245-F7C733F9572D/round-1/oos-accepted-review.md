### OOS_1: [OUT_OF_SCOPE] Consumption without `repo_root` skips live snapshot validation
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: When `repo_root` is omitted, note consumption can succeed on HEAD equality without validating the covered fingerprint or snapshot against the live diff. This permits same-HEAD notes with missing, symlinked, stale, or mismatched snapshots to be accepted, including through final-report and legacy-reader paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Temporary coverage files are vulnerable to symlink planting
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Predictable temporary coverage paths are opened with `write_text` before replacement. A same-user attacker could plant a symlink and redirect the write outside the repository. Temporary creation should use exclusive, no-follow semantics and revalidate containment and file type before use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
