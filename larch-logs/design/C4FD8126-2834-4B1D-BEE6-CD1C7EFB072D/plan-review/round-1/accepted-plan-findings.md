### FINDING_1: Gate codex-step2-out paths and mkdir to CODER=codex only
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: A planned change would set `STEP2_OUT_DIR` after `TMPDIR_ARG` canonicalization and retarget `MANIFEST_PATH`, `QA_PENDING_PATH`, and `TRANSCRIPT_PATH` under `codex-step2-out` for every external implementer (Codex and Cursor), not only Codex. Cursor Step 2 would then write into a Codex-named subdirectory without needing sandbox narrowing. The same plan may run `mkdir` before the `claude` early-exit (line 176) and before cursor-unhealthy fallbacks, so even paths that never launch an external implementer get the subdir layout—scope creep beyond narrowing Codex `--add-dir` and a likely break for Cursor stub tests (e.g. test 3e) unless every Cursor harness path is rewritten.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Scope mkdir and the three path variables to CODER=codex only (e.g. set defaults in the shared block; override inside the codex) branch); leave Cursor paths at $TMPDIR_ARG/manifest.json etc.
  - From Cursor-Edge: Gate STEP2_OUT_DIR/mkdir and the three Codex output paths on CODER=codex only; leave Cursor paths at $TMPDIR_ARG/... and place mkdir after the claude/cursor-unhealthy early returns


### FINDING_2: Align codex dispatch tests with codex-step2-out manifest path
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: If `step2-implement.sh` expects manifests under `$TMP/codex-step2-out/manifest.json`, the plan only updates `STEP2_MANIFEST_PATH` for tests 17a–17c. Roughly fifteen other Codex dispatch tests still set `STEP2_MANIFEST_PATH` to `$TMP/manifest.json` while stubs write the wrong file, causing manifest-missing or wrong `STATUS` (e.g. 12a/12b, 13, 16, 18, M1, M2, M12, M16–M19, 25).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Set STEP2_MANIFEST_PATH to $TMP/codex-step2-out/manifest.json (or derive from dispatcher layout) for every codex stub invocation; keep 17a–17c META path updates already listed

---

**Merge notes**: FINDING_1 and FINDING_2 from the raw input were merged (same behavioral risk in `step2-implement.sh` 152–260, different fixes). FINDING_3 stays separate (test harness in `test-step2-dispatch.sh`). No `[OUT_OF_SCOPE]` tags; no empty-merge attestation.

