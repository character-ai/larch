Structured aggregator output from the supplied reviewer findings (merged by shared behavioral risk; severity = max across sources).

### FINDING_1: code-quality / risk-integration: plan-mandated rebase acceptance tests largely missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan and acceptance criteria call for deterministic bash-parity coverage (drop-bump plus versioned drop-changelog replay, CHANGELOG deterministic prepass, post-rebump changelog tail, guarded drop stall, multi-hop continue after successful `rebase --continue`, post-waterfall scenarios), but `python/test_rebase.py` does not enforce these paths in CI. Regressions in drop/stage/commit orchestration, prepass, or multi-hop conflict handling can ship undetected until Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add stub-runner `rebase_and_rebump` test scripting `drop_bump` dropped, bullets staged, `drop_changelog_commit` called, and `Stalled` on guarded companion drop refusal.
  - From cursor-specialist-edge-cases-output.txt: Add stub tests for companion drop Stalled/success
  - From cursor-specialist-plan-fidelity-output.txt: Add the listed stub-runner tests per implementation plan `test_rebase.py` section

### FINDING_2: [OUT_OF_SCOPE] correctness: `_commit_changelog_after_rebump` hardcodes `origin/main` for `replaces_version` fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_commit_changelog_after_rebump` uses a fixed `origin/main` (or equivalent) for `plugin.json` / `replaces_version` fallback while `rebase_and_rebump` parameterizes `base_remote` / `base_ref` elsewhere. Rebases against non-default remotes/refs can pick the wrong version, stall, or write incorrect CHANGELOG sections after rebump. Thread `base_remote` / `base_ref` through the helper and use the same ref in `git.show_file` and regression guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Thread `base_remote`/`base_ref` into `_commit_changelog_after_rebump` `show_file` ref
  - From cursor-specialist-plan-fidelity-output.txt: Use `f"{base_remote}/{base_ref}"` passed from `rebase_and_rebump`

### FINDING_3: code-quality / architecture: `_resolve_conflicts` lacks per-file fixer prompt context
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_resolve_conflicts` passes only a `--conflict-files` CSV via launchers; it does not build `conflict-resolution.md`-style per-file prompt blocks (`repo` / `run_id` unused). Agents lack upstream/feature context required by the plan, reducing fix quality versus Phase 1–4 procedure (or plan wording should be aligned with launcher-only delegation).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Align plan wording with launcher delegation or implement prompt assembly in `rebase.py`

### FINDING_4: code-quality: `ScriptRunner` duplicates stub-runner patterns
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/test_rebase.py` `ScriptRunner` duplicates `ProcRunner` / `StubRunner` patterns from `test_version_bump.py`. Future argv/env changes require parallel edits in two harness implementations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: code-quality: duplicate bump-subject regex vs `version_bump.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/rebase.py` duplicates bump subject regex/parsing vs `version_bump.py`. Divergent regex or template changes could desync drop-bump version extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: code-quality: double resolution of rebump bullets path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `rebase_and_rebump` resolves rebump bullets path twice (`python/rebase.py` ~481–501). Low risk today but adds noise when evolving path resolution rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: code-quality: `python/README.md` phase heading stale
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: README title still says Phase 1–2 only; docs mislead readers about Phase 3 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: code-quality / risk-integration: `read_launcher_exit` lacks unit tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `read_launcher_exit` in `python/agents.py` has no unit test. Regression in `LAUNCHER_EXIT` parsing could break `make_conflict_launch_fn` waterfall classification (wrong tier skip or stall).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add `test_agents` cases for `LAUNCHER_EXIT` parsing and missing file default.

### FINDING_9: [OUT_OF_SCOPE] code-quality: `git.branch_force` untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `branch_force` in `python/git.py` is untested in `test_git.py` (pre-existing gap adjacent to Phase 3 git helpers).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] correctness: Python vs bash drop-changelog failure handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Python stalls on more drop-changelog failures than bash (`scripts/ship-pr.sh` rc!=0 continue path). Transient drop script failures stall in Python where bash would warn and continue. Alignment needed only if bash-parity tests require identical non-match vs hard-failure handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_11: correctness: `make_conflict_launch_fn` reads `LAUNCHER_EXIT` from agent output file, not launcher stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Cursor can fail with `LAUNCHER_EXIT=1` on launcher stdout while Python reads a missing key from the agent `--output` file as `0`, treats the tier as winner, and skips Codex/Claude. Parse `LAUNCHER_EXIT` from `launch_tier` `CommandResult.stdout` (bash `launcher_stdout` parity); add a test with `LAUNCHER_EXIT` only on stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: correctness: `_resolve_conflicts` uses CI-style waterfall, not bash recovery waterfall
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_resolve_conflicts` uses CI-style `run_waterfall` (first-tier “other” short-circuit; no fallback after win with remaining unmerged paths). Bash `run_recovery_waterfall` tries all tiers with `rebase --continue` verify between attempts. Python short-circuits or raises `NeedsUserInput` after one tier. Conflict resolution should use recovery-style tier loop: no first-tier other bail, verify per tier, continue to next tier on failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: correctness: no tree rollback between fixer waterfall tiers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Without snapshot/revert between tiers, a partial Cursor fix leaves a dirty tree; Codex runs on polluted state and mis-resolves. Bash reverts tracked+untracked deltas between tiers (`recovery_waterfall_paths_delta_revert` parity).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: correctness: uncaught `ChangelogError` during rebump changelog write
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write_changelog_entry` can raise `ChangelogError` (bad anchor, duplicate heading) after bullets are staged; driver gets uncaught `ChangelogError` instead of `Stalled`. Catch `ChangelogError`, clear bullets if appropriate, and raise `Stalled` with a redacted message (or use a commit helper that returns `CommitResult`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Catch `ChangelogError` and raise `Stalled` or use commit helper that returns `CommitResult`

### FINDING_15: risk-integration: `_commit_changelog_after_rebump` / `_changelog_ready_after_rebump` lack direct tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Helpers at `python/rebase.py` ~151–233 have zero direct tests; bump integration tests noop the helper. Duplicate-heading stall, `replaces_version` fallback, and ready-tree short-circuit can regress at the rebase boundary without assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `tmp_path` unit tests for helper functions without monkeypatching `_commit_changelog_after_rebump`.

### FINDING_16: risk-integration: `NeedsUserInput` when conflicts remain after winning waterfall untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Agent appears to win but tree still has unmerged paths; escalation via `NeedsUserInput` (“conflicts remain”) may not be exercised in tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub `launch_fn` success with persistent U paths; assert `NeedsUserInput` conflicts remain message.

### FINDING_17: risk-integration: `version.go` / `go.sum` deterministic prepass paths untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Deterministic pre-pass for `version.go` and `go.sum` lacks tests; regression could broad-checkout or omit go module conflict resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `_deterministic_prepass` tests for `version.go` and `go.sum` basenames.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: no bash-parity harness for rebase component on this branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No bash-parity harness for the rebase component on this branch; Phase 7 cutover may discover drift not caught by stub unit tests alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Plan shadow runs or embedded bash parity before `LARCH_SHIP_PR_IMPL=python`.

### FINDING_19: security: `TransientNetworkError` may attach unredacted fetch `CommandResult`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `TransientNetworkError` on fetch can attach an unredacted `CommandResult` on `.result`; future driver logging of `exception.result` could leak tokens/URLs from `git fetch` stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact or drop `.result` on outbound errors; keep only redacted message

### FINDING_20: security: conflict CSV built without path validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Conflict file list is built via comma-join without Python path validation. An unmerged path containing a comma splits into wrong `--conflict-files` entries; fixers may edit unintended files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Port `larch_validate_vendor_conflict_csv` before join; stall on invalid paths

### FINDING_21: risk-integration: `bullets_path` / tmpdir paths not confined to session tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `bullets_path`, `tmpdir`, and `IMPLEMENT_TMPDIR` are not constrained to the session tmpdir; a misconfigured caller could write bullets or launcher captures outside the intended tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document trust boundary; resolve and confine paths under `IMPLEMENT_TMPDIR` in Phase 7 driver

### FINDING_22: security: launcher `--output` may be relative
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Launcher `--output` may be relative when `output_dir` is relative; `launch-*-ci.sh` rejects non-absolute `OUTPUT`, so waterfall can fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve `out_root` with `Path.resolve()` before launch

### FINDING_23: [OUT_OF_SCOPE] security: full-file reads of launcher output in `agents.py`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Full-file reads of launcher output for classification (not introduced solely by rebase logic); secret-bearing stderr may remain in memory. Pre-existing agents-layer hardening gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pre-existing; add size limits/redaction if hardening agents layer

### FINDING_24: [OUT_OF_SCOPE] security: `gh.TransientNetworkError` stores raw `CommandResult`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Same leakage pattern as the new rebase fetch path in `python/gh.py`; not part of this diff alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Not part of this diff; fix holistically across errors module

### FINDING_25: correctness: broad `"no changes"` substring enables `--skip`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Continue failure handling treats any stderr containing `"no changes"` as skip-worthy; incidental messages could trigger blind `--skip` without bash/git-rebase-skip parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Tighten signatures to bash/git-rebase-skip parity

### FINDING_26: correctness: duplicate-heading check hardcodes MARKDOWN for RST changelogs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Duplicate-version-heading detection hardcodes MARKDOWN while RST changelogs with bullets bypass correct dup detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use `detect_format` for `duplicate_version_heading_count`

### FINDING_27: architecture: `_sync_local_main` ignores `branch_force` failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `git branch -f main` failure is ignored; classification may proceed with stale local `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Check returncode; warn or `Stalled`

### FINDING_28: risk-integration: all-tier launcher health failure becomes `NeedsUserInput`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Infra blip during rebase conflict resolution surfaces `NeedsUserInput` whereas bash might orchestrator-retry; Phase 7 driver retry policy vs `NeedsUserInput` needs alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Phase 7 driver retry policy vs NeedsUserInput

### FINDING_29: architecture: force-push path ignores fetch errors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Fetch errors before lease-guarded force-push may be ignored silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optionally check fetch rc before push

### FINDING_30: [OUT_OF_SCOPE] correctness: `read_launcher_exit` maps parse errors to `0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Malformed `LAUNCHER_EXIT` with `wrapper_rc` 0 is treated as success; launcher contract should be tightened repo-wide.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Tighten launcher contract repo-wide

### FINDING_31: correctness: `_sync_local_main` silently returns on `main` instead of refusing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: If `ship.py` ever invokes `rebase_and_rebump` on `main`, Python silently returns instead of refusing like `git-sync-local-main.sh`; rebump may proceed with wrong branch semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Raise `Stalled` with bash-parity message and add a unit test

### FINDING_32: architecture: `RebaseResult.detail` always empty
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan specifies redacted `detail` on outcomes; field is always empty so callers cannot surface human-readable results without parsing other fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Populate `detail` via `redact.redact_outbound` on key outcomes or document as driver-owned

---

**Merge notes (for voters, not machine output):**
- Input **FINDING_19** (CHANGELOG prepass) and **FINDING_20** (drop_bump stall) are subsumed under **FINDING_1** (same acceptance-test gap).
- Input **FINDING_21** (multi-hop) is subsumed under **FINDING_1**.
- Input **FINDING_37** (edge drop-changelog tests) is subsumed under **FINDING_1**.
- Input **FINDING_42** merged into **FINDING_3**; input **FINDING_44** merged into **FINDING_2** (OOS tag retained on merged heading per aggregator rules).
- **FINDING_12** vs **FINDING_13**: kept separate (waterfall algorithm vs inter-tier tree rollback).
- No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).
