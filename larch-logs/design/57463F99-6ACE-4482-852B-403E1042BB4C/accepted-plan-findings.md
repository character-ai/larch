### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/gh-body-file.md:54-58
- **Concern**: Unqualified mandate to route every gh pr create through scripts/create-pr.sh. Scenario: design-log-publish.sh must call gh pr create --head from a disposable worktree after its own push; create-pr.sh uses the current branch symbolic-ref and existing-PR fast-path (documented in scripts/design-log-publish.md:47-48)
- **Proposed resolution**: Qualify the rule: create-pr.sh for normal implement/ship flows; direct gh pr create --body-file only when a worktree script already pushed an explicit --head branch (cite design-log-publish as the canonical exception)


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:986-991
- **Concern**: Proposed rule conflicts with an existing normative /design instruction that still requires inline gh issue comment --body. Scenario: The new .claude/rules/gh-body-file.md would say inline --body values are forbidden while /design Step 5d still says the --body argument MUST be a fixed literal and shows an inline --body command, leaving maintainers with contradictory standards after the PR lands
- **Proposed resolution**: Update Step 5d to write the fixed literal to a temp file under DESIGN_TMPDIR and invoke gh issue comment --body-file, preserving the same guards and redaction/security rationale


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/report-tokens/scripts/run-analysis.sh:1022-1035
- **Concern**: The plan misses an actual gh issue create --body call site outside the proposed rule frontmatter. Scenario: After this PR lands, /report-tokens can still post a generated analysis issue via inline --body, so the repository will not satisfy the new file-backed-only standard and future edits to that script will not receive the path-triggered reminder
- **Proposed resolution**: Migrate create_report_issue to write the body to a tempfile and pass --body-file, clean it in a finally block, and add skills/report-tokens/scripts/run-analysis.sh plus its SKILL/contract docs to the rule paths if the standard is meant to cover all gh body producers


### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:985-991
- **Concern**: Proposed rule bans all inline `--body` but Step 5d normative snippet still uses inline `--body`. Scenario: `skills/design/SKILL.md` is in the rule `paths:` list; editing or running `/design` injects a flat ban while Step 5d still shows `gh issue comment … --body '…'` as the only allowed invocation
- **Proposed resolution**: Extend the plan to rewrite Step 5d to write the fixed literal into a temp file (or `$DESIGN_TMPDIR/…`) and call `--body-file`, or add an explicit, narrow exception in the rule for this security-pinned literal and align the snippet


### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:986-991
- **Concern**: Plan adds a rule forbidding inline gh --body but leaves an existing skill step that explicitly mandates inline --body. Scenario: After the PR lands, opening skills/design/SKILL.md triggers the new rule while the same file still instructs the opposite fixed-literal inline command, so /design Step 5d can continue producing the forbidden pattern
- **Proposed resolution**: Update Step 5d to write the fixed literal to a temp/body file and call gh issue comment --body-file, while preserving the no-dynamic-content security constraint


### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .claude/rules/gh-body-file.md:4-25
- **Concern**: Planned frontmatter omits existing gh body caller surfaces covered by the rule text. Scenario: The rule text covers gh issue create/comment, but current callers such as skills/issue/scripts/create-one.sh:253-259 and scripts/tracking-issue-summary.sh:73-80 would not receive the reminder during future edits, allowing silent regression back to inline --body
- **Proposed resolution**: Add all existing gh --body-file/--notes-file caller surfaces and their docs to paths, or use a broader scripts/skills path glob if the intended invariant is repository-wide


### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:986-991
- **Concern**: Proposed rule bans all inline --body/--notes but Step 5d documents gh issue comment with inline --body and SECURITY.md:135 requires a fixed literal (no dynamic session material) for upstream anti-exfiltration. Scenario: Editing design/SKILL.md injects a rule that contradicts the same file and SECURITY; implementers may "fix" Step 5d to --body-file from plan.txt and reintroduce injection risk
- **Proposed resolution**: Add a narrow exception in the rule (and Scope) for SECURITY-documented fixed literals, or migrate Step 5d to --body-file on a committed constant file (e.g. skills/design/references/l3-velocity-deferral-comment.txt) and update SECURITY.md in the same PR


### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:986-991
- **Concern**: Proposed rule conflicts with an existing security-pinned inline --body instruction. Scenario: The new rule includes skills/design/SKILL.md and forbids every inline --body, but Step 5d still says the --body argument MUST be a fixed literal; after landing, the same skill gives contradictory instructions and leaves one live inline gh body path
- **Proposed resolution**: Rewrite Step 5d to write the fixed literal to a temp/body file and call gh issue comment --body-file, preserving the no-dynamic-material security invariant


### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/audit-runs/scripts/audit-close-priors.sh:55; skills/report-tokens/scripts/run-analysis.sh:1031
- **Concern**: The grep audit missed current inline gh --body call sites. Scenario: The PR would land with remaining inline --body uses, including report-tokens posting markdown/JSON through argv, which is close to the original failure class; the new rule frontmatter also omits these files so edits there will not receive the reminder
- **Proposed resolution**: Migrate these call sites to --body-file and add their SKILL/script/md paths to the rule frontmatter, or add an explicit documented exemption if any caller truly must remain inline


### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:447-463
- **Concern**: The proposed post-push mktemp/write path is unguarded under set -e. Scenario: If TMPDIR is unavailable after git push succeeds, the script can exit non-zero before emitting PUBLISH_OK=false or RECOVERY_BRANCH, leaving a pushed branch without the normal recovery contract
- **Proposed resolution**: Create the PR body file before pushing, or guard mktemp/printf failures and emit the existing structured failure output with RECOVERY_BRANCH when PUSH_DONE=true


### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/gh-body-file.md:54-56 (proposed);scripts/design-log-publish.md:47-48
- **Concern**: Rule requires all gh pr create to use create-pr.sh but design-log-publish intentionally uses raw gh pr create. Scenario: Editors of design-log-publish.sh (in paths:) get a rule that contradicts the documented disposable-worktree PR path and may wrongly route through create-pr.sh (existing-PR fast-path / assignee / push semantics)
- **Proposed resolution**: Qualify Required pattern: create-pr.sh for interactive/implement PRs; exempt scripts/design-log-publish.sh (documented direct gh pr create --body-file on disposable branch)


### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/gh-body-file.md:24-26 (proposed); scripts/design-log-publish.md:47-49
- **Concern**: Proposed rule says every gh pr create in this repo must use scripts/create-pr.sh, but the same plan keeps design-log-publish.sh on direct gh pr create and its contract says not create-pr.sh.. Scenario: Future edits to design-log-publish.sh will receive contradictory guidance and may replace its specialized disposable-worktree push/PR/admin-merge flow with the generic wrapper, breaking recovery and merge behavior.
- **Proposed resolution**: Narrow the rule wording to normal assistant-authored PR creation, or explicitly carve out design-log-publish.sh as direct gh pr create --body-file; update scripts/design-log-publish.md if body-file becomes part of the contract.


### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:986-991; SECURITY.md:135
- **Concern**: The plan bans inline --body but leaves /design Step 5d requiring a fixed literal inline --body, with SECURITY.md documenting that invariant.. Scenario: After landing, /design Step 5d either violates the new rule or silently changes a security-relevant public-comment boundary without updating the security docs.
- **Proposed resolution**: Migrate Step 5d to write the fixed literal to a temp file and post --body-file, preserving the no-dynamic-content rule; update SECURITY.md to describe fixed literal file-backed posting and cleanup.


### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:1024-1034; skills/report-tokens/scripts/run-analysis.md:39
- **Concern**: The grep audit missed a Python gh issue create --body call in /report-tokens, and the proposed rule path list omits that script.. Scenario: /report-tokens can still send a large markdown plus JSON report through inline argv, preserving the exact body/argument fragility the rule is meant to eliminate.
- **Proposed resolution**: Migrate create_report_issue to write body to a temp file and pass --body-file; add skills/report-tokens/scripts/run-analysis.sh and its sibling .md to the rule paths or update the rule scope to explain the exclusion.


### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/test-design-log-publish.sh:234-235
- **Concern**: The plan changes design-log-publish.sh argv shape but intentionally leaves the existing gh-stub harness without an assertion for --body-file.. Scenario: The migration can accidentally keep inline --body, pass both flags, or regress later while the publish harness still passes because it only checks that pr create ran.
- **Proposed resolution**: Add a focused assertion that the logged pr create argv contains --body-file and does not contain inline --body; optionally verify the body-file payload equals the expected text.


### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:986-991
- **Concern**: Proposed rule flat-bans all inline `--body` but Step 5d still requires inline `--body` for a SECURITY.md-pinned literal; `skills/design/SKILL.md` is in the rule `paths:` list. Scenario: After merge, editing `/design` injects a rule that forbids the exact Step 5d snippet agents are told they MUST run; reviewers may also flag the live inline call as violating Decision 4
- **Proposed resolution**: Migrate Step 5d to write the fixed literal to `$DESIGN_TMPDIR/gh-l3-velocity-comment.md` (or similar) and use `--body-file`, or add an explicit rule exception for SECURITY.md-documented pinned literals and update Step 5d prose to match


### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:986-991; SECURITY.md:135
- **Concern**: Plan leaves an existing prompt-authored `gh issue comment --body` path untouched despite the stated all `gh ... --body`/`--notes` file-backed requirement. Scenario: After the PR lands, /design Step 5d still teaches and runs the inline `--body` pattern the new rule is meant to ban, including on a public upstream comment path
- **Proposed resolution**: Update the plan to migrate Step 5d to write the fixed literal to a `$DESIGN_TMPDIR/...md` file and call `gh issue comment ... --body-file`, preserve the fixed-literal/no-dynamic-material guard, and update SECURITY.md wording


### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/tracking-issue-summary.sh:73-80; scripts/tracking-issue-summary.md:1-12
- **Concern**: Rule frontmatter path list omits an existing `gh issue comment --body-file` helper and its sibling contract. Scenario: Editing tracking-issue-summary later will not inject the new rule even though it owns GitHub comment body composition, so the path-trigger surface is incomplete relative to the all `gh --body`/`--notes` scope
- **Proposed resolution**: Add `scripts/tracking-issue-summary.sh` and `scripts/tracking-issue-summary.md` to the rule paths or explicitly justify why this body-writing helper is excluded


### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:234-235
- **Concern**: Testing strategy says no new tests and the existing design-log harness only checks `pr create`/`pr merge`, not that PR creation uses `--body-file` with the intended content. Scenario: The central acceptance criterion can regress from `--body-file` back to inline `--body` while `test-design-log-publish` still passes; the new rule's path inventory also has no automated validation
- **Proposed resolution**: Add an assertion in the gh stub/harness that `pr create` receives `--body-file`, reads the file, and does not receive `--body`; add a small static grep/lint check for inline `gh ... --body`/`--notes` on the covered surfaces if feasible


### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: .claude/rules/script-md-siblings.md:7-12; scripts/design-log-publish.md:1-72
- **Concern**: Plan changes `scripts/design-log-publish.sh` behavior but is silent on its sibling `.md` contract. Scenario: The repository's script sibling rule requires the contract doc to be updated in the same PR as behavior changes, so implementation can pass functional checks while violating repo authoring constraints
- **Proposed resolution**: Add `scripts/design-log-publish.md` to UPDATED and note the PR body is now written to a temp file and passed with `--body-file`, including cleanup expectations


### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:460-463
- **Concern**: Plan claims the migrated PR body text is byte-identical, but the proposed `printf ...\n` writes a trailing newline absent from the current inline `--body` argument. Scenario: Exact body comparisons or reviewer expectations can disagree with the stated no-content-change claim
- **Proposed resolution**: Use `printf 'Automated design log directory for run %s. Commit uses [skip ci].' "$RUN_ID" > "$PR_BODY_TMP"` or revise the plan to say the body is content-equivalent rather than byte-identical


### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-path-inventory
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:1031-1034
- **Concern**: Runtime `gh issue create` uses Python `--body` with a large dynamic analysis string; path not in proposed `paths:`. Scenario: Grep audit missed this caller; rule never injects when editing run-analysis; large bodies can hit argv limits and reintroduce #2830-class quoting risk
- **Proposed resolution**: Add `skills/report-tokens/scripts/run-analysis.sh` and `skills/report-tokens/scripts/run-analysis.md` to frontmatter; switch to temp file + `--body-file` (mirror create-one.sh)


### FINDING_24:
- **Reviewer(s)**: Codex-dyn-path-inventory
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:123-129; skills/report-tokens/scripts/run-analysis.sh:1024-1034; .claude/skills/audit-runs/scripts/audit-close-priors.sh:54-55
- **Concern**: Plan inventory misses current inline gh --body callers outside the proposed frontmatter. Grep finds no live heredoc-in-substitution caller, but these two inline callers are absent while the plan only migrates scripts/design-log-publish.sh and asserts the rest of the codebase already uses --body-file.. Scenario: Because the new rule fires only on listed paths, edits to these files silently miss the reminder and current inline gh issue bodies remain after the PR lands.
- **Proposed resolution**: Migrate both callers to write a body file and pass --body-file, then add their paths to frontmatter or explicitly document a narrower exclusion; at minimum include the runtime skills/report-tokens path.


### FINDING_25:
- **Reviewer(s)**: Codex-dyn-path-inventory
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:986-991; SECURITY.md:135; plan.txt:39-65
- **Concern**: Proposed flat ban conflicts with an included security-sensitive design skill path that explicitly requires a fixed literal inline --body. SECURITY.md also documents that fixed literal contract, but the plan neither migrates nor updates it.. Scenario: After landing, opening skills/design/SKILL.md injects a rule that contradicts the skill’s own Step 5d and security contract, so authors may either leave a known violation or change the comment path without updating the public-boundary guidance.
- **Proposed resolution**: Revise Step 5d to write the fixed literal to a temp file and invoke gh issue comment with --body-file, then update SECURITY.md; alternatively add a narrow explicit exception and remove the “flat ban” wording.


### FINDING_26:
- **Reviewer(s)**: Codex-dyn-path-inventory
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .github/workflows/release-tag.yaml:102-104; scripts/tracking-issue-summary.sh:80; skills/review-and-fix/scripts/review-and-fix.sh:691-692
- **Concern**: Current compliant gh --notes-file and --body-file callers are also absent from the proposed paths list, despite the plan saying the list was grep-discovered and the rule text explicitly covering gh release create --notes.. Scenario: The rule will not fire on several existing body/notes publication surfaces, so future edits to those current callers can regress to inline --body or --notes without seeing the new reminder.
- **Proposed resolution**: Add the current compliant gh body/notes caller paths to frontmatter or narrow the rule text and plan claim to the intentionally covered subset.


### FINDING_27:
- **Reviewer(s)**: Codex-dyn-path-inventory
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:61-65; plan.txt:135
- **Concern**: No --body-file - or --notes-file - usage appears in the current repo, but the proposed “value MUST come from a file” and “--body-file <path>” wording would accidentally forbid stdin even though the plan’s own failure-mode section calls that out.. Scenario: A future legitimate stdin use such as gh issue comment --body-file - would be treated as noncompliant by the rule despite avoiding inline shell quoting.
- **Proposed resolution**: Either explicitly allow --body-file - and --notes-file - as stdin-backed accepted patterns or state that stdin is intentionally disallowed.


### FINDING_28:
- **Reviewer(s)**: Cursor-dyn-trap-lifecycle
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:144-152
- **Concern**: Plan omits trap-safe error suppression on proposed PR_BODY_TMP rm inside wt_cleanup. Scenario: Adjacent ENUM cleanup uses rm -f … 2>/dev/null || true (line 145); a bare [ -n … ] && rm -f "$PR_BODY_TMP" can return non-zero on permission or odd FS errors and, under set -e, abort wt_cleanup before worktree removal (lines 146-151)
- **Proposed resolution**: Mirror line 145: [ -n "${PR_BODY_TMP:-}" ] && rm -f "$PR_BODY_TMP" 2>/dev/null || true; optionally set PR_BODY_TMP="" after the explicit post-gh rm (ENUM_TOP_TMP="" pattern at line 287)


### FINDING_29:
- **Reviewer(s)**: Codex-dyn-trap-lifecycle
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:458-482
- **Concern**: Proposed temp body cleanup removes PR_BODY_TMP after gh pr create but leaves the variable non-empty until the EXIT trap is cleared. Scenario: If gh pr create returns non-zero, the planned explicit rm runs, then the PR lookup failure path exits at current line 482 before trap clearing at line 494; wt_cleanup then runs rm -f on the same stale path a second time
- **Proposed resolution**: Add PR_BODY_TMP="" immediately after the explicit rm -f "$PR_BODY_TMP" so later trap cleanup only handles files that still need cleanup; keep the [ -n "${PR_BODY_TMP:-}" ] guard in wt_cleanup for the mktemp-never-reached case


