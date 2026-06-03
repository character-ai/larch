### FINDING_10: [OUT_OF_SCOPE] full-tmpdir equality guard skipped when `IMPLEMENT_TMPDIR` unset
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The full-tmpdir equality guard is skipped when `IMPLEMENT_TMPDIR` is unset (isolation tests in `test-codex-implementer.sh`). Direct launcher invocation without that env var can still grant `--add-dir` at an arbitrary directory parent. Documented harness behavior; `/implement` always sets `IMPLEMENT_TMPDIR` in `step2-implement.sh` before Codex spawn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_11: [OUT_OF_SCOPE] repo-wide `--add-dir "$PWD"` coupling remains by design
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-existing — `--add-dir "$PWD"` still grants repo-wide workspace-write. If `$IMPLEMENT_TMPDIR` ever lives inside the repo tree, orchestrator files at the session root could remain writable via the repo grant even with the narrowed session `--add-dir`; narrowing the session grant does not remove that coupling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document or constrain tmpdir placement (existing SECURITY.md posture); out of scope for this PR’s session-grant narrowing.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_12: [OUT_OF_SCOPE] run-logs.md lists codex transcript at session root
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `docs/run-logs.md:30-31` — The run-log tree still lists `codex-impl-transcript.txt` at the session tmpdir root; `step-7a` now flushes from `codex-step2-out/`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Note the subdir in the directory diagram when updating run-log docs; out of plan scope here.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] codex-manifest-schema.md still documents root tmpdir manifest path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cursor-claude-path-isolation-output.txt
- **Severity**: latent
- **Concern**: The normative schema doc still states Codex writes the manifest (and related sanitized copy paths) at `$IMPLEMENT_TMPDIR/manifest.json` while the branch relocates Codex output to `$IMPLEMENT_TMPDIR/codex-step2-out/manifest.json`. Runtime is fine because prompts and `MANIFEST=` KV use substituted paths, but operators, contributors, tests, or tooling that follow only `codex-manifest-schema.md` may mis-locate files or stub wrong paths after this change. Cursor paths at the tmpdir root remain correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cursor-claude-path-isolation-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Update the contract to document $IMPLEMENT_TMPDIR/codex-step2-out/manifest.json for codex (cursor unchanged at tmpdir root).
  - From cursor-specialist-testing-output.txt: Qualify codex manifest path as IMPLEMENT_TMPDIR/codex-step2-out/manifest.json in a follow-up doc edit
  - From cursor-specialist-edge-cases-output.txt: Qualify Codex vs Cursor paths in `codex-manifest-schema.md` (mirror `step2-implement.md`).
  - From cursor-specialist-plan-fidelity-output.txt: Qualify the path for `CODER=codex` when touching that file; not required by this plan’s file list.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] harness checks manifest absence only at tmpdir root
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Harness checks only root `manifest.json` after codex retry failure. A manifest written only under `codex-step2-out/` would not fail this assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend assertion to the codex subdir path if full absence is intended.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] `launch-codex-implement.sh` canonicalization parity gap vs `launch-review.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_codex_canonical_existing_dir` in `launch-codex-implement.sh` mirrors symlink rejection and `pwd -P` but lacks `launch-review.sh` control-character and `..` segment checks (and, for review `--codex-add-dir`, `_codex_under_root` containment). Crafted or unusual `--manifest-path` parents might canonicalize differently than review `--codex-add-dir` validation. The implement launcher also does not require `SESSION_TMPDIR` to be a subdirectory of `IMPLEMENT_TMPDIR` when set. Pre-existing parity gap, not widened by this diff’s production caller (`$TMPDIR/codex-step2-out/*`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align helper with launch-review.sh _codex_canonical_existing_dir or extract shared lib.
  - From cursor-specialist-edge-cases-output.txt: Reuse or share the review helper (or add the same predicates) if pathological argv is in scope.
  - From cursor-specialist-security-output.txt: mirror `_codex_under_root "$SESSION_TMPDIR" "$_canon_implement_tmpdir"` when `IMPLEMENT_TMPDIR` is set.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] test-codex-implementer.md coverage bullets stale
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness md not updated for narrowed add-dir or tests 11c–11e. Contributors reading only the md may miss new reject-path coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update Coverage bullets for codex-step2-out grant and 11c/11d/11e per script-md-siblings


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Cursor Step 2 still writes anywhere under session tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-cursor-implement.sh` (Cursor Step 2) — Cursor still writes anywhere under `$TMPDIR_ARG` (including `session-env.sh`, baselines, `manifest-raw.json`). Documented intentional asymmetry; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

