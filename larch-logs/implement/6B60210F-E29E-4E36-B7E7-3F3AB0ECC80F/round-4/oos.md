### FINDING_10: [OUT_OF_SCOPE] Plan says ship-pr untouched; branch adds python per-job replay
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan acceptance claims `ship-pr.sh` untouched, but the branch adds `python-lint` / `python-tests` to `_per_job_argv` per-job replay. Strangler-fig / acceptance may reject the PR; allowlist-only `ci-failed-jobs` can still yield `ci-local-unfixable` exit 3 without replay mapping. Docs/plan drift from the actual diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_1: [OUT_OF_SCOPE] Stale ignore-patterns in python/.pylintrc
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Stale `ignore-patterns` from copied config; contributor confusion only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] relevant-checks skips py-test/py-lint when tools absent (optional extension)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Optional `py-test` / `py-lint` in `relevant-checks` when dev tools are not on PATH; local passes may not reflect CI. Extends beyond four enumerated non-python Phase 1 edits; extra local validation path not required by Phase 1 acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] gitleaks allowlist for python fixtures and caches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Gitleaks path allowlist expanded for `python/test_redact.py`, caches, and related paths; synthetic or accidental secrets under allowlisted paths may skip gitleaks layers 1–2 in CI. Supporting `SECURITY.md` / plan file-list drift for Phase 1 enumeration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] make lint omits py-lint/py-test by design
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `make lint` omits `py-lint` / `py-test` by design. Developers who only run `make lint` never exercise the new Python tree locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] Bash create-pr sends unredacted title (pre-existing)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Bash `create-pr` sends unredacted title to `gh` (pre-existing). Same title leakage class as new `gh.py` for PR titles only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Full CI-fix waterfall in ship-pr not ported to Python agents
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Full CI-fix waterfall includes rollback/verify/bail not ported to Python. Phase 7 must not assume `agents.run_waterfall` equals `run_ci_fix_vendor`; keep orchestration in ship-pr until explicitly migrated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Plan understates ship-pr _per_job_argv for fixable jobs
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan failure-mode text understates need for ship-pr `_per_job_argv` when jobs are fixable. Fixable classification without argv mapping still exits 3; ship-pr edit closes a gap the plan did not fully specify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

