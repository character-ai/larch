# Review Round 1

- Mode: `diff`
- Accepted findings: 20
- Rejected findings: 5
- Exonerated findings: 9
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** correctness `scripts/drop-bump-commit.sh:96-99` — The new walk-back matcher uses shell glob syntax, so `[0-9]*` means “one digit followed by anything,” not “one or more digits.” A commit like `Bump version to 1.x.3` that only touches `.claude-plugin/plugin.json` would pass Guard 2 and Guard 4 and be dropped, even though the documented contract requires strict `X.Y.Z` semver. Use the prior Bash regex check inside the loop: `[[ "$_subj" =~ ^Bump\ version\ to\ [0-9]+\.[0-9]+\.[0-9]+$ ]]`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness `scripts/drop-bump-commit.sh:96-99` — The new walk-back matcher uses shell glob syntax, so `[0-9]*` means “one digit followed by anything,” not “one or more digits.” A commit like `Bump version to 1.x.3` that only touches `.claude-plugin/plugin.json` would pass Guard 2 and Guard 4 and be dropped, even though the documented contract requires strict `X.Y.Z` semver. Use the prior Bash regex check inside the loop: `[[ "$_subj" =~ ^Bump\ version\ to\ [0-9]+\.[0-9]+\.[0-9]+$ ]]`.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/test-drop-bump-commit.sh (Test 19)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Weak stderr assertion (grep digit 2 only) Unrelated WARN containing 2 could false-pass. Assert stable depth warning substring.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: scripts/test-drop-bump-commit.sh:256-257
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 19 only greps for digit 2 in stderr to assert depth is mentioned. False positives; weak guarantee the warning documents walked depth. Assert a stable phrase from drop-bump-commit.sh WARN output.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:83-88
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unmerged-path detection labels every conflict as “rebase in progress” and suggests rebase-only recovery. A merge conflict mid-feature shows the same message; operators may run rebase commands on a merge state and worsen the repo. Tighten wording to “unmerged paths” / “merge or rebase in progress” and mention `merge --abort` where appropriate, or detect MERGE_HEAD vs REBASE_HEAD if distinct messaging is required.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:97-106
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unmerged-index check always labels error as rebase and suggests only rebase recovery Operator in unresolved merge (UU from merge --no-conflict) reads wrong recovery commands and may run rebase --abort on a merge conflict state. Reword error to conflict/unmerged index or detect merge vs rebase and tailor commands.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: scripts/drop-bump-commit.md:310-311 vs scripts/drop-bump-commit.sh:96-99
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Documents strict regex Guard 2 but script uses case glob with * digit runs. Maintainers misread guarantees; weaker match than documented +. Align documentation to implementation or restore regex per subject.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: scripts/drop-bump-commit.sh:468-474
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Guard bump-subject match is looser than the plan’s ^Bump version to [0-9]+\.[0-9]+\.[0-9]+$ pattern. A non-bump commit with a permissively matching subject could be selected and dropped destructively. Use the strict regex (or equivalent) for each walked commit subject before setting FOUND_AT.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: scripts/drop-bump-commit.sh:86-99
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Guard2 bump subject uses loose case glob vs documented strict semver regex Subjects like Bump version to 1.2.3-rc1 can be mistaken for the bump commit; drop may target wrong commit or mis-guard. Use anchored bash regex matching documented ^Bump version to [0-9]+\.[0-9]+\.[0-9]+$.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/drop-bump-commit.sh:96-97
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] case glob uses shell '.' (any character) not literal dots; matches non-semver subjects like Bump version to 1x2x3 First matching subject can be chosen for destructive reset/rebase --onto; wrong commit dropped if subject spoofed and diff allowlist passes Use extglob/literal-dot pattern or [[ =~ ^Bump version to [0-9]+\.[0-9]+\.[0-9]+$ ]] on each candidate subject
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/implement-finalize.sh:697-704
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] ISSUE_NUMBER=0 treated as valid tracking for fallback bullet CHANGELOG could show Closed: #0 while orchestration treats #0 as non-tracking. Treat 0 same as empty for fallback gating.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/test-drop-bump-commit.sh Test 19
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Depth warning assertion only greps for the digit 2. False pass if unrelated stderr contains 2 without naming walked depth. Grep for the full expected WARN fragment (e.g. within $MAX_DEPTH commits).
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/test-drop-bump-commit.sh:1026-1027
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Test 19 stderr assertion only requires digit 2 substring. Regression in depth warning can slip through while unrelated stderr still contains 2. Assert full expected WARN substring or phrase.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: Item J / Makefile; docs/linting.md; scripts/implement-finalize.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New Step 8a changelog harness is not wired into Makefile or docs/linting.md despite the plan and existing finalize contract. Operators and CI never run skills/implement/scripts/test-step-8a-changelog.sh unless invoked by hand; lint documentation omits the new harness. Add test-step-8a-changelog Makefile target (harness-timer), place it on a test-harnesses-N shard, and add a docs/linting.md row mirroring sibling harnesses.
- **Suggested revision**: Address the concern above.


### FINDING_29: risk-integration: Makefile; docs/linting.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] New test harness test-step-8a-changelog.sh not wired into make test-harnesses CI never runs Item J regression; future changelog logic can regress silently. Add Makefile target shard entry and docs/linting.md mention per convention.
- **Suggested revision**: Address the concern above.


### FINDING_30: risk-integration: Makefile; skills/implement/scripts/test-step-8a-changelog.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New Step 8a changelog harness is not wired into test-harnesses / Makefile targets despite the plan. CI runs `make test-harnesses` and never executes the new script; regressions in Item J can ship unnoticed. Add a `test-step-8a-changelog` recipe (harness-timer + script path), attach it to an appropriate `test-harnesses-N` shard, update `docs/linting.md`, and keep `test-harness-shards-coverage` green.
- **Suggested revision**: Address the concern above.


### FINDING_31: risk-integration: docs/linting.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan requested linting doc updates for the new harness; diff shows no change. Contributors may not discover how to run the new test locally. Document the new Makefile target alongside other harness entries per repo convention.
- **Suggested revision**: Address the concern above.


### FINDING_35: risk-integration: scripts/drop-bump-commit.sh:12-15 vs 96-100
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] File header still documents strict regex bump subjects while Guard 2 uses a looser `case` glob. Future contributors may tighten/loosen the wrong layer or assume regex parity that does not exist. Align comments with the actual `case` pattern or restore true regex validation to match the documented contract.
- **Suggested revision**: Address the concern above.


### FINDING_36: risk-integration: scripts/test-drop-bump-commit.sh:1026-1031
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 19 only checks stderr contains the digit `2`, not a stable depth warning substring. A unrelated `2` in stderr could mask a broken WARN message. Assert on the full expected WARN fragment (e.g., max depth integer embedded in the scripted sentence).
- **Suggested revision**: Address the concern above.


### FINDING_37: risk-integration: skills/implement/scripts/test-step-8a-changelog.sh:1458-1471
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Fixture (c) omits `STATUS=changelog-failed` assertion present in real postbump output. A regression that still prints CHANGELOG_STATUS but drops STATUS could slip past the harness. Grep `out_c` for `STATUS=changelog-failed` (or the exact `emit_kv STATUS` tail) in addition to the existing strings.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: Makefile:31-64
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Item J promised Makefile/linting harness wiring for test-step-8a-changelog.sh; no target or shard entry exists. New changelog regression harness never runs under make lint / test-harnesses; Item J coverage is effectively dead in CI. Add make test-step-8a-changelog (harness-timer.sh pattern), attach to a test-harnesses-N shard, update docs/linting.md if that table lists harnesses.
- **Suggested revision**: Address the concern above.


