### FINDING_1: **Important** risk-integration: Makefile:15 wires `lint-bash32` only into the aggregate `make lint`, but CI does not run that target; `.github/workflows/ci.yaml:52-63` runs `make lint-only`, and `.github/workflows/ci.yaml:186-187` runs only the harness shards. Concrete scenario: a later PR adds `declare -A cache` to `scripts/foo.sh`; CI runs pre-commit plus `test-lint-bash32`, but never runs the full-tree `scripts/lint-bash32.sh`, so the Bash-4-only construct can merge and then fail for consumers on macOS Bash 3.2. Fix by adding a CI step/target that runs `make lint-bash32` over the full repo, or by making one CI shard depend on `lint-bash32` instead of only `test-lint-bash32`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** risk-integration: Makefile:15 wires `lint-bash32` only into the aggregate `make lint`, but CI does not run that target; `.github/workflows/ci.yaml:52-63` runs `make lint-only`, and `.github/workflows/ci.yaml:186-187` runs only the harness shards. Concrete scenario: a later PR adds `declare -A cache` to `scripts/foo.sh`; CI runs pre-commit plus `test-lint-bash32`, but never runs the full-tree `scripts/lint-bash32.sh`, so the Bash-4-only construct can merge and then fail for consumers on macOS Bash 3.2. Fix by adding a CI step/target that runs `make lint-bash32` over the full repo, or by making one CI shard depend on `lint-bash32` instead of only `test-lint-bash32`.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: .claude-plugin/plugin.json; larch-logs/implement/*; version bump commits
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Version bumps and implement run logs ride along the branch Expected repo workflow noise for this plugin, not bash32 plan incompleteness No action required for plan fidelity
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: branch commits (e.g. e9a74a2d a83cd1dc 8ea4de6c)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Version bump and larch-logs flush commits ride with bash32 work; orthogonal to bash32 test coverage. Reviewer noise when reading PR scope only; no bash32 CI gap by themselves. None required for bash32 feature; optional history cleanup for PR authors.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: larch-logs/implement/* flush
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Large implement run logs committed By design per docs/run-logs.md; optional path scrub policy only if org requires cleaner archives N/A unless policy changes
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: .git history e9a74a2d a83cd1dc
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Standalone version bump commits appear in the same branch range as the portability work. PR reviewers see extra noise unrelated to bash32 semantics. No code change required for bash32 feature; optional branch hygiene only.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/review-core.sh:327-373 (cited in logs)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] NOT_SUBSTANTIVE visibility on zero-findings path may remain unresolved Only noted via larch-logs review text in this diff bundle; not re-derived from minimal code read here Confirm in a follow-up code pass if review-core changed outside logs
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: implementation_plan scope vs branch diff (scripts/collect-agent-results.sh, scripts/dispatch-code-voters.sh, scripts/launch-claude-review.sh, skills/review/scripts/*.sh and tests)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Large unrelated collector retry, voter dispatch, Claude launcher role, and review harness changes bundled with Bash 3.2 lint work Reviewers expect a bash32-only PR; mixed semantics increase regression and rollback risk and violate the stated implementation_plan file list Split unrelated changes into their own PR or update the authoritative plan/requirements to include them
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: Makefile:15
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] make lint orders test-harnesses before lint-bash32. Local contributor waits through full harness fan-out before a trivial Bash 4 typo fails at lint-bash32. Reorder lint target or document expected slow path for bash32-only edits.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/collect-agent-results.sh;scripts/dispatch-code-voters.sh:6196-6210;scripts/launch-claude-review.sh:6324-6361
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Branch diff bundles large collector retry / voter context behavior changes not named in the bash32 implementation plan. Reviewers cannot validate bash32 isolation; rollback or bisect ties unrelated runtime behavior to the portability lint. Split unrelated work into separate PRs/commits or expand the authoritative plan/issue to list every touched subsystem.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/lint-bash32.md:3
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract says tracked-only shell files but git enumeration includes untracked non-ignored scripts. A contributor expects only staged paths to matter and is surprised when an untracked local .sh fails lint. Align wording with git ls-files --cached --others --exclude-standard semantics.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/lint-bash32.sh:75-76
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Substring lint-bash32: ok skips the full physical line. A malformed or accidental ok token could hide a real violation on the same line. Tighten suppression anchoring or document whole-line waiver discipline.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/test-lint-bash32.sh:105
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Obscure double-quote escaping for the &>> needle. Future edits may corrupt quoting and silently weaken the regression assertion. Use a single-quoted literal needle for readability.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/collect-agent-results.sh:1140-1146
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Section 3.7 NS retry requires SUBSTANTIVE_VALIDATION=true but structured validation can run alone. Caller passes only --structured-reviewer-validation; 3.6 emits NOT_SUBSTANTIVE with NS_RETRY_MODE=structured but 3.7 never runs; no retry despite metadata implying one. Extend 3.7 guard, require paired flags, or drop NS_RETRY_MODE when substantive validation is off.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/lint-bash32.sh:66-85
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Linter skips symlink targets, misses anonymous coprocs, and suppresses any line containing lint-bash32: ok substring. Tracked symlinked script bypasses scan; coproc { ... } slips through; accidental substring in a string silences real Bash 4 tokens on the same line. Follow symlink targets or lint referents; broaden coproc detection if needed; anchor suppression comments.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/lint-bash32.sh:81
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Case-conversion awk only matches ^^ and ,, not single ^ or ,. ${var^} or ${var,} slips past lint-bash32 while still requiring Bash 4+. Extend regex, BASH_AUTHORING.md, and test-lint-bash32.sh for single-caret/comma forms.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/lint-bash32.sh:85
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Named-coproc-only regex misses anonymous coproc forms. A Bash-4-only anonymous coproc slips past lint and breaks on macOS Bash 3.2 at runtime. Extend detection or explicitly document the unsupported coproc subset.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/lint-bash32.sh:85
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Named coproc pattern misses anonymous coproc { ... }. Anonymous coproc is incompatible with Bash 3.2 but passes the linter. Add coproc-before-{ detection and regression cases (or narrow docs if intentional).
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/test-collect-agent-results.sh (C_IT1 OUT_IT1 heredoc per diff hunk @@ -238,27 +260,71 @@)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] C_IT1 fixture body replaced with meta prose and an example TSV block unrelated to collector behavior Fixture no longer encodes a deliberate substantive-output scenario; future validation changes may bake accidental content into expectations Restore an intentional synthetic reviewer output (or co-update tests and documentation if the scenario changed on purpose)
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/test-lint-bash32.sh:105
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Needle for &>> rule does not match scripts/lint-bash32.sh:84 stderr text assert_case uses a garbled substring versus &>> append-all redirection; redirect rule may be untested Fix quoting use single-quoted needle or match exact linter message bytes
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: .github/workflows/ci.yaml:52-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] CI lint job never runs make lint-bash32; only local make lint does. A PR can merge Bash 4+ syntax into tracked *.sh; test-lint-bash32 fixtures still pass; full-tree bash32 guard from feature_description is not enforced on CI. Add make lint-bash32 (or equivalent pre-commit hook) to CI and document it in docs/linting.md CI section.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: .github/workflows/ci.yaml:63 and .claude/skills/relevant-checks/scripts/run-checks.sh:116-134
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Full-repo lint-bash32 is not part of CI or /relevant-checks; only fixture harness runs. Contributor adds Bash 4+ to tracked scripts/foo.sh; CI (lint-only + harness shards) and /relevant-checks stay green; macOS bash 3.2 users hit runtime syntax errors. Add make lint-bash32 (or bash scripts/lint-bash32.sh) to CI lint job and relevant-checks after pre-commit (or add pre-commit hook).
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: .github/workflows/ci.yaml:63,Makefile:lint
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] target CI runs make lint-only and sharded test-harnesses; full-repo lint-bash32 is not invoked in ci.yaml A contributor adds declare -A to a real tracked script; test-lint-bash32 still passes because fixtures-only; Bash4+ ships to main Add make lint-bash32 to CI (or pre-commit) so every PR scans all tracked *.sh at repo root
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: docs/linting.md CI section vs Makefile lint chain
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Full-tree make lint-bash32 is on local make lint; CI lint job described as lint-only; harness tests fixtures not whole tree Bash-4 constructs could reach main if only CI and partial checks are used and no job runs make lint-bash32 Add CI step for make lint-bash32 or explicitly document local-only full-tree enforcement
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/launch-claude-review.sh:105-111 and scripts/dispatch-code-voters.sh (voter wiring)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Voter role no longer receives diff/plan/scope context files forwarded to the subprocess. Voter asked to verify ballot claims against the diff never sees that diff while dispatch accepts symlink/large diff paths; votes can look valid but be ungrounded. Restore bounded diff context for voters or document the intentional loss of diff-grounded verification in voter contracts.
- **Suggested revision**: Address the concern above.

### FINDING_25: security: scripts/collect-agent-results.sh:5807-5808 (approx)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] eval on dynamic variable name fragments for retry bookkeeping If launched_var ever becomes attacker-influenced eval becomes shell injection Replace eval with printf -v or fixed allow-list of destination variable names
- **Suggested revision**: Address the concern above.

### FINDING_26: security: scripts/lint-bash32.sh:46-47 (awk)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Whole-line skip on any /lint-bash32: ok/ substring A line can hide real Bash4+ usage behind one inline marker; relies on reviewer discipline for suppressions Anchor suppression to EOL-only comment or stricter token parse
- **Suggested revision**: Address the concern above.

