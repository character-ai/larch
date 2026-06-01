### FINDING_10: [OUT_OF_SCOPE] correctness: Python vs bash drop-changelog failure handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Python stalls on more drop-changelog failures than bash (`scripts/ship-pr.sh` rc!=0 continue path). Transient drop script failures stall in Python where bash would warn and continue. Alignment needed only if bash-parity tests require identical non-match vs hard-failure handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] risk-integration: no bash-parity harness for rebase component on this branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No bash-parity harness for the rebase component on this branch; Phase 7 cutover may discover drift not caught by stub unit tests alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Plan shadow runs or embedded bash parity before `LARCH_SHIP_PR_IMPL=python`.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_2: [OUT_OF_SCOPE] correctness: `_commit_changelog_after_rebump` hardcodes `origin/main` for `replaces_version` fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_commit_changelog_after_rebump` uses a fixed `origin/main` (or equivalent) for `plugin.json` / `replaces_version` fallback while `rebase_and_rebump` parameterizes `base_remote` / `base_ref` elsewhere. Rebases against non-default remotes/refs can pick the wrong version, stall, or write incorrect CHANGELOG sections after rebump. Thread `base_remote` / `base_ref` through the helper and use the same ref in `git.show_file` and regression guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Thread `base_remote`/`base_ref` into `_commit_changelog_after_rebump` `show_file` ref
  - From cursor-specialist-plan-fidelity-output.txt: Use `f"{base_remote}/{base_ref}"` passed from `rebase_and_rebump`


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_23: [OUT_OF_SCOPE] security: full-file reads of launcher output in `agents.py`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Full-file reads of launcher output for classification (not introduced solely by rebase logic); secret-bearing stderr may remain in memory. Pre-existing agents-layer hardening gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pre-existing; add size limits/redaction if hardening agents layer


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_24: [OUT_OF_SCOPE] security: `gh.TransientNetworkError` stores raw `CommandResult`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Same leakage pattern as the new rebase fetch path in `python/gh.py`; not part of this diff alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Not part of this diff; fix holistically across errors module


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_30: [OUT_OF_SCOPE] correctness: `read_launcher_exit` maps parse errors to `0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Malformed `LAUNCHER_EXIT` with `wrapper_rc` 0 is treated as success; launcher contract should be tightened repo-wide.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Tighten launcher contract repo-wide


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_9: [OUT_OF_SCOPE] code-quality: `git.branch_force` untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `branch_force` in `python/git.py` is untested in `test_git.py` (pre-existing gap adjacent to Phase 3 git helpers).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


