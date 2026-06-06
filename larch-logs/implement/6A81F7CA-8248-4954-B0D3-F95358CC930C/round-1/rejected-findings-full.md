### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: assert_no_probe_homes only observes post-EXIT state; trap cleanup can mask inline rm regression
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `assert_no_probe_homes` runs only after EXIT-trap cleanup in `scripts/test-check-reviewers.sh`, so inline `rm -rf` inside `larch_run_one_codex_probe` can be removed while trap cleanup still passes all probe-home assertions—hiding regressions in inline cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document end-state-only semantics or add harness hook to distinguish inline vs trap cleanup
  - From cursor-specialist-correctness-output.txt: Pin inline cleanup via stub logging or trap-disable harness env; document end-state-only semantics


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Auth-prep TMPDIR survivor scan is post-EXIT only; trap can mask inline codex_home rm regression
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Auth-prep TMPDIR survivor scan in `test-review-and-fix.sh` runs only after EXIT; inline `rm -rf "$codex_home"` at `review-and-fix.sh:332` can regress while `REVIEW_FIX_TMPDIRS` trap still cleans, so `find` shows no new survivors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Assert captured CODEX_HOME removal inside stub or disable trap in test-only mode


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Uneven assert_no_probe_homes coverage on live probe paths (t6e, t6m, t10, t11, etc.)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Several live probe paths (including `t6e` env-key decoy and others such as `t6m`, `t10`, `t11`) omit `assert_no_probe_homes`; probe temp homes can leak while other paths' cleanup assertions stay green. (`t8` is covered separately in FINDING_2.)
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add assert_no_probe_homes and optional sentinel sweep like t10-env-key-false
  - From cursor-specialist-security-output.txt: Add assert_no_probe_homes wherever live probe runs
  - From cursor-specialist-plan-fidelity-output.txt: Add assert_no_probe_homes wherever live probe runs


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Login-fallback test lacks temp CODEX_HOME removal assertion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Login-fallback success path does not assert temp `CODEX_HOME` removal; successful codex dispatch could leave `larch-codex-review-fix-home.*` if inline `rm` regresses but trap masks it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Capture CODEX_HOME via TEST_AGENT_CODEX_HOME_FILE and assert path absent after run
  - From cursor-specialist-security-output.txt: Capture CODEX_HOME and assert directory removed post-run
  - From cursor-specialist-plan-fidelity-output.txt: Capture CODEX_HOME and assert directory removed post-run


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: multiline-dq-comment fixture missing header strip assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `multiline-dq-comment` case lacks header strip assertion; partial strip could remove table body but leave `[model_providers.openai-larch-env]` header.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add assert_file_not_contains for the larch provider table header


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: assert_argv_immediately_after_c passes on first correct pair only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `assert_argv_immediately_after_c` accepts any single adjacent `-c`/config pair; later mis-ordered duplicate `-c` overrides in argv log would not fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Tighten helper to fail on any non-adjacent override occurrence
  - From cursor-specialist-security-output.txt: Use positional argv index checks or require unique adjacency
  - From cursor-specialist-plan-fidelity-output.txt: Use positional argv index checks or require unique adjacency


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Global /tmp larch-codex-home-* snapshot is not case-isolated
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `test-codex-implementer.sh` global `/tmp` `larch-codex-home-*` snapshot is not case-isolated; parallel CI or leftover `/tmp` dirs can cause false failures or mask leaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Scope snapshots to case-private TMPDIR or assert on captured CODEX_HOME path only


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Login-mode launcher paths 4f/4g lack temp-home cleanup assertions
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Temp-home cleanup is asserted only for tests 4 and 4h; login-mode launcher paths 4f/4g can leak `larch-codex-home-*` undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add assert_no_new_larch_codex_homes around 4f and 4g


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: 4f accepts non-canonical symlink path string
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Test 4f accepts non-canonical symlink path string; relative symlink target could mask `readlink`/canonicalization bugs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require only canonical resolved auth.json path
  - From cursor-specialist-plan-fidelity-output.txt: Require only canonical resolved auth.json path


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_27: multiline sq body fixture retains in-body larch selectors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `multiline sq` body fixture retains in-body larch selectors inside `'''` literals after strip; may be intended contract or a security/documentation gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document intended contract or add strip-if-required production change


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Login-mode cases use OPENAI_API_KEY='' instead of unset subshell
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Login-mode harness cases set `OPENAI_API_KEY=''` rather than using an `unset` subshell, diverging from `test-codex-implementer` 4f and plan edge-case guidance; future empty-vs-unset handling differences could hide regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use `( unset OPENAI_API_KEY; ... )` subshell per plan
  - From cursor-specialist-plan-fidelity-output.txt: Wrap invocations in `( unset OPENAI_API_KEY; export TMPDIR=…; … )` per plan


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated auth-link target acceptance logic across harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Auth-link target acceptance logic is duplicated across harnesses; future symlink assertion changes must be edited in two places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared `assert_codex_auth_link_points_at` helper


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Redundant overlapping post-table assertions on login-home/config.toml
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lib-external-launcher-common.sh` uses both `grep -Fxc` counts and `assert_file_not_line` for the same needles on login-home/config.toml, adding maintenance burden without extra signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep grep -Fxc counts OR line helpers not both for same needles
  - From cursor-specialist-correctness-output.txt: Remove redundant assert_file_not_line or use nested-table-specific assertion


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate mkdir -p for rf_auth_prep_case_tmp
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` calls `mkdir -p` twice for `rf_auth_prep_case_tmp`; no functional bug but adds noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove second mkdir


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Stamp login decoy omits login symlink/auth-material assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The stamp login decoy case checks env-key argv behavior but omits login symlink/auth-material assertions; login-path symlink wiring regressions could pass while argv checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add symlink or config capture assertions mirroring review-and-fix login fallback


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Legacy strip case lacks intent comment
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The legacy strip case duplicates unit strip coverage without an intent comment; readers may treat it as redundant strip testing rather than integration wiring coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add comment that case pins probe-stub config capture integration


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

