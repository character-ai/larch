### FINDING_1: assert_no_probe_homes only observes post-EXIT state; trap cleanup can mask inline rm regression
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `assert_no_probe_homes` runs only after EXIT-trap cleanup in `scripts/test-check-reviewers.sh`, so inline `rm -rf` inside `larch_run_one_codex_probe` can be removed while trap cleanup still passes all probe-home assertions—hiding regressions in inline cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document end-state-only semantics or add harness hook to distinguish inline vs trap cleanup
  - From cursor-specialist-correctness-output.txt: Pin inline cleanup via stub logging or trap-disable harness env; document end-state-only semantics

### FINDING_2: t8 auth-retry success path omits assert_no_probe_homes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The auth-retry case `t8` lacks `assert_no_probe_homes` unlike other probe paths; intermediate retry attempts may leak `larch-codex-probe-home.*` while the final attempt succeeds and CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add assert_no_probe_homes after t8
  - From cursor-specialist-correctness-output.txt: Add assert_no_probe_homes after t8 or log homes per retry in stub
  - From cursor-specialist-testing-output.txt: Add assert_no_probe_homes after t8 assertions
  - From cursor-specialist-security-output.txt: Add assert_no_probe_homes for SCRATCH/t8
  - From cursor-specialist-plan-fidelity-output.txt: Add assert_no_probe_homes for SCRATCH/t8

### FINDING_3: Login-mode cases use OPENAI_API_KEY='' instead of unset subshell
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Login-mode harness cases set `OPENAI_API_KEY=''` rather than using an `unset` subshell, diverging from `test-codex-implementer` 4f and plan edge-case guidance; future empty-vs-unset handling differences could hide regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use `( unset OPENAI_API_KEY; ... )` subshell per plan
  - From cursor-specialist-plan-fidelity-output.txt: Wrap invocations in `( unset OPENAI_API_KEY; export TMPDIR=…; … )` per plan

### FINDING_4: Duplicated auth-link target acceptance logic across harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Auth-link target acceptance logic is duplicated across harnesses; future symlink assertion changes must be edited in two places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared `assert_codex_auth_link_points_at` helper

### FINDING_5: Redundant overlapping post-table assertions on login-home/config.toml
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lib-external-launcher-common.sh` uses both `grep -Fxc` counts and `assert_file_not_line` for the same needles on login-home/config.toml, adding maintenance burden without extra signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep grep -Fxc counts OR line helpers not both for same needles
  - From cursor-specialist-correctness-output.txt: Remove redundant assert_file_not_line or use nested-table-specific assertion

### FINDING_6: Duplicate mkdir -p for rf_auth_prep_case_tmp
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` calls `mkdir -p` twice for `rf_auth_prep_case_tmp`; no functional bug but adds noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove second mkdir

### FINDING_7: Stamp login decoy omits login symlink/auth-material assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The stamp login decoy case checks env-key argv behavior but omits login symlink/auth-material assertions; login-path symlink wiring regressions could pass while argv checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add symlink or config capture assertions mirroring review-and-fix login fallback

### FINDING_8: Legacy strip case lacks intent comment
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The legacy strip case duplicates unit strip coverage without an intent comment; readers may treat it as redundant strip testing rather than integration wiring coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add comment that case pins probe-stub config capture integration

### FINDING_9: [OUT_OF_SCOPE] Monolithic test-check-reviewers harness file
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-check-reviewers.sh` keeps growing with inline stubs; pre-existing structure not new to this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider modularizing in a separate refactor

### FINDING_10: [OUT_OF_SCOPE] /tmp snapshot helper concurrent-run race (plan-accepted trade-off)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Global `/tmp` snapshot diff in `test-codex-implementer.sh` has a concurrent-run race window; parallel local runs or unrelated `/tmp/larch-codex-home-*` creation can cause spurious failures; plan accepted this trade-off.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add single-runner comment near snapshot helper
  - From cursor-specialist-correctness-output.txt: Isolate TMPDIR in launcher tests or accept single-runner CI constraint
  - From cursor-specialist-testing-output.txt: Add comment documenting no concurrent implementer launches; plan explicitly requested this
  - From cursor-specialist-plan-fidelity-output.txt: Keep plan contract or document CI isolation if flakiness appears

### FINDING_11: Auth-prep TMPDIR survivor scan is post-EXIT only; trap can mask inline codex_home rm regression
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Auth-prep TMPDIR survivor scan in `test-review-and-fix.sh` runs only after EXIT; inline `rm -rf "$codex_home"` at `review-and-fix.sh:332` can regress while `REVIEW_FIX_TMPDIRS` trap still cleans, so `find` shows no new survivors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Assert captured CODEX_HOME removal inside stub or disable trap in test-only mode

### FINDING_12: Stamp decoy checks stamp existence but not decoy stamp content
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Stamp login decoy assertions verify stamp file existence (and env-key stamp stability) but not that login stamp content remains the expected decoy value; probe can write `login` stamp `false` while `CODEX_PRESENT=true` and checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror t6: assert login stamp content is true and env-key decoy unchanged
  - From cursor-specialist-testing-output.txt: Assert env-key stamp still reads true after run

### FINDING_13: Uneven assert_no_probe_homes coverage on live probe paths (t6e, t6m, t10, t11, etc.)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Several live probe paths (including `t6e` env-key decoy and others such as `t6m`, `t10`, `t11`) omit `assert_no_probe_homes`; probe temp homes can leak while other paths' cleanup assertions stay green. (`t8` is covered separately in FINDING_2.)
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add assert_no_probe_homes and optional sentinel sweep like t10-env-key-false
  - From cursor-specialist-security-output.txt: Add assert_no_probe_homes wherever live probe runs
  - From cursor-specialist-plan-fidelity-output.txt: Add assert_no_probe_homes wherever live probe runs

### FINDING_14: Login-fallback test lacks temp CODEX_HOME removal assertion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Login-fallback success path does not assert temp `CODEX_HOME` removal; successful codex dispatch could leave `larch-codex-review-fix-home.*` if inline `rm` regresses but trap masks it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Capture CODEX_HOME via TEST_AGENT_CODEX_HOME_FILE and assert path absent after run
  - From cursor-specialist-security-output.txt: Capture CODEX_HOME and assert directory removed post-run
  - From cursor-specialist-plan-fidelity-output.txt: Capture CODEX_HOME and assert directory removed post-run

### FINDING_15: [OUT_OF_SCOPE] Legacy strip case duplicates lib-external unit strip tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Legacy strip case duplicates `lib-external` unit strip tests without unique failure modes; extra maintenance surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Defer unless integration wiring regression is a priority

### FINDING_16: Legacy strip test omits TMPDIR-wide sentinel leak scan
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Legacy strip integration test does not grep case `TMPDIR` recursively for `<REDACTED-TOKEN>`; sentinel can leak to non-captured probe artifacts undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep case TMPDIR recursively for <REDACTED-TOKEN> like t10-env-key-false
  - From cursor-specialist-security-output.txt: Add grep -Fr <REDACTED-TOKEN> on case TMPDIR fail-on-match
  - From cursor-specialist-plan-fidelity-output.txt: Add grep -Fr <REDACTED-TOKEN> on case TMPDIR fail-on-match

### FINDING_17: multiline-dq-comment fixture missing header strip assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `multiline-dq-comment` case lacks header strip assertion; partial strip could remove table body but leave `[model_providers.openai-larch-env]` header.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add assert_file_not_contains for the larch provider table header

### FINDING_18: assert_argv_immediately_after_c passes on first correct pair only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `assert_argv_immediately_after_c` accepts any single adjacent `-c`/config pair; later mis-ordered duplicate `-c` overrides in argv log would not fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Tighten helper to fail on any non-adjacent override occurrence
  - From cursor-specialist-security-output.txt: Use positional argv index checks or require unique adjacency
  - From cursor-specialist-plan-fidelity-output.txt: Use positional argv index checks or require unique adjacency

### FINDING_19: [OUT_OF_SCOPE] OPENAI_API_KEY='' instead of unset subshell (functionally equivalent today)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Login-mode cases use `OPENAI_API_KEY=''` instead of unset subshell; functionally equivalent today via length check in `external_codex_env_key_enabled`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Use unset subshell for plan consistency if desired

### FINDING_20: [OUT_OF_SCOPE] Mutation sanity checks not evidenced in session artifacts
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan-required mutation sanity and full harness matrix execution are not evidenced in diff/session artifacts; false-green assertions or failing harnesses could merge undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run plan-required mutation sanity per harness before merge
  - From cursor-specialist-plan-fidelity-output.txt: Run and record remaining harness targets plus one assertion flip per file

### FINDING_21: Global /tmp larch-codex-home-* snapshot is not case-isolated
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `test-codex-implementer.sh` global `/tmp` `larch-codex-home-*` snapshot is not case-isolated; parallel CI or leftover `/tmp` dirs can cause false failures or mask leaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Scope snapshots to case-private TMPDIR or assert on captured CODEX_HOME path only

### FINDING_22: Login-mode launcher paths 4f/4g lack temp-home cleanup assertions
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Temp-home cleanup is asserted only for tests 4 and 4h; login-mode launcher paths 4f/4g can leak `larch-codex-home-*` undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add assert_no_new_larch_codex_homes around 4f and 4g

### FINDING_23: Env-key dispatch-failure omits events.jsonl sentinel leak check
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Env-key dispatch-failure test does not grep `coder-codex.events.jsonl` for sentinel leak; `<REDACTED-TOKEN>` in events would not fail the new test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Grep events.jsonl for <REDACTED-TOKEN> fail-on-match
  - From cursor-specialist-plan-fidelity-output.txt: Grep events.jsonl for <REDACTED-TOKEN> fail-on-match

### FINDING_24: 4f accepts non-canonical symlink path string
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Test 4f accepts non-canonical symlink path string; relative symlink target could mask `readlink`/canonicalization bugs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require only canonical resolved auth.json path
  - From cursor-specialist-plan-fidelity-output.txt: Require only canonical resolved auth.json path

### FINDING_25: [OUT_OF_SCOPE] multiline sq fixture documents stripper skips quoted bodies
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New multiline sq fixture documents that stripper skips selectors inside triple-quoted literals; pre-existing stripper behavior, not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Harden external_strip_codex_larch_env_provider if multiline embedding is in threat model

### FINDING_26: [OUT_OF_SCOPE] Pre-existing telemetry test never asserts CODEX_HOME cleanup
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Pre-existing codex-telemetry test never asserts `CODEX_HOME` cleanup; temp home survival on success path untested outside new failure case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add post-run removal assertion to codex-telemetry test
  - From cursor-specialist-plan-fidelity-output.txt: Add post-run removal assertion to codex-telemetry test

### FINDING_27: multiline sq body fixture retains in-body larch selectors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `multiline sq` body fixture retains in-body larch selectors inside `'''` literals after strip; may be intended contract or a security/documentation gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document intended contract or add strip-if-required production change

### FINDING_28: [OUT_OF_SCOPE] Env-key auth-prep failures swallowed in production
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Env-key auth-prep failures are swallowed in production; auth-prep breadcrumb unreachable on `OPENAI_API_KEY` path without prod change; correctly out of scope for this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Out of scope; branch correctly omits unreachable case

### FINDING_29: [OUT_OF_SCOPE] Cleanup only on 4 and 4h is plan-scoped; 4f/4g omission matches plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Asserting cleanup only on tests 4 and 4h matches plan item 2; login paths 4f/4g omission is plan-intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: No change required for plan fidelity
