### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality — redundant `[[ -d ]]` checks before canonicalization
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Redundant `[[ -d ]]` checks precede `_codex_canonical_existing_dir`, which already requires a directory. Extra branches to maintain when validation evolves; no functional bug today. Collapse to a single canonicalization call per parent with mapped exit-2 diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `SESSION_TMPDIR` not required under canonical `IMPLEMENT_TMPDIR`
- **Reviewer(s)**: dyn-cursor-claude-path-isolation-output.txt
- **Severity**: latent
- **Concern**: When `IMPLEMENT_TMPDIR` is set, argv validation only rejects `SESSION_TMPDIR` canonical-equal to the tmpdir root; it does not require `SESSION_TMPDIR` to lie under canonical `IMPLEMENT_TMPDIR`, unlike `launch-review.sh`’s `--codex-add-dir` containment. A caller can set `IMPLEMENT_TMPDIR` to one directory while manifest/qa/transcript parents resolve elsewhere (e.g. `test-codex-implementer.sh:289-325` uses `IMPLEMENT_TMPDIR="$SCRATCH/implement-tmpdir"` with outputs under `$SCRATCH/codex-step2-out/`), and Codex still receives `--add-dir` on that outside path. Production `step2-implement.sh:260-265` keeps `codex-step2-out/` under `$TMPDIR_ARG` (exported as `IMPLEMENT_TMPDIR`), so the live dispatcher path is consistent; the gap is defense-in-depth and diverges from `SECURITY.md` / `launch-codex-implement.md` wording that the grant is under `$IMPLEMENT_TMPDIR/codex-step2-out/`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cursor-claude-path-isolation-output.txt: After the root-equality check, require `SESSION_TMPDIR` to be under `_canon_implement_tmpdir` (reuse `_codex_under_root` from `launch-review.sh`); move harness `STEP2_OUT_DIR` under `IMPLEMENT_TMPDIR_FIXTURE/codex-step2-out/` wherever `IMPLEMENT_TMPDIR` is exported.

---

**Subsumed (no `### FINDING_N:` blocks):** Security confirmations (step2 retargeting, launcher canonicalization, step-7a flush, SECURITY.md accuracy, harness 11c–11e, residual repo grant by design), plan-fidelity requirement traceability for commit `0edbc847d`, and dyn-cursor scout path-trace (no defect). **Not merged across scope:** FINDING_4 (OOS nit) vs FINDING_6 (in-scope important) — same assertion shape, different scope tags per aggregator rules.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality — repeated `codex-step2-out` string literal
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `codex-step2-out` is a repeated string literal across production and harness code. Renaming the subdir for future parity requires a wide grep; `step-7a.sh` is easy to miss and causes silent transcript log loss. Introduce one readonly subdir constant or documented contract path shared by dispatcher and log flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

