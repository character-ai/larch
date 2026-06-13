# Review Round 5

- Mode: `diff`
- 8 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Tier-4 revise status overwrites instead of merging
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Tier-4 revise status overwrites the last vendor attempt instead of using `merge_tier4_status` severity merge. Unified-diff fallback: codex tier-4 `invalid-patch` then cursor `emit-plan-failed` emits `REVISE_TIER_4_STATUS=emit-plan-failed` and may change `REVISE_STATUS` away from `failed-validation`; deleted harness case out11 expected `invalid-patch`. Step 3 loop reads `revise.env` KVs; regressions in tier-4 aggregation or `failed-validation` vs `failed-apply` routing may ship without CI catching them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port merge_tier4_status semantics; merge on each attempt(4, tier); add pytest for multi-vendor tier-4 failure aggregation.


### FINDING_10: `lstrip("./")` strips leading dots, not only `./` prefixes
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_is_new_script` and `_allow_flag` use `lstrip("./")` on stored row paths, which strips any leading dot, not only a literal `./` prefix. A plan that declares `### NEW: .claude/skills/foo/scripts/new.sh` and invokes `.claude/skills/foo/scripts/new.sh` will not match the allowlist, so validation falls through to `missing-script` and blocks a valid new `.claude` skill script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Add a shared canonicalizer that removes only repeated literal `./` prefixes, and use it for both stored rows and invocation paths.


### FINDING_11: Non-file `drift-baseline.env` can crash `plan check-size`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: A non-file `drift-baseline.env`, such as a directory, makes `baseline_path.unlink()` raise `IsADirectoryError`. In that corrupted-baseline scenario, `plan check-size` crashes before emitting the documented warning and drift KVs, so Step 2b.5 cannot recover or fail closed cleanly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Treat non-regular baseline paths as unreadable baseline state without an unhandled unlink, using guarded removal or recovery from `plan.txt-original`.


### FINDING_12: `_validate_unified_headers` can raise on malformed diff lines
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_validate_unified_headers` indexes `line.split()[1]` without checking length. If an external reviewer emits a malformed diff line like `--- ` or `+++ `, `revise-waterfall` raises instead of recording an `invalid-patch` tier status and preserving the `revise.env` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Check `len(parts) >= 2` before indexing and return `False` for malformed headers.


### FINDING_14: Inconsistent `--repo-root` across design validation call sites
- **Reviewer(s)**: dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: Postplan, publish, and driver validation pass `--repo-root "$PLUGIN_ROOT"`, but auto-fix passes `--repo-root "$(git -C "$PWD" rev-parse --show-toplevel …)"` with a `CLAUDE_PLUGIN_ROOT` fallback. In consumer-repo `/design` sessions where `PLUGIN_ROOT` (marketplace plugin) differs from the git toplevel under `$PWD`, the same plan can validate differently at Step 2b/5c than during auto-fix revalidation, producing false passes or false defects across the flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-callsite-cutover-output.txt: Resolve one shared consumer `REPO_ROOT` once (git toplevel of the active design checkout, with the same plugin-root fallback chain) and pass that to every `plan validate` / `plan validate-commands` invocation; keep `PLUGIN_ROOT` only for locating `python/cli.py`.


### FINDING_2: Revision waterfall pytest omits deleted shell harness tier-4 cases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Revision waterfall pytest omits deleted shell harness tier-4 and `revise.env` contract cases. Step 3 loop reads `revise.env` KVs; regressions in tier-4 aggregation or `failed-validation` vs `failed-apply` routing may ship without CI catching them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port test-revise-plan-with-waterfall.sh cases 11, 11b, 11c (minimum) into pytest.


### FINDING_3: SKILL.md S030 pin names wrong drift-baseline runtime authority
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still lists `lib-drift-baseline.sh` as a runtime authority for plan check-size. `/design` loads `SKILL.md`; operators and reviewers may assume the bash drift baseline is still sourced though Python inlined drift reads. The S030 pin claims Python plan check-size sources `lib-drift-baseline.sh`, so debugging drift issues may target deleted or wrong surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update SKILL.md to name python/plan_quality.py and plan check-size only.
  - From cursor-specialist-edge-cases-output.txt: Update pin: Python owns drift reads in plan_quality.py; only design-postplan-emit.sh sources lib-drift-baseline.sh for write-once snapshot


### FINDING_9: `relevant-checks.sh` does not route `plan_quality.py` to `test-design-publish`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `plan_quality.py` edits do not route to `test-design-publish`. Composed-plan validate regressions in `plan validate --source-kind composed` or publish `VALIDATE_*` parsing may not run `test-design-publish` on bash `scripts/relevant-checks.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add append_target_once test-design-publish for python/plan_quality.py changes and a test-relevant-checks routing assertion.


