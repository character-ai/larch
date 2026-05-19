### FINDING_1: **Important** correctness `scripts/drop-bump-commit.sh:96-99` — The new walk-back matcher uses shell glob syntax, so `[0-9]*` means “one digit followed by anything,” not “one or more digits.” A commit like `Bump version to 1.x.3` that only touches `.claude-plugin/plugin.json` would pass Guard 2 and Guard 4 and be dropped, even though the documented contract requires strict `X.Y.Z` semver. Use the prior Bash regex check inside the loop: `[[ "$_subj" =~ ^Bump\ version\ to\ [0-9]+\.[0-9]+\.[0-9]+$ ]]`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness `scripts/drop-bump-commit.sh:96-99` — The new walk-back matcher uses shell glob syntax, so `[0-9]*` means “one digit followed by anything,” not “one or more digits.” A commit like `Bump version to 1.x.3` that only touches `.claude-plugin/plugin.json` would pass Guard 2 and Guard 4 and be dropped, even though the documented contract requires strict `X.Y.Z` semver. Use the prior Bash regex check inside the loop: `[[ "$_subj" =~ ^Bump\ version\ to\ [0-9]+\.[0-9]+\.[0-9]+$ ]]`.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** risk-integration `Makefile:4-64`, `docs/linting.md:225-230`, `skills/implement/scripts/test-step-8a-changelog.sh` — The new Step 8a changelog harness is added and referenced from `skills/implement/SKILL.md`, but there is no `test-step-8a-changelog` Makefile target and no shard entry under `test-harnesses-*`, so `make lint` / CI will never run it. A future regression in the new no-manifest fallback can land green because the only targeted harness is orphaned. Add the target, add it to one harness shard, update `.PHONY`, and document it in `docs/linting.md`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** risk-integration `Makefile:4-64`, `docs/linting.md:225-230`, `skills/implement/scripts/test-step-8a-changelog.sh` — The new Step 8a changelog harness is added and referenced from `skills/implement/SKILL.md`, but there is no `test-step-8a-changelog` Makefile target and no shard entry under `test-harnesses-*`, so `make lint` / CI will never run it. A future regression in the new no-manifest fallback can land green because the only targeted harness is orphaned. Add the target, add it to one harness shard, update `.PHONY`, and document it in `docs/linting.md`.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: scripts/implement-finalize.sh:1-12
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Intentional no-errexit policy and redundant set +e probe boundaries pre-exist Item J. Not introduced or amplified by the changelog fallback change. No action required for this PR scope.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/implement-finalize.sh:720-723
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicate set +e around write_changelog_entry Noise only; no functional impact noted. Optional cleanup unrelated to batch items.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/implement-finalize.sh:720-723
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Duplicate consecutive `set +e` around `write_changelog_entry` predates Item J and is unrelated to the new fallback logic. No direct regression link to Items E–J; fixing is optional churn. Leave as-is or collapse to a single `set +e`/`set -e` pair in a separate cleanup PR.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/create-pr.sh:176-188
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] gh pr create stdout still buffered in shell variable before tmpfile Large gh stdout could cause memory pressure. Stream stdout directly to PR_STDOUT_FILE and read tail only on failure.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: Makefile:31-64
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Item J promised Makefile/linting harness wiring for test-step-8a-changelog.sh; no target or shard entry exists. New changelog regression harness never runs under make lint / test-harnesses; Item J coverage is effectively dead in CI. Add make test-step-8a-changelog (harness-timer.sh pattern), attach to a test-harnesses-N shard, update docs/linting.md if that table lists harnesses.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/create-pr.sh:170-171
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Argv diagnostic uses manual redaction string instead of redact-tmpdir-paths.sh per plan Edge argv shapes may leak paths the helper would redact. Invoke redact-tmpdir-paths.sh on composed argv text.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/create-pr.sh:170-196
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan Item I required argv redaction via redact-tmpdir-paths.sh; implementation uses a hand-built GH_CREATE_ARGV string only. Divergence from canonical redaction; tmp or sensitive argv fragments may leak compared to repo helper contract. Pipe composed argv diagnostic through scripts/redact-tmpdir-paths.sh (or equivalent single source of truth).
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/drop-bump-commit.sh:161
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale warning says HEAD subject though match may be at HEAD depth. Misleading diagnostics when LARCH_BUMP_FILES path fails file guard. Mirror found commit wording used elsewhere in the script.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/test-drop-bump-commit.sh (Test 19)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Weak stderr assertion (grep digit 2 only) Unrelated WARN containing 2 could false-pass. Assert stable depth warning substring.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/test-drop-bump-commit.sh:256-257
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 19 only greps for digit 2 in stderr to assert depth is mentioned. False positives; weak guarantee the warning documents walked depth. Assert a stable phrase from drop-bump-commit.sh WARN output.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: skills/implement/scripts/test-step-8a-changelog.md:1-8
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness markdown is a minimal stub versus sibling harness contract docs. Higher maintenance friction and weaker operator guidance. Expand contract doc to match established harness .md depth when stable.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:83-88
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unmerged-path detection labels every conflict as “rebase in progress” and suggests rebase-only recovery. A merge conflict mid-feature shows the same message; operators may run rebase commands on a merge state and worsen the repo. Tighten wording to “unmerged paths” / “merge or rebase in progress” and mention `merge --abort` where appropriate, or detect MERGE_HEAD vs REBASE_HEAD if distinct messaging is required.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:86-87
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Error text claims rebase for all unmerged UU states Misleading when conflict is from merge or cherry-pick Use neutral wording such as unmerged paths or merge/rebase in progress
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:97-106
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unmerged-index check always labels error as rebase and suggests only rebase recovery Operator in unresolved merge (UU from merge --no-conflict) reads wrong recovery commands and may run rebase --abort on a merge conflict state. Reword error to conflict/unmerged index or detect merge vs rebase and tailor commands.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:97-106
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unmerged-index pre-check always emits ERROR text claiming rebase in progress and only suggests rebase commands. Plain merge --no-commit conflicts (valid UU state) mislead operators; wrong recovery commands. Broaden wording to unmerged paths or branch on MERGE_HEAD vs REBASE_HEAD for accurate hints.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/create-pr.sh:170-197
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] PR-create failure diagnostics use a synthetic argv string instead of redact-tmpdir-paths.sh as required by Item I. Tmp or sensitive path segments in real argv expansion are not guaranteed to match repo redaction policy. Pipe constructed argv text through scripts/redact-tmpdir-paths.sh (or equivalent) for the ERROR line; align create-pr.md with the mechanism.
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

### FINDING_26: correctness: skills/implement/scripts/test-step-8a-changelog.sh:1463-1471
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Fixture c does not assert non-zero postbump exit. Success exit with stray output could mask a broken failure contract. Assert implement-finalize postbump rc is non-zero for fixture c.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:83-88
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unmerged file list embedded raw in emit_kv ERROR value Newline in rare pathnames can break single-line KEY=value parsers Encode paths as single-line safe list or reject paths containing newlines
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

### FINDING_32: risk-integration: scripts/create-pr.sh:170-171
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] GH_CREATE_ARGV uses unquoted array join for GH_REPO_ARGS in diagnostic text. Unusual gh args with spaces could render misleading argv in failure logs. Use a safely quoted join for display-only argv serialization.
- **Suggested revision**: Address the concern above.

### FINDING_33: risk-integration: scripts/create-pr.sh:170-196
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] GH_CREATE_ARGV not passed through redact-tmpdir-paths.sh; BRANCH and BASE_REF unquoted in assignment Operator logs/execution-issues may expose tmp/home paths or odd split argv; diverges from planned redaction contract Quote branch and base in the argv string; pipe diagnostic text through scripts/redact-tmpdir-paths.sh before larch_err
- **Suggested revision**: Address the concern above.

### FINDING_34: risk-integration: scripts/create-pr.sh:170-197
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] PR-create failure argv diagnostics skip `redact-tmpdir-paths.sh` compared to the plan’s redaction requirement. Argv strings that later include tmp paths or other sensitive segments may leak unchanged while the plan promised centralized redaction. Build or post-process the argv diagnostic with `scripts/redact-tmpdir-paths.sh` (or pipe the composed string through it) to match the plan and existing helper semantics.
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

### FINDING_38: security: scripts/implement-finalize.sh:696-703
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] PR_TITLE and ISSUE_NUMBER from state interpolated into committed CHANGELOG without sanitization Malformed or misleading changelog bullets if title contains newlines/control content Normalize PR_TITLE (strip newlines cap length) before printf to categories_md
- **Suggested revision**: Address the concern above.

