Here is the normalized aggregation. In-scope items are merged by behavioral risk; out-of-scope log-noise items are merged into one `### OOS_1:` block. Slots use the filenames from your input.

### FINDING_1: review_budget JSON read falls back to full when python3 is missing or broken
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The `review_budget` gate uses a python3 JSON snippet with `|| echo` full fallback. If python3 is missing or broken, `review_budget` becomes `full`, so `VALIDATE_PLAN_COMMANDS` runs on `--trivial` (quick) runs contrary to `flags.md` / Step 3 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Tier 2 `help_ok` treats non-empty stdout as success even when `--help` exits non-zero
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tier 2 help detection can treat `--help` as OK when stdout is non-empty despite a non-zero exit, which may yield false negatives on unknown flags versus a strict reading of plan bullets; sibling doc may imply a different contract (e.g. tying no-help to non-zero exit). Needs a single normative rule (implementation, issue acceptance, and docs including `SECURITY` if applicable).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Align implementation with issue acceptance or update normative docs and SECURITY so one contract governs help availability and exit codes.

### FINDING_3: `with_timeout` runs unbounded when `timeout`/`gtimeout` is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Without a timeout helper, `--help` or dry-run children can hang past the promised ceiling (e.g. 10s), risking hung `/design` or stuck local `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Add portable timeout or hard-require timeout binary
  - From cursor-specialist-testing-output.txt: Document coreutils requirement or fail closed or add portable watchdog.

### FINDING_4: `SKILL.md` validator gate duplication and driver-output example only parses `VALIDATE_STATUS` while prose lists more KVs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Duplicate bash gate blocks for Step 2b and Step 5c invite drift; the example loop only switches on `VALIDATE_STATUS` while prose lists additional `emit_kv` keys, so operators following the snippet omit breadcrumbs the prose promises.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Wrong cross-reference for normative TSV schema in `parse-plan-commands.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Readers directed to `SKILL.md` may not find the `cmd_uid` column contract; should point at `parse-plan-commands.md` / validate docs instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: `validate-plan-commands` harness gaps for Tier 3, registry, cwd, unsafe-token, and composed Tier3-off behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests omit several plan-promised cases (Tier3/metachar/cwd, argv hardening, dry-run registry paths, unsafe-token, composed source-kind / Tier3-disable paths), so regressions may not fail `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add tmpdir registry plus fixture scripts covering dry-run success failure unsafe-token no-help and composed source-kind.
  - From cursor-specialist-plan-fidelity-output.txt: Add temp registry+dry-runnable fixture script tests for Tier 3 success failure and unsafe-token rejection plus composed Tier3 disable assertion.

### FINDING_7: Awk suffix / character-class test for flags may be non-portable across awk implementations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: An awk test using `/[A-Za-z0-9_-]/`-style boundary logic can behave differently across awk implementations and help punctuation, causing false unknown-flag or false OK results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rewrite boundary test without ambiguous bracket ranges

### FINDING_8: `SKIPPED_COUNT` summary excludes `SKIPPED_FLAG_CHECK`, misleading KV totals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Summary KVs undercount skips when `SKIPPED_FLAG_CHECK` is omitted from `SKIPPED_COUNT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Count SKIPPED_FLAG_CHECK or rename KV field

### FINDING_9: Tier 3 argv construction omits non-flag positionals from plan commands
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Dry-run can miss failures that need bare path args; either extend TSV / argv assembly or document limitation vs literal-command goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend TSV or document limitation vs literal-command goal

### FINDING_10: Acceptance harness does not pin real `launch-claude-review.sh --context-files` / R4 unknown-flag case
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Demo / synthetic fixture path means CI may not catch help/flag drift or the literal historical failure mode (`scripts/launch-claude-review.sh` with `--context-files`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add an integration assertion against the real launch-claude-review.sh --context-files invocation and expected DEFECT line.
  - From cursor-specialist-edge-cases-output.txt: Add a harness assertion (or fixture plan) that runs scripts/launch-claude-review.sh with --context-files and expects unknown-flag context-files.
  - From cursor-specialist-plan-fidelity-output.txt: Add fixture asserting DEFECT script=scripts/launch-claude-review.sh kind=unknown-flag flag=context-files for --context-files.

### FINDING_11: `test-parse-plan-commands.sh` lacks golden coverage for plan-required parse branches
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Parser harness omits cases called out in acceptance (e.g. subshell / `PARSE_NOTE` / continuations / quoted args / charset / `UPDATED`/allow-list rows); awk changes could merge undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixtures and byte-exact expected TSV for each missing acceptance path.
  - From cursor-specialist-plan-fidelity-output.txt: Add golden markdown+tsv fixtures and run_case entries covering parse_note and updated_flag paths.

### FINDING_12: `docs/linting.md` omits new Makefile `test-*` harness rows for operator discoverability
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: New harness targets are not listed in the operator linting table.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add two rows mirroring existing design harness documentation style.

### FINDING_13: Relative `./script` paths dropped by `is_repo_script` globs, skipping validation silently
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Plans using `./scripts/foo.sh` can fail repo-prefix checks and be dropped, so unknown-flag and dry-run checks never run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Strip ./ before repo-prefix checks or extend globs; add regression fixture

### FINDING_14: Naive `$(` substring detection conflates `$((` arithmetic; blocks can bypass flag/help validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A naive `$(` match can mis-classify `$((...))` segments, yielding `parse_note` only and skipping flag/help validation for affected command text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Detect command substitution without matching $(( ; add awk/harness coverage

### OOS_1: [OUT_OF_SCOPE] Large committed `larch-logs/**` trees add PR diff noise (policy-driven, not validator logic)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Run-log bulk dominates branch diffs and reviewer paging; framed as workflow / policy noise rather than functional defects in validator code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Accept as workflow noise per repo policy; optional future split of log-only commits for readability (not a functional defect in the validator code).
  - From cursor-specialist-correctness-output.txt: Confirm intentional per run-log policy
  - From cursor-specialist-testing-output.txt: No change required for CI correctness.
  - From cursor-specialist-edge-cases-output.txt: None required for product correctness; policy-driven artifact per docs/run-logs.md.
  - From cursor-specialist-plan-fidelity-output.txt: No code change required for lesson scope.

### FINDING_15: `design-driver.md` “Primary Callers” omits `VALIDATE_PLAN_COMMANDS` / Step 5c Gate B contexts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Operators using `design-driver.md` may miss when validation runs relative to `SKILL.md` / `flags.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update contract bullets to mirror SKILL approval-gates and flags.md.

---

**Merge map (for traceability)**  
- 1 → FINDING_1  
- 2, 24 → FINDING_2  
- 3, 9, 18 → FINDING_3  
- 4, 5, 12, 25 → FINDING_4  
- 6 → FINDING_5  
- 7, 17, 29 → FINDING_6  
- 10 → FINDING_7  
- 11 → FINDING_8  
- 13 → FINDING_9  
- 15, 23, 27 → FINDING_10  
- 16, 28 → FINDING_11  
- 19 → FINDING_12  
- 21 → FINDING_13  
- 22 → FINDING_14  
- 8, 14, 20, 26, 31 → OOS_1  
- 30 → FINDING_15  

`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is **not** included because this output contains one or more `### FINDING_` blocks (and `### OOS_1:`).
