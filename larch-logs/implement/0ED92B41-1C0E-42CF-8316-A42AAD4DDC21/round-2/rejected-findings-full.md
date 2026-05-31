### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `run_checks_phase` uses one `site` for checks and lint-fix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `run_checks_phase` uses one site (default `step6`) for both checks and lint-fix; bash `run_checks_phase` uses step6 checks and `ship-pr-ci-initial` fix. Phase 7 drop-in without site override changes commit messages and prompt labels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document split or add checks_site/fix_site parameters.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `_scripts_dir(repo_root)` ignores `repo_root` (misleading signature)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_scripts_dir(repo_root)` always resolves plugin scripts via `__file__`, ignoring `repo_root`. Misleading signature suggests consumer-repo script lookup during Phase 7 wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Rename to _plugin_scripts_dir() without repo_root or add a comment documenting plugin-root resolution.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Unused `baseline_tracked` / `baseline_untracked` in `_post_dispatch_forbidden_revert`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_post_dispatch_forbidden_revert` accepts `baseline_tracked`/`baseline_untracked` but never uses them. Dead parameters add noise and suggest unfinished baseline-scoped revert logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove unused parameters or implement baseline-scoped revert if required for parity.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `normalize_max_iter` parametrization omits explicit multi-digit strings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Parametrization omits explicit two-digit strings like `10`/`12` though the plan table includes multi-digit clamp (unlikely bug since `99` covers length>1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add ("10", 6) and ("12", 6) to parametrize.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: `ChecksResult.raw_log_path` is an undeclared extension field
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Extra field beyond plan dataclass spec may surprise Phase 7 consumers expecting exact machine record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document as extension or move raw path handling out of ChecksResult


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Missing `errors` import listed in plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan specifies `errors` sibling import; module omits it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Import errors where appropriate or update plan import list


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `run_lint_fix` is an oversized god function with duplicated post-dispatch logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_lint_fix` (~325 lines) duplicates forbidden-revert/violation blocks across branches, making parity auditing, CI-fixer extension, and isolated unit testing of post-dispatch paths difficult.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract _finalize_dispatch_delta(...) for forbidden revert, delta capture, and commit; keep run_lint_fix as thin orchestration.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `checks.py` monolith should split after Phase 4 acceptance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: ~1421-line module with ~25 private helpers and four embedded `bash -c` wrappers exceeds sibling `python/` modules; future phases (CI fixer) will increase merge-conflict and review cost in one file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: After Phase 4 acceptance, split dispatch helpers into a flat sibling module (e.g. checks_dispatch.py).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

