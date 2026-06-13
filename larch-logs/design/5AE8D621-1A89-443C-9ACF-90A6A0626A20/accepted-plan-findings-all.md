### FINDING_1: Same-directory bare-basename rule will break `make lint-retired-scripts` on live `scripts/*.md`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-lint-scope
- **Severity**: important
- **Concern**: The plan extends `migration_lint.py` with same-directory markdown bare-basename matching but only remediates `classify-bump.md`. Many existing `scripts/*.md` contract docs already mention retired script basenames in the same directory (e.g. `scripts/implement-finalize.md`, `scripts/rebase-checkpoint-probe.md`, `scripts/run-step1-plan-log.md`, `scripts/lib-quiet.md`, `scripts/lib-phantom-probe.md`). After the new rule lands, `make lint-retired-scripts` in the plan's testing strategy will fail even after `classify-bump.md` is fixed. Non-goals forbid exclusion-list expansion, so the plan lacks an explicit triage or bulk-remediation step for these hits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an early lint-retired-scripts triage step and either budget bulk scripts/*.md fixes (python/cli.py paths or # lint-ignore), or [SCOPE-REDUCTION] narrow the rule (e.g. only when the markdown file stem matches the retired script stem) if cross-name hits like release-prepare.sh in classify-bump.md stay a one-off doc edit
  - From Cursor-Requirements: Add an explicit step: run make lint-retired-scripts, triage same-directory hits under scripts/, and either add end-of-line # lint-ignore on intentional historical migration prose or replace with python/cli.py verbs where one-to-one; do not leave the test target failing
  - From Cursor-dyn-lint-scope: After classify-bump.md is fixed the plan still runs make lint-retired-scripts but scripts/lib-quiet.md scripts/implement-finalize.md scripts/run-step1-plan-log.md and others in scripts/ contain bare basenames of retired scripts in the same directory (e.g. redact-secrets.sh local-cleanup.sh larch-log.sh). A repo scan shows 76 such hits under scripts/*.md versus 4 hits under .claude/skills/**/*.md all in classify-bump.md Narrow bare-basename markdown matching to .claude/skills/** (or explicitly exclude scripts/*.md contract docs). Add a regression test that scripts/lib-quiet.md prose mentioning redact-secrets.sh stays clean while classify-bump.md bare mentions still fail


### FINDING_2: `verify_main` may double-append `(#N)` when `--expected-title` already includes a PR suffix
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-lint-scope, Cursor-dyn-verify-shared-helper
- **Severity**: important
- **Concern**: The plan extracts a shared `_title_matches` helper but does not define how callers pass `expected` when it already contains a trailing `(#N)`. `implement-finalize.sh` passes `--expected-title "Title (#N)"` as one string while also supplying `pr_number`. `finalize.postmerge` passes title-only plus separate `pr_number`. A naive port that always builds `f"{expected} (#{pr_number})"` yields `"Title (#42) (#42)"` and breaks suffix/prefix checks, causing `test_verify_main_direct_title_and_suffix` and bash Step 15 to disagree with postmerge behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Document that verify_main must pass the bare PR title (suffix stripped) and pr_number separately to finalize._title_matches; add a unit test with --expected-title "Title (#7)" and commit subject "Title (#7)"
  - From Cursor-dyn-lint-scope: implement-finalize.sh passes PR_TITLE (#PR_NUMBER) as one string. finalize.postmerge uses pr_title without suffix plus separate pr_number. If verify_main forwards the full string and extracted pr_number the helper can build Implement thing (#7) (#7) or reject valid suffix-only matches from test_verify_main_direct_title_and_suffix In verify_main.py strip trailing (#N) from expected to get the base title then call finalize._title_matches(commit_message base_title pr_number). Add a test where expected includes (#N) and helper must not double-append
  - From Cursor-dyn-verify-shared-helper: Document helper contract: strip a trailing (#N) from expected before composing expected_with_number when pr_number is also set (or have verify_main pass title-only plus pr_number). Add one parametrized case where expected already ends with (#N) and pr_number is also passed


### FINDING_4: No test that `# lint-ignore` suppresses bare-basename only, not full-path matches
- **Reviewer(s)**: Cursor-dyn-lint-scope
- **Severity**: important
- **Concern**: Plan edge cases require full-path matches to report even when `# lint-ignore` is present on the line. Without a test, an implementer could short-circuit on `lint-ignore` before the full-path check and mask real stale references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-lint-scope: Edge cases at plan.txt:103-104 require full-path matches to report even with # lint-ignore. Without a test an implementer could short-circuit on lint-ignore before the full-path check and mask real stale references Add test: same-directory markdown line like scripts/foo.sh # lint-ignore with bare foo.sh exits 0 but line scripts/foo.sh # lint-ignore exits 1


### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/migration_lint.py:51-72; scripts/check-main-sync.md:78-80
- **Concern**: [SCOPE-REDUCTION] The planned same-directory markdown basename check is broader than the intended cleanup and will sweep top-level scripts docs.. Scenario: Because every top-level scripts/*.md file is in the same directory as many retired scripts/* entries, the proposed lint would flag existing refs such as local-cleanup.sh in scripts/check-main-sync.md and many similar contract docs. make lint-retired-scripts would fail unless this PR expands into a broad unrelated doc cleanup.
- **Proposed resolution**: Narrow the bare-basename rule so this PR only covers the targeted stale release prose, or explicitly add all newly exposed same-directory markdown cleanup if the broad lint is intentional.


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/migration_lint.py:60-82
- **Concern**: [SCOPE-REDUCTION] Same-directory bare-basename markdown rule has no live-sibling guard. Scenario: After the matcher lands, many tracked scripts/*.md contract docs (e.g. scripts/rebase-checkpoint-probe.md:15, scripts/lib-phantom-probe.md:7, scripts/render-session-transcript.md:60) sit in scripts/ and mention retired peers by bare basename such as append-execution-issue.sh; rel_dir equals retired_dir for both sides, so make lint-retired-scripts exits 1 repo-wide even once classify-bump.md is fixed
- **Proposed resolution**: Only enable the bare-basename branch when the hosting markdown has no live sibling .sh on disk (Path(rel).with_suffix('.sh') missing); that targets orphan docs like .claude/skills/release/scripts/classify-bump.md without sweeping live contract docs; add a regression test pairing a live foo.md/foo.sh stub with a bare retired basename mention that must stay clean


### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/migration_lint.py:60-82
- **Concern**: [SCOPE-REDUCTION] Same-directory bare-basename lint overreaches for top-level scripts docs. Scenario: The planned rel_dir == retired_dir rule makes every scripts/*.md file same-directory with every retired scripts/*.sh entry. Existing docs such as scripts/check-main-sync.md:78-80 mention local-cleanup.sh as prose, so make lint-retired-scripts would start failing even though the plan only updates classify-bump.md.
- **Proposed resolution**: Narrow the bare-basename rule so it does not apply to top-level scripts/ markdown, or scope it to the release skill directory this cleanup updates. Keep full-path and $SCRIPT_DIR checks unchanged.


### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/migration_lint.py:60-82
- **Concern**: [SCOPE-REDUCTION] Planned same-directory basename lint has unplanned repo-wide fallout. Scenario: The proposed rule would flag existing tracked markdown beyond classify-bump.md, for example scripts/implement-finalize.md:95 and scripts/launch-cursor-implement.md:7 mention retired bare .sh names in the same scripts/ directory. The plan only updates classify-bump.md, so make lint-retired-scripts can fail after the proposed change.
- **Proposed resolution**: Before enabling the rule, inventory the exact new matches and either update or add line-level # lint-ignore for every legitimate existing hit in this PR, or narrow the matcher enough that the planned lint target stays clean.


### FINDING_9:
- **Reviewer(s)**: Codex-dyn-lint-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:17-25; python/migrated-scripts.tsv:24-29; scripts/lib-phantom-probe.md:7-11; scripts/dispatch-code-voters.md:59-63
- **Concern**: [SCOPE-REDUCTION] Same-directory markdown basename matching is still too broad for the current repo. Scenario: `python/migrated-scripts.tsv` retires `scripts/append-execution-issue.sh` and `scripts/append-tool-failure.sh`, while live same-directory markdown under `scripts/` mentions those bare basenames. The proposed `rel_dir == retired_dir` markdown rule would flag those lines, so `make lint-retired-scripts` can fail after this plan even though the plan only updates `.claude/skills/release/scripts/classify-bump.md`.
- **Proposed resolution**: Narrow the bare-basename rule before enabling it. Keep it on the release markdown surface needed for this issue, or otherwise exclude/ignore the existing top-level `scripts/*.md` historical prose so the lint target stays clean without repo-wide doc churn.




### FINDING_1: Unified `_title_matches` may drop verify_main prefix matching
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: A shared `_title_matches` contract may omit verify_main's `startswith` semantics on the caller-normalized expected string when `pr_number` is None. After consolidation, verify_main could reject commits that pass today (e.g. `--expected-title "Feature"` with subject `"Feature follow-up"`) because postmerge-style logic only exact-matches the bare expected title and never applies prefix matching on the unnumbered title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify _title_matches as the union of both call sites: keep verify_main-style startswith on the caller-normalized expected string when pr_number is None; retain postmerge exact/in/numbered-startswith/suffix rules when pr_number is set; add a unit test for prefix-only title match without a PR suffix


### FINDING_2: Unified `_title_matches` may adopt postmerge mid-string PR-suffix matching
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: A shared `_title_matches` may adopt postmerge suffix-in-subject matching instead of verify_main's endswith-only PR-suffix fallback. After unification, verify_main could return `VERIFIED=true` when HEAD subject contains `(#N)` mid-string but not at the end (e.g. `"(#42) Feature title"`), while today's verify_main returns false; `scripts/implement-finalize.sh` Step 15 treats `VERIFIED=true` as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Preserve verify_main's current endswith-only PR-suffix branch when calling the helper from verify_main, or add an explicit parity test for this edge case and document the intentional behavior change


### FINDING_5: Tests omit backtick-wrapped bare basenames
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Planned tests omit backtick-wrapped bare basenames, the dominant stale pattern in `classify-bump.md`. A boundary regex that only treats ASCII word edges may miss or mis-handle `` `classify-bump.sh` `` / `` `release-prepare.sh` `` in backticks; the doc fix could ship while the lint rule still misses equivalent stale prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a fixture mirroring classify-bump.md backtick-wrapped retired basenames in same-directory orphan markdown (flag without lint-ignore, clean after doc rewrite)


### FINDING_6: Orphan-markdown bare-basename guard underspecified for `scripts/*.md` contract docs
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The orphan-markdown bare-basename guard is underspecified for existing `scripts/*.md` contract docs. With the planned rules (markdown, same directory as retired script, no live sibling `.sh` at the md path), at least `scripts/render-session-transcript.md:60` (bare `append-execution-issue.sh`) and `scripts/lint-literal-counts.md:3` (bare `test-lint-skill-invocations.sh`) would still be flagged; both md files lack a live same-stem `.sh` sibling. The plan's Testing strategy requires `make lint-retired-scripts` to pass and only says to fix the matcher guard without naming these files or an exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit remediation: e.g. scope bare-basename matching to .claude/skills/**/*.md only, or document per-line # lint-ignore on those two contract lines, or require updating those two prose references to non-retired Python entrypoints; add a regression test fixture mirroring at least one of these production shapes


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/migration_lint.py:60-83
- **Concern**: [SCOPE-REDUCTION] Same-directory orphan-markdown bare-basename rule also matches orphan scripts/*.md that cite retired shell names in historical prose. Scenario: After the matcher lands, make lint-retired-scripts will flag scripts/render-session-transcript.md:60 (append-execution-issue.sh) and scripts/lint-literal-counts.md:3 (test-lint-skill-invocations.sh); those files are not in the plan and will block the PR testing gate
- **Proposed resolution**: Restrict the new bare-basename branch to dev skill doc paths (e.g. only .claude/skills/** orphan markdown), or add explicit plan steps to update/lint-ignore those two scripts/*.md files before the final lint run


### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/migration_lint.py:60-82; scripts/lint-literal-counts.md:3; scripts/render-session-transcript.md:60
- **Concern**: [SCOPE-REDUCTION] Proposed same-directory/no-live-sibling bare-basename branch still covers live top-level scripts/*.md contract docs. Scenario: scripts/lint-literal-counts.md mentions retired test-lint-skill-invocations.sh and scripts/render-session-transcript.md mentions retired append-execution-issue.sh; both are same-directory scripts/ markdown files without matching live .sh siblings, so make lint-retired-scripts would fail or force out-of-scope doc edits
- **Proposed resolution**: Tighten the bare-basename eligibility so the targeted orphan release skill prose is covered while current live top-level scripts/*.md contract docs stay out of the new branch; keep full-path and $SCRIPT_DIR checks unchanged




### FINDING_1: Plan omits `repo_root` for live-sibling `.sh` guard in `migration_lint`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds a bare-basename / live-sibling `.sh` guard that must resolve paths as `repo_root / Path(rel).with_suffix(".sh")`, but it does not thread `repo_root` (or `root_path` from `main()`) into `_line_references_retired()` or its `main()` call site. Without that parameter and wiring, an implementer may omit the guard, re-resolve root incorrectly, or call `.exists()` on a repo-relative path without joining `root_path`. The live-sibling exemption can then be wrong under non-root cwd, always false, or otherwise break the contract that markdown with a live sibling `.sh` stays clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add repo_root: Path to _line_references_retired(), pass root_path from the main() scan loop, and document that the dev-skill basename helper depends on it
  - From Cursor-Pragmatic: Add `repo_root: Path` to `_line_references_retired()`, pass `root_path` from the `main()` loop, and state that requirement explicitly in the `python/migration_lint.py` plan section.


### FINDING_2: `postmerge()` may omit `pr_number` when calling `_title_matches()`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan is ambiguous about `pr_number` when `postmerge()` calls `_title_matches()`. It says postmerge should use helper defaults but also preserve suffix logic driven by `ctx.pr_number`. If `postmerge()` calls `_title_matches(actual, expected_title)` without `pr_number=ctx.pr_number`, numbered-title and `(#N)` suffix behavior can diverge from today's `title_ok` block and flip `verify_main_status` on squash-merge titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: State explicitly that `postmerge()` calls `_title_matches(actual, expected_title, ctx.pr_number)` and that defaults apply only to `allow_plain_prefix=False` and `suffix_match="contains"`.


### FINDING_3: Shared helper may broaden `verify_main` prefix matching vs current CLI
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned helper can broaden verify-main prefix matching after stripping a trailing PR number. Current CLI checks `commit_message.startswith(raw expected)`. The plan strips `Title (#7)` to `Title`, then calls `_title_matches` with `allow_plain_prefix=True`, so `--expected-title "Title (#7)"` may incorrectly verify `"Title follow-up"`; this violates the plan goal to keep current CLI edge-case behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Preserve the raw expected-title prefix check for verify_main, or only enable plain-prefix matching when the raw expected title has no trailing (#N). Add the missing negative test for --expected-title "Title (#7)" with commit subject "Title follow-up".



