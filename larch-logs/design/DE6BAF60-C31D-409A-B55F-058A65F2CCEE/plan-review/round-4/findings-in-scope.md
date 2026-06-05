### FINDING_1: Env-key auth-prep failure case is unreachable with planned mechanism
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Codex-Edge, Codex-Requirements, Cursor-dyn-stub-isolation, Codex-dyn-env-leak, Codex-dyn-assertion-fidelity
- **Severity**: important
- **Concern**: Multiple reviewers report that the planned review-and-fix env-key auth-prep failure test cannot trigger the intended `codex_auth_setup_failed` / auth-setup breadcrumb path under current production semantics, because the OPENAI_API_KEY path treats strip/mv failures as best-effort and returns success after temp home setup. A test following the plan may dispatch Codex instead, fail assertions, or force an unplanned production behavior change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Drop review-and-fix dispatch item 4 (env-key auth-prep failure fallback); keep item 5 (env-key dispatch failure) and login auth-prep failure item 2; add an explicit note mirroring test-codex-implementer.sh item 3 that this breadcrumb is unreachable under current production semantics unless lib-external-launcher-common.sh changes
  - From Codex-Arch: For the env-key auth-prep case, specify a failure that makes external_prepare_codex_auth return nonzero in env-key mode, such as a narrowly delegated mkdir stub for the larch-codex-review-fix-home path, or drop this case and keep only the env-key dispatch-failure breadcrumb test
  - From Codex-Pragmatic: For the env-key auth-prep case, specify a failure that makes external_prepare_codex_auth return nonzero in env-key mode, such as a narrowly delegated mkdir stub for the larch-codex-review-fix-home path, or drop this case and keep only the env-key dispatch-failure breadcrumb test
  - From Codex-Edge: Drop the env-key auth-prep failure case, or re-scope it to the planned env-key dispatch-failure breadcrumb test unless the PR intentionally changes production behavior to make env-key strip failures fatal
  - From Codex-Requirements: Drop the review-and-fix env-key auth-prep failure case, or replace it with the already planned env-key dispatch-failure breadcrumb and cleanup test. Keep login-mode auth-prep failure coverage for prep-failure behavior.
  - From Cursor-dyn-stub-isolation: Proposed env-key auth-prep failure case uses the same mv-based prep-failure mechanism as login, but external_prepare_codex_auth always returns 0 on the OPENAI_API_KEY branch (strip errors are swallowed with || true) and review-and-fix already mktemps codex_home before calling it, so mkdir cannot fail either. The case cannot emit codex-env-key-failure auth-setup breadcrumbs; it contradicts the same plan’s implementer note that env-key auth-prep breadcrumb is unreachable (plan.txt:77). Drop the env-key auth-prep failure case, or retarget it to the dispatch-failure breadcrumb already covered in plan item 5 (cursor-success stub) unless production is changed to fail closed on env-key strip.
  - From Codex-dyn-env-leak: For the env-key auth-prep case, specify a prep-failure fixture that makes `external_prepare_codex_auth` return nonzero in env-key mode, such as a narrowly targeted `mkdir` stub for the temp `larch-codex-review-fix-home.*` path, and keep `OPENAI_API_KEY` scoped to that subshell/call.
  - From Codex-dyn-assertion-fidelity: Keep the minimum-change contract by dropping this review-and-fix env-key auth-prep-failure case, mirroring the implementer note that this path is fixture-unreachable; retain the env-key dispatch-failure breadcrumb case instead.

### FINDING_2: Login auth-prep cleanup needs a case-private exported TMPDIR
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-env-leak
- **Severity**: important
- **Concern**: The planned login auth-prep cleanup assertions snapshot or scan a temp directory that review-and-fix does not necessarily use, because the harness does not export a case-private `TMPDIR` before invoking `review-and-fix.sh`. This can make survivor checks vacuous or vulnerable to unrelated global `/tmp` state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add TMPDIR="$case_tmp" (or export TMPDIR="$case_tmp") to the login auth-prep failure subshell alongside unset OPENAI_API_KEY and HOME="$fixture_home" before run_review_and_fix
  - From Cursor-dyn-env-leak: Inside each new auth subshell export a dedicated dir (`TMPDIR="$work_case/harness-tmp"; mkdir -p "$TMPDIR"`) before `run_review_and_fix`, then run `assert_no_review_fix_homes` on that path; or reuse the implementer `/tmp` before/after survivor diff pattern from `test-codex-implementer.sh`.

### FINDING_3: Trusted-project `-c` adjacency is planned on a less direct env-key case
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The trusted-project `-c` adjacency assertion is planned for `t10-env-key-false`, even though `t6m` already exercises the live login-path probe with argv capture. Extending `t10-env-key-false` adds sentinel setup without covering a distinct production surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add adjacency plus trust string assertions to the existing t6m argv log; keep t10-env-key-false limited to stamp miss, env-key argv, and sentinel leak checks

### FINDING_4: Stamp-isolation login-path case must control login-stamp cache state
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The stamp-isolation test does not explicitly prevent a fresh `codex-login` stamp from short-circuiting the login probe. If such a stamp exists, Codex may not be invoked, so the case can pass without proving login-path argv or symlink wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit fixture contract: no fresh `codex-login` stamp (absent, `false`, or expired) whenever the case must "exercise the login path"; keep the env-key stamp as decoy and assert live-probe argv lacks env-key overrides (and/or shows login auth material)

### FINDING_5: Post-table selector assertions target the wrong fixture file
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-assertion-fidelity, Codex-dyn-assertion-fidelity
- **Severity**: important
- **Concern**: Planned assertions for post-table provider/env-key retention and nested selector removal are aimed at `strip-edge-config.toml`, but the relevant copied config is processed into `login-home/config.toml`. Counts or absence checks can pass against the wrong file while the actual post-table stripping behavior regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Move post-table model_provider/env_key count assertions to login-home/config.toml immediately after external_prepare_codex_auth on copied-config.toml; keep strip-edge-config.toml for direct external_strip_codex_larch_env_provider edge cases only.
  - From Cursor-dyn-assertion-fidelity: Move post-table model_provider/env_key count assertions to login-home/config.toml immediately after external_prepare_codex_auth on copied-config.toml; keep strip-edge-config.toml for the direct external_strip_codex_larch_env_provider edge cases only.
  - From Codex-dyn-assertion-fidelity: When implementing item 1, relocate this assertion to login-home/config.toml post-strip and delete the strip-edge-config.toml copy; add a preflight [[ -f ... ]] before any grep -Fxc count on that path.

### FINDING_6: Review-and-fix mv stub must delegate unrelated mv calls
- **Reviewer(s)**: Codex-dyn-stub-isolation
- **Severity**: important
- **Concern**: The plan’s instruction to mirror the implementer mv stub risks copying an unconditional `mv` failure stub into review-and-fix. That could break unrelated harness or fallback `mv` calls and create false failures rather than isolating the intended Codex auth-prep rename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stub-isolation: Replace “mirroring” with an explicit conditional stub shape: fail only the larch-codex-review-fix-home.* config.toml rewrite/rename and exec /bin/mv "$@" for every other invocation.

### FINDING_7: Stamp-isolation login-path case must explicitly unset OPENAI_API_KEY
- **Reviewer(s)**: Cursor-dyn-env-leak
- **Severity**: important
- **Concern**: The stamp-isolation login-path subcase does not require the helper path or subshell environment that unsets `OPENAI_API_KEY`. On hosts where the key is exported, the test can remain on the env-key path, making login-path assertions vacuous or order-dependent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-env-leak: Implement that subcase with `run_cr` (or an explicit subshell `unset OPENAI_API_KEY`) on a fresh per-case TMPDIR; keep `run_cr_with_env` only where the sentinel key must be present (legacy strip, live env-key probe).

### FINDING_8: Mutation sanity needs negative controls for strip/capture wiring
- **Reviewer(s)**: Cursor-dyn-assertion-fidelity
- **Severity**: latent
- **Concern**: The planned mutation sanity checks only flip expected values, which can catch inverted assertions but not vacuous wiring. A grep against an unstripped, missing, or wrong capture file may still fail when flipped without proving the assertion observes the production processing step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-assertion-fidelity: Add one negative control per harness: skip the strip/capture step (or point at a pre-strip snapshot) and require the new assertion to fail before the flip check.
