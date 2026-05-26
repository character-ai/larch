### FINDING_1: code-quality: skills/implement/scripts/test-step2-dispatch.sh:1278-1451
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Only 4 of 20 planned M-tests (M1 M2 M12 M16) are implemented Acceptance claims M1-M20 but M3-M11 M13-M15 M17-M20 missing so submodule tmpdir pre-dirty and post-Step3 gates are unpinned Add missing stub tests or revise acceptance to match shipped harness
- **Suggested revision**: Address the concern above.

### FINDING_2: architecture: skills/implement/SKILL.md:1047
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Post-Step 3 recovery delta recompute has no callable script only prose Orchestrator may commit using stale RECOVERY_PATHS_FILE after lint-fix adds paths and miss files from Step 3 Extract shared compute-step2-recovery-paths helper invoked from SKILL Step 2.4
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/step2-implement.sh:375-490
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Triple copy of NUL porcelain parsing Python in one shell file Porcelain rule changes require three edits and can desync digest vs delta vs submodule scan Factor one shared parser module or helper script
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/test-step2-dispatch.md:39-42
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract documents 4 M-tests while plan promised M1-M20 docs Reviewers assume full gate matrix is tested when harness only covers four cases Document implemented M-tests only or add remaining bullets when tests land
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/implement/scripts/step2-implement.sh:797-798
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] schema_version gate uses jq -r string compare not tostring coercion Numeric schema_version 1 may diverge from prompt-side jq self-validation Align dispatcher gate with (.schema_version | tostring) == "1"
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: agents/_implementer-base.md:271-291
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Complete-status inline template includes needs_qa example fields Long runs may emit complete manifests still carrying needs_qa keys Use status-specific minimal JSON examples
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: skills/implement/SKILL.md:1047
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan-scope alignment is prose-only no check script Orchestrator may mis-compare paths or skip realpath rules and commit out-of-scope files Add check-recovery-paths-in-plan-scope.sh helper
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/implement/scripts/test-step2-dispatch.sh:1279-1334
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] M1 lacks cursor RECOVERY_PRIOR_TOOL parallel sub-test Plan M1 cursor variant never regression-tested Duplicate M1 with stub cursor launcher
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/implement/scripts/step2-implement.sh:536-546
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Recovery runs per-path submodule check then full-repo submodule scan Minor redundant work on recovery path Document intent or narrow scan to recovery paths only
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/scripts/step2-implement.sh:418-435
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Rename/copy porcelain -z rows record source path only and skip destination token. Implementer renames plan/file.py to plan/file_new.py; recovery emits/commits plan/file.py (often deleted) and omits plan/file_new.py. On R/C rows set rel to the post-NUL destination path in parse(), digest capture, and recovery output; add git mv harness.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/implement/scripts/step2-implement.sh:679-683
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Prelaunch baseline rewritten every step2 run including --answers QA resume. Round 1 edits A; round 2 baseline includes A; round 2 only edits B; malformed manifest recovery commits B only and drops A. Write baseline once per tmpdir (skip if prelaunch file exists or on --answers); two-round harness expects A and B in RECOVERY_PATHS_FILE.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/implement/scripts/test-step2-dispatch.sh:1279-1450
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan acceptance Tests M1-M20 but harness only implements M1 M2 M12 M16. Submodule/branch/NUL/tmpdir/M18/M19 guards unenforced; regressions can ship undetected. Implement missing M tests or update acceptance to match shipped coverage.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/implement/SKILL.md:1047-1152
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] No shared helper for post-Step-3 recovery delta recompute (FINDING_14). Checks-repair adds bar.py; Step 4 uses step2-recovery-paths.nul without bar.py; partial commit or wrong scope. Factor compute_recovery_paths into callable script; wire Step 2.4; add M18.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/SKILL.md:1047
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan-scope alignment is orchestrator prose only. Orchestrator skips scope check; recovery commits paths outside ### NEW/UPDATED/REWRITTEN plan list. Add fail-closed scope verifier script for Step 2.4.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/implement/scripts/step2-implement.sh:796-798
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Recovery allowed when schema_version != 1 but status is complete. Manifest schema_version 2 with working tree edits recovers instead of hard invalid schema bail. Limit recovery to legacy/missing schema_version or version coercing to 1 only.
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: skills/implement/scripts/test-step2-dispatch.md:39-42
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc lists four M tests while plan promises M1-M20. Reviewers assume CI covers M9b submodule dirty-file case. Sync doc with implemented tests or add missing harness cases.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/scripts/test-step2-dispatch.sh:1279-1451
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Only 4 of plan-required Tests M1-M20 (M1 M2 M12 M16) are implemented; M3-M11 M13-M15 M17-M20 missing. Recovery gate regressions (submodule dirty untracked-only needs_qa exclusion NUL paths pre-dirty overlap tmpdir filter) can merge with green make test-step2-dispatch. Add missing M-series scratch-repo tests or shared helpers; update test-step2-dispatch.md to match.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/scripts/test-step2-dispatch.md:44-49
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Harness doc marks branch-changed submodule-dirty and path guards out of scope while recovery code enforces them. False confidence: contributors rely on test-step2-dispatch.md but recovery safety rails are largely unpinned in that harness. Add M8-M10 (and related) tests or revise docs/plan acceptance to match intentional scope cut.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/implement/SKILL.md:1047-1152
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test for post-Step-3 recovery delta recompute to step2-recovery-paths-final.nul (plan M18). Checks-repair can add paths after Step 2.4; without a harness wrong files may be committed or valid fixes omitted. Add offline integration harness for recovery-out-of-scope and final pathspec file after stub Step 3.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: agents/_implementer-base.md:103-108
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No automated test runs prompt-side jq -e on qa-pending.json.tmp (plan M20). Empty .questions tmp could still be renamed; dispatcher catches late after wasted Q/A cycle. Add prompt-contract jq fixture tests in test-codex-implementer.sh and test-cursor-implementer.sh.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-extract-plan-scope-paths.sh:17-70
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Single synthetic fixture; no golden diff vs prior scout write_scope_files corpus. Helper/scout divergence on edge plan headings may break plan-scope alignment in production recovery. Extend harness with scout fixture corpus golden diffs.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/implement/scripts/test-step2-dispatch.sh:1302-1321
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] M1 recovery happy path tests codex only; plan required cursor parallel. Cursor-only recovery regressions (e.g. cursor-modified-history interaction) go undetected. Add parallel M1 sub-test with stub cursor and RECOVERY_PRIOR_TOOL=cursor.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/implement/scripts/test-step2-dispatch.sh:1335-1338
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] M17 Step 7a publication of recovery-metadata.json not asserted (only sidecar file existence). Step 7a could publish wrong artifact; M1 would still pass. Add stub Step 7a assertion on published log artifact.
- **Suggested revision**: Address the concern above.

### FINDING_24: security: skills/implement/SKILL.md:1047
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Plan-scope alignment for recovery is prompt-only; no script fails closed before commit. Codex edits out-of-plan CI/workflow files plus in-plan files; recovery path list includes both; orchestrator skip commits malicious workflow change. Add mechanical align-recovery-paths-to-plan.sh (or commit-implementation preflight) and offline tests for mixed-scope deltas.
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: skills/implement/scripts/step2-implement.sh:679-683
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pre-launch recovery baseline is rewritten on every Step 2 call including --answers resumes despite a once-per-dispatch comment. On Q/A resume after partial needs_qa work a malformed final manifest can recover with RECOVERY_PATHS_FILE listing only the last cycle s edits leaving earlier uncommitted work unstaged for commit. Guard write_prelaunch_recovery_baseline so baseline files are created only on first external launch per tmpdir not on each --answers redispatch.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: skills/implement/scripts/test-step2-dispatch.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Only Tests M1 M2 M12 M16 implemented; plan requires M1-M20 CI passes without pinning submodule branch protected-path NUL tmpdir pre-dirty M18 M20 gates Add missing M3-M20 cases per plan fixtures
- **Suggested revision**: Address the concern above.

