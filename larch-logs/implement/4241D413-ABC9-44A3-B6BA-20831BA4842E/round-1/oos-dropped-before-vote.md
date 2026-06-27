### OOS_1: [OUT_OF_SCOPE] architecture: fence-shape harness does not scan bootstrap-recovery.md resume fence
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-prompt-relocation
- **Severity**: latent
- **Concern**: `scripts/test-implement-fence-shape.sh` scans `SKILL.md` only; the relocated `--mode resume` old-shape fence in `bootstrap-recovery.md` has no mechanical old-shape validation. Old-shape guard/awk drift in the reference would not fail `make test-implement-fence-shape`. Structure harness only pins substring presence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend the harness to scan `bootstrap-recovery.md` for the resume fence, or document the intentional exemption explicitly in `test-implement-fence-shape.md`.
  - From cursor-specialist-testing: Same pattern as `step18-cleanup.md`; acceptable unless you want reference old-shape coverage later.
  - From dyn-dyn-prompt-relocation: The harness still scans only `skills/implement/SKILL.md`, so the relocated old-shape `--mode resume` fence in `bootstrap-recovery.md` has no mechanical old-shape validation. Drift there would not fail `make test-implement-fence-shape`.

### OOS_2: [OUT_OF_SCOPE] code-quality: SKILL.md:138 prelude doc hygiene (testing duplicate)
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The Bash block prelude still says "dirty-tree recovery resume may keep the source guard" in `SKILL.md`, but that resume fence now lives only in `bootstrap-recovery.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Repoint the prelude to note the resume fence moved to the reference (optional doc hygiene).

### OOS_3: [OUT_OF_SCOPE] risk-integration: bootstrap-recovery.md resume-tail parity note (testing duplicate)
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The old dirty-recovery table row prose about preserving `$IMPLEMENT_TMPDIR` and resume-tail behavior (degraded gate / `1.r` rerun) was not copied into the reference; only partial equivalents remain (`absorbed continue tail` in `SKILL.md` still covers degraded/1.r). Low runtime risk; behavior is in `python/bootstrap.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a short preserve-tmpdir / resume-tail note to the reference if you want parity with the removed table row (low runtime risk; behavior is in `python/bootstrap.py`).

### OOS_4: [OUT_OF_SCOPE] architecture: anti-halt harness edit-in-sync note omits self-review.md
- **Reviewer(s)**: dyn-dyn-prompt-relocation
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-implement-relevant-checks-anti-halt.md:1088` edit-in-sync note still names only `skills/implement/SKILL.md` even though the harness now also depends on `skills/implement/references/self-review.md`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] code-quality: self-review.md step numbering gap
- **Reviewer(s)**: dyn-dyn-prompt-relocation
- **Severity**: nit
- **Concern**: `skills/implement/references/self-review.md:27-49` step numbering still jumps from 7 to 9 (pre-existing); harmless but slightly confusing in the relocated reference.
- **Suggested revisions (informational for voters; coder decides)**:

