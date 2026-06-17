### OOS_1: [OUT_OF_SCOPE] `_append_voter1_failure` reads entire voter output before slicing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On voter failure with a very large output file, `_append_voter1_failure` calls `read_bytes()[:200]` (and similar `[:500]` paths), allocating the full file in memory despite needing only a small preview.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use open('rb').read(200) or a shared bounded-read helper


### OOS_2: [OUT_OF_SCOPE] Judge-error path uses unbounded `read_bytes()` for voter preview
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When ≥80% of judges error, `voting.py` loads `voter_path.read_bytes()[:200]` for diagnostics. A huge voter file can trigger the same unbounded-read memory spike this PR fixes elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Switch to bounded open().read(200) consistent with _make_bounded_context_copy


