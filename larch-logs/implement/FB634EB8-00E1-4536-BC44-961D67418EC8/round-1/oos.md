### FINDING_10: [OUT_OF_SCOPE] Postmerge log finalization writes report before done manifest
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` renders the final report before writing `status=done`/`pr_number` to the manifest, inverting bash ordering. A report/redaction or later manifest failure can leave summary and manifest state inconsistent with bash recovery semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.
  - From dyn-runlog-recovery-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Merge parity lacks an always-collected fail-closed gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `python/test_merge_bash_parity.py` has the same all-skipped-green risk because there is no separate always-collected gate asserting real merge parity tests collect when bash is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] Finalize parity gate checks source text instead of collected tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity_gate.py` only greps for skip markers/source strings. If the parity module is empty, over-skipped, or smoke-only, bash-present CI can still pass with no real collected/non-skipped parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] Redundant merge skip mapping branch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `python/merge.py` has a redundant `redaction-failed` branch after the generic `skip.skipped` handler; behavior is unchanged but mapping can be collapsed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_26: [OUT_OF_SCOPE] `python/README.md` still documents pending retry as omitted
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-resume-output.txt
- **Severity**: nit
- **Concern**: The Phase 6 README note still says `CI_FIX_REBASE_PENDING` is intentionally omitted even though this branch adds partial pending plumbing, creating documentation drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-state-resume-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] Large unrelated design/timing diffs increase review blast radius
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: Large design-skill/timing-report changes appear bundled with finalize/ship CI parity work, making scope and verification harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_31: [OUT_OF_SCOPE] Postbump conflict handling is stricter than prior Python path
- **Reviewer(s)**: dyn-git-safety-output.txt
- **Severity**: nit
- **Concern**: Postbump no longer uses conflict-fixing `rebase_and_push` and now goes through `_rebase_no_push` with explicit abort; this is an improvement versus pre-branch Python, separate from remaining CI-fix rebase issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-safety-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] CI monitor test comment is stale around pending retry
- **Reviewer(s)**: dyn-git-safety-output.txt
- **Severity**: nit
- **Concern**: `python/test_ci_monitor.py` still documents no `CI_FIX_REBASE_PENDING` retry for push failure, while code now partially sets pending in behind-main rebase paths; the existing test does not exercise the new path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-safety-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] Plan-listed CI monitor pending/rebase tests lack coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-git-safety-output.txt, dyn-state-resume-output.txt
- **Severity**: important
- **Concern**: New CI-fix rebase, force-push, pending retry, behind-main, and monitor persistence behavior lacks focused tests. Regressions in `stage_and_push`, `CI_FIX_REBASE_PENDING`, and ship/monitor handoff can pass `py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.
  - From dyn-git-safety-output.txt: Address the concern above.
  - From dyn-state-resume-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_40: [OUT_OF_SCOPE] `timing-ledger.sh` exits zero so callers must verify writes
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: `scripts/timing-ledger.sh` exits 0 even when internal operations fail, making post-verification load-bearing on deferred timing paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_41: [OUT_OF_SCOPE] Design step labels differ from implement step labels
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: nit
- **Concern**: Design timing marks include a `design Step N — …` prefix while implement uses bare `Step N — …` with `skill=implement`, making cross-skill comparisons awkward though reporting still works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Run-log recovery skip paths lack regression tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: latent
- **Concern**: Tests cover happy-path manifest recovery but not `recovery_ok=false` / `manifest-recovery-failed` skip paths. `flush_logs_pre`/`flush_logs_post` could incorrectly write done manifests, reports, or commits after failed recovery without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-runlog-recovery-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

