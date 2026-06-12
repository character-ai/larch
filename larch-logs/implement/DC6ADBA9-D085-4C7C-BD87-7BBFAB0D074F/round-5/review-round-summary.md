# Review Round 5

- Mode: `diff`
- 21 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Slow-run gate incorrectly fails NO_ISSUES_FOUND_TOO_THIN
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Python applies the slow-run failure gate to `NO_ISSUES_FOUND_TOO_THIN`, while bash and `SKILL.md` limit that timing gate to `NO_ISSUES_FOUND`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: gh body-file rule no longer covers migrated Python callers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `.claude/rules/gh-body-file.md` dropped migrated shell paths but did not add the replacement Python modules. Edits to `python/combine_issues.py`, `python/audit_runs.py`, and `python/release_finish.py` may skip the file-backed `gh` reminder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: promote-latest ignores isPrerelease probe failure when tag is already latest
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `promote_release.py` ignores the `gh release view --json isPrerelease` return code when the tag is already Latest. A transient or auth failure can leave stdout empty and still report success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: self_deploying_gap duplicate field lacks CI coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test asserts the cross-cutting `self_deploying_gap` duplicate field, so audit consumers can lose that field without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: scan error rows lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Documented scan error rows for missing run dir, missing scans registry, and invalid scan-run args lack pytest coverage. Wire contract or exit code regressions may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: promote-latest verification failure KV phase lacks test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The post-selection verification failure path is untested. Callers that parse phase KVs before `ERROR=` can break without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: combine-issues close WARNING redaction path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Failed close stderr may leak secrets into operator-visible `WARNING` lines because the redaction path required by the plan lacks test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: test_scan_run_rejects_skill_root mutates repo-root larch-logs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_scan_run_rejects_skill_root` writes under repo-root `larch-logs`. Interrupted pytest can leave a dirty tree and affect later implement or lint runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: ns-retry-sidecars legacy sidecar fallback path lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pre-migration logs without `reviewer_signals` may get the wrong pass, skip, or fail classification because the legacy sidecar-only fallback scan path is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Timing fallback misses timing-report steps/per_step data
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The timing fallback reads only `vendor_task_averages`, but retired bash also used timing-report `steps[]` and committed logs use `per_step`. This can report `elapsed_seconds=0` and pass slow `NO_ISSUES_FOUND` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_20: GH_HOST-aware OOS filed URL matching lacks pass-path coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Enterprise `GH_HOST` URLs may not count toward `issue_urls`, breaking OOS silent-drop audit pass logic, because that pass path is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: close-priors partial success output is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Mixed close success and failure cases lack coverage. Per-issue failures may omit `CLOSED_NUMBER` or `CLOSE_FAILED` rows or return the wrong exit code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_25: release finish drops target-resolution retry after merge commit appears
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-release-safety-output.txt
- **Severity**: important
- **Concern**: `release_finish.py` performs single-shot reachability and `origin/main` ancestry checks. GitHub can return `mergeCommit` before `origin/main` or the target SHA is locally available, causing a healthy release PR to fail instead of retrying.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt, dyn-release-safety-output.txt: Address the concern above.


### FINDING_27: required-file scan treats corrupt manifests as empty steps_ran
- **Reviewer(s)**: dyn-required-file-gating-output.txt
- **Severity**: important
- **Concern**: `_scan_required` drops the bash parse-success guard. Invalid or non-object `manifest.json` becomes `{}`, causing `empty_steps()` to enable bail-empty skips and turn required-file failures into passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-required-file-gating-output.txt: Address the concern above.


### FINDING_28: required-file scan treats non-dict steps_ran as empty
- **Reviewer(s)**: dyn-required-file-gating-output.txt
- **Severity**: important
- **Concern**: Non-dict `steps_ran` values are silently coerced to `{}`. Bash treated non-object `steps_ran` as not empty, so bail skips should not apply and step9a1 files should remain enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-required-file-gating-output.txt: Address the concern above.


### FINDING_29: required-file gating parity tests are incomplete
- **Reviewer(s)**: dyn-required-file-gating-output.txt
- **Severity**: important
- **Concern**: `test_scan_required_bail_and_step9a1_gating` covers only happy skip paths. Missing parity cases for corrupt manifests, non-bail incomplete runs, and explicit `steps_ran.step9a1=false` allowed required-file regressions to slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-required-file-gating-output.txt: Address the concern above.


### FINDING_5: compute-counters crashes on non-numeric NDJSON counters
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `compute_counters_main` directly casts scan counter fields with `int()`. Malformed values now raise `ValueError` instead of preserving bash `num_or_zero` behavior and emitting the required KV set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: preflight missing --repo loses machine-readable KVs
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `audit-runs preflight --skill implement` makes `--repo` argparse-required. Missing repo exits with usage text and no `PREFLIGHT_OK` or `REASON` KVs, while the skill synopsis still shows calls without `--repo`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: resolve-prs parses audited_pr_range outside YAML frontmatter
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `resolve-prs` searches the whole prior report body for `audited_pr_range.last`. A malformed prior report can resolve from a later code block or stale example instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: oos-category-mangle stringifies arrays and objects
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The OOS category scan stringifies arrays and objects, drifting from retired jq behavior that treated those types as blank. This can fail rows that previously passed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Design run ID extraction accepts loose suffixes
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Design run ID extraction accepts loose hex or hyphen suffixes instead of strict UUID design run titles. Nonconforming titles can map to log manifests that retired bash ignored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


