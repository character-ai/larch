### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:Step 1
- **Concern**: `-s` is pinned as the `--file` short alias but its boolean grammar is not defined. Scenario: An operator invoking `/learn-from-bugs -s closed` (or `-s` with any trailing token) can enable filing mode while treating `closed` as verbal search text instead of `--state closed`, mining the wrong issue set before batch filing
- **Proposed resolution**: In Step 1, define `-s`/`--file` as boolean flags that take no value; keep `--state` long-form only; reject `-f` and any unknown flag; abort before Step 2 when argv is malformed (for example `-s closed` or `-s` combined with a second short option)

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/learn-from-bugs/SKILL.md:--file branch
- **Concern**: Section 5 filing routing is underspecified for `best-home` splits. Scenario: Report section 5 is titled invariants, but rows can classify `hook`, `guideline`, or `lint`. A `--file` gather step that serializes all of section 5 into invariants-file issues will drop hook-contract bodies or file hooks with the invariant template, despite the separate hook category
- **Proposed resolution**: Pin the gather step: section 4 → lint bucket; section 6 → guidelines; section 7 → regression tests; section 8 → still-broken code; section 5 rows route by `best-home` (`hook` → hook-contract, `invariants-file` → invariants-file, `guideline`/`lint` only when no matching section 4/6 proposal exists). Mirror the rule in the structural harness

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: agent-lint.toml
- **Concern**: The new Makefile-only structural harness is not listed in the plan. Scenario: Adding `scripts/test-learn-from-bugs-structure.sh` without an `agent-lint.toml` exclude entry matches the orphan pattern that fails `make agent-lint` / CI for sibling harnesses such as `test-bug-structure.sh`
- **Proposed resolution**: Add `### UPDATED: agent-lint.toml` with an exclude entry (and optional sibling `scripts/test-learn-from-bugs-structure.md` if you follow the other structure-harness pattern) in the same change as the new harness target ## Findings ### 1. `-s` boolean grammar is undefined (correctness) The revised plan correctly adopts `--file|-s` and rejects `-f`, but Step 1 still only documents pulling `-n`, `--state`, `--repo`, and `--search`, then treating the remainder as verbal description. That leaves `-s closed` ambiguous: filing mode turns on, and `closed` becomes search text instead of state. Pin `-s`/`--file` as valueless boolean flags, keep `--state` long-form only, and fail fast on malformed argv before prepare runs. ### 2. Section 5 `best-home` routing for `--file` gather (architecture) Hook-contract filing is called out, but the report still places hook classification inside section 5 (“Proposed architectural invariants”). The plan does not say how `--file` maps section 5 rows into the six filing buckets. Without an explicit `best-home` split at gather time, hook residuals are easy to mis-file with invariant bodies, which defeats FINDING_2’s fix at the body-template layer only. ### 3. Missing `agent-lint.toml` exclude (risk-integration) The plan adds a new Makefile-only harness and shard target but does not update `agent-lint.toml`. Peer harnesses (`test-bug-structure.sh`, `test-research-structure.sh`, etc.) are excluded there; omitting the new script is a likely CI regression on the path that runs `make agent-lint`. ## Prior ledger Accepted round-1 items (`-s` vs `-f`, hook filing category, batch `###` fencing, amendment text, `--repo` passthrough, section renumbering) look addressed in the current plan; I did not re-raise them. Rejected/OOS ledger items (explicit Step 1 allowlist, dedupe keys, title prefixes, parent exit codes, intra-batch deps) were not repeated unless the gaps above add new evidence.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: security
- **Location**: skills/learn-from-bugs/SKILL.md:planned Step 5
- **Concern**: Automatic `--file` filing lacks an explicit untrusted-content boundary for mined GitHub issue data. Scenario: The new no-approval path turns issue bodies, comments, and derived digests into issue creation instructions. A malicious or compromised bug report can inject directives that alter scope, fabricate proposals, or cause unintended issue content to be filed.
- **Proposed resolution**: Add a mandatory prompt boundary for all mined issue content and require treating it as evidence only. State that embedded commands, workflow requests, scope changes, and output-format instructions must never be followed, and that only independently verified root-cause facts may enter filed bodies.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/learn-from-bugs/SKILL.md:planned Step 5
- **Concern**: Invoke `/issue` using the repository’s required bare-name-then-qualified-name fallback. Scenario: The planned filing path says to invoke `/issue` through the Skill tool but does not specify the mandated fallback from bare `issue` to `larch:issue` or the consumer namespace. In a consumer repo where bare lookup fails, `--file` cannot file issues even though the feature is otherwise ready.
- **Proposed resolution**: Specify the canonical Skill-tool invocation: try bare `issue` first, then retry with the fully qualified plugin namespace only when the result is `Unknown skill`, while preserving the existing anti-halt continuation and result parsing.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:46-57
- **Concern**: Step 2 never forwards Step 1 `--repo` into `learn-from-bugs prepare`. Scenario: The contract parses `--repo`, but the Step 2 fence always calls prepare with only `--root "$PWD"`. `REPO` in stdout therefore comes from the cwd repo, so `--file` can file into a different repo than the one whose bugs were mined when the operator passed `--repo`.
- **Proposed resolution**: Add conditional `--repo "$REPO"` to the prepare invocation when Step 1 binds it, and pin that wiring in the structural harness.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:--file-branch
- **Concern**: Section 5 `best-home` values are not routed before `--file` batching. Scenario: Section 5 keeps hook, guideline, lint, and invariants-file candidates together. The plan requires six filing categories but never partitions section 5 by `best-home`, so hook or guideline residuals can be filed with invariant templates despite the hook-body ban.
- **Proposed resolution**: Before writing `batch-issues.md`, route each section 5 residual by `best-home`: `hook` to hook-contract bodies, `guideline` to guideline bodies, `lint` to lint bodies, and only `invariants-file` to invariant append/amendment templates; assert that partition in the harness.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/learn-from-bugs/SKILL.md (planned --file filing branch)
- **Concern**: The durable scan marker is committed before automatic filing, while the generated report and batch file remain only under temporary RUN_DIR. Scenario: If `/issue --dry-run` or the create pass fails, the scan marker still advances and a later run may skip the same closed issues; the unfiled proposals have no durable retry artifact, so the requested filing can be permanently lost
- **Proposed resolution**: For `--file`/`-s`, either commit the scan marker only after filing completes successfully, or persist the report and batch input in a durable retry location and retain a pending marker until all proposals are handled; keep the existing marker ordering for default approval-gated mode

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md
- **Concern**: The `--file` gather step does not route section 5 `best-home` values to the six filing categories. Scenario: Section 5 mixes `lint`, `hook`, `invariants-file`, and `guideline` candidates via `best-home`, but the plan only splits `hook` away from `invariants-file`. A `--file` run can file `best-home: guideline` or `best-home: lint` rows with the invariants-file body template, dropping required Deviate-when or lint-rule fields and producing decision-incomplete issues
- **Proposed resolution**: In the `--file` branch, partition section 5 rows by `best-home` before body generation: `invariants-file` to invariants issues, `hook` to hook-contract issues, `lint` to lint issues (dedupe section 4), `guideline` to guideline issues (dedupe section 6). Pin the rule and a harness fixed-string check in `scripts/test-learn-from-bugs-structure.sh`
