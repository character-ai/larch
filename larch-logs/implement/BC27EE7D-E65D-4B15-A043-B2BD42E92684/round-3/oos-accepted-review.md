### OOS_1: [OUT_OF_SCOPE] Unbounded memory read in `_make_bounded_context_copy`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_make_bounded_context_copy` uses `Path(src).read_bytes()[:max_bytes]`, which reads the entire source file into memory before truncating. A pathological multi-GB diff/plan can spike memory even though output is capped at 200k/60k bytes. Same pattern existed in the retired bash helper; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Stream-copy with a byte cap (`open` + `read(max_bytes)` or `shutil.copyfileobj` with a limit).


