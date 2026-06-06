### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-codex-exec-auth.sh:55 / plan.txt:33-34
- **Concern**: Per-line linter scans all `scripts/*.sh` and `skills/*/scripts/*.sh` but plan leaves five already-wired launchers untouched with no pragma lines. Scenario: `make lint` / pre-commit fail on `launch-review.sh`, `launch-codex-ci.sh`, `launch-codex-implement.sh`, `check-reviewers.sh`, and `skills/review-and-fix/scripts/review-and-fix.sh` immediately after hook registration; contradicts "covered sites are untouched"
- **Proposed resolution**: Either add `### UPDATED` entries to place `# lint-codex-exec-auth: ok …` on each canonical `codex exec` line in those five files, or narrow the linter shell scope with an explicit allowlist for those canonical launcher surfaces

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-codex-exec-auth.sh:55-55
- **Concern**: New linter scans all scripts/*.sh for raw codex exec with per-line pragma only; plan leaves launch-review.sh launch-codex-ci.sh launch-codex-implement.sh check-reviewers.sh and skills/review-and-fix/scripts/review-and-fix.sh untouched yet expects zero violations. Scenario: Adding lint-codex-exec-auth to make lint and pre-commit fails immediately on six already-wired launcher/probe/coder scripts that must keep codex exec argv after run-external-agent --; contradicts Covered sites are untouched and Run make lint-codex-exec-auth against the swept tree zero violations expected
- **Proposed resolution**: Add an explicit wired-path basename allowlist in lint-codex-exec-auth.sh (and harness fixtures) for the canonical auth-wired launchers plus launch-codex-exec.sh itself; keep per-line pragma only for the intentional inline exception in scripts/run-negotiation-round.sh

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-codex-exec-auth.sh:55-55
- **Concern**: Linter scope hits already-auth-wired covered launchers but plan adds no suppressions. Scenario: `lint-codex-exec-auth` scans all `scripts/*.sh` and `skills/*/scripts/*.sh` with per-line-only pragmas and no file-scope exemption; plan leaves `launch-review.sh`, `launch-codex-ci.sh`, `launch-codex-implement.sh`, `check-reviewers.sh`, `skills/review-and-fix/scripts/review-and-fix.sh`, and post-wiring `run-negotiation-round.sh` untouched yet each still contains a literal `codex exec` dispatch line; `launch-codex-exec.sh` will too. Testing calls for zero violations repo-wide, but no file lists pragmas or allowlist exclusions for those sites.
- **Proposed resolution**: `make lint` / pre-commit fails immediately after merge despite the auth sweep being complete Add per-line `# lint-codex-exec-auth: ok …` on each remaining canonical `codex exec` line in the covered launchers plus negotiation, or extend `lint-codex-exec-auth.sh` with an explicit allowlist for those six paths (and document it in `lint-codex-exec-auth.md`); register the allowlist/pragma fixtures in `test-lint-codex-exec-auth.sh`

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-codex-exec-auth.sh:55
- **Concern**: Repo-wide linter has no exemption for already-wired launchers. Scenario: Plan adds lint-codex-exec-auth to make lint and expects zero violations, but leaves launch-review.sh, launch-codex-ci.sh, launch-codex-implement.sh, check-reviewers.sh, and skills/review-and-fix/scripts/review-and-fix.sh untouched; each still contains raw codex exec (check-reviewers uses CODEX_HOME=… codex exec, which the harness explicitly flags)
- **Proposed resolution**: make lint / pre-commit fails immediately after the sweep unless those sites get per-line # lint-codex-exec-auth: ok pragmas or the linter gains an explicit allowlist for those canonical wired paths (document the allowlist in lint-codex-exec-auth.md)

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements, Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-codex-exec-auth.sh:55
- **Concern**: Per-line linter conflicts with untouched blessed launcher scripts. Scenario: Plan leaves launch-review.sh launch-codex-ci.sh launch-codex-implement.sh and review-and-fix.sh untouched yet adds a shell rule that flags any non-comment line whose command word is codex exec without a per-line pragma. Those four scripts use continuation-line codex exec argv (no leading NAME=value skip). Testing strategy expects make lint-codex-exec-auth zero violations after the sweep so CI pre-commit fails immediately unless those files are edited with pragmas contrary to untouched contract or launch-codex-exec.sh is also flagged
- **Proposed resolution**: Add an explicit basename allowlist for already-wired dispatchers (launch-review.sh launch-codex-ci.sh launch-codex-implement.sh check-reviewers.sh review-and-fix.sh launch-codex-exec.sh) distinct from the forbidden file-scope external_prepare_codex_auth exemption document it in lint-codex-exec-auth.md and pin with a harness fixture that blessed launchers pass while helper-plus-raw-exec still fails

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/external-reviewers.md:114
- **Concern**: Negotiation exit-code doc target points at the wrong section. Scenario: Plan asks to update Negotiation Protocol exit-code prose at docs/external-reviewers.md line ~114 but that line is dialectic integration text negotiation exit codes live in skills/shared/external-reviewers.md:114 which the plan does not list under Files to modify Codex auth-prep exit 2 semantics may ship without updating the orchestrator-facing negotiation protocol readers use
- **Proposed resolution**: Move the exit-code update to skills/shared/external-reviewers.md:114 or add that file under UPDATED and keep docs/external-reviewers.md limited to the Codex auth scope paragraph at line ~12

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-sidecar-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/external-reviewers.md:114
- **Concern**: Negotiation Protocol exit-code prose is not in the plan's UPDATED file list. Scenario: Plan expands Codex auth-prep failure to exit 2 in run-negotiation-round.sh and says to update negotiation exit-code prose in docs/external-reviewers.md (~line 114), but that prose actually lives at skills/shared/external-reviewers.md:114 (loaded by /research). docs/external-reviewers.md:114 is dialectic content, not negotiation exit codes. After the PR, operators still read stale text: exit 2 = reviewer command failed only, with no Codex auth-setup branch
- **Proposed resolution**: Add skills/shared/external-reviewers.md to UPDATED files and revise line 114 to state exit 2 covers Codex auth setup failure or reviewer command failure; fix the docs/external-reviewers.md edit target (auth-scope paragraph ~line 12 only, not line 114 negotiation prose)

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-exit-grammar
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-review.sh:579-598, scripts/launch-codex-ci.sh:220, scripts/launch-codex-implement.sh:400, scripts/check-reviewers.sh:242, skills/review-and-fix/scripts/review-and-fix.sh:314, scripts/run-negotiation-round.sh:89
- **Concern**: Plan adds per-line-only lint-codex-exec-auth with no file-scope exemption but leaves six already-wired codex exec call sites untouched (five listed as covered plus run-negotiation inline path). Scenario: The harness and Testing strategy require make lint-codex-exec-auth over the real tree to pass after the sweep; those scripts still contain raw codex exec lines without the mandated pragma, so lint/pre-commit fails immediately even though the six targeted surfaces are fixed
- **Proposed resolution**: Add an explicit plan step: per-line # lint-codex-exec-auth: ok <reason> on each remaining wired codex exec in the five covered launchers and review-and-fix.sh, and on the stdin-pipe line in run-negotiation-round.sh after inline auth (or narrow the linter scope to exclude only those paths—contradicts the stated no-exemption rule)

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-lint-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:33-34,54-55
- **Concern**: Plan says five covered launchers stay untouched while the new linter scans scripts/*.sh and skills/*/scripts/*.sh with per-line pragma only and no file-scope exemption, but never states how those files pass. Scenario: Naive per-line matching flags continuation argv lines such as scripts/launch-review.sh:579,598 scripts/launch-codex-ci.sh:220 scripts/launch-codex-implement.sh:400 scripts/check-reviewers.sh:242 and skills/review-and-fix/scripts/review-and-fix.sh:314; the new scripts/launch-codex-exec.sh dispatch block has the same pattern; make lint-codex-exec-auth fails immediately after merge
- **Proposed resolution**: Document one mechanism in lint-codex-exec-auth.sh/.md: either a basename allowlist for the five canonical launchers plus launch-codex-exec.sh, or scanner logic that skips codex exec argv after run-external-agent.sh --; add a harness fixture pinning whichever rule is chosen
