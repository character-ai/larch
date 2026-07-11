### FINDING_1: Required `--file/-s` short alias is rejected
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Auto Filing Contract Auditor, Codex-dyn-Auto Filing Contract Auditor
- **Severity**: major
- **Concern**: The plan implements `-f` and rejects `-s`, but the requested interface is `--file/-s`. Operators using the required `-s` form would receive an unknown-flag error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the plan and all prompt, README, docs, and structural-harness requirements to accept `--file` and `-s`; reject `-f` unless it is intentionally added as an extra documented alias
  - From Codex-Innovation: Use `-s` as the short alias everywhere: frontmatter, argument parsing, rejection rules, README.md, docs/skills.md, and the structural harness. Do not add or document `-f` unless the feature scope is explicitly changed.
  - From Cursor-Pragmatic: Either accept `-s` as an alias for `--file`, or keep `-f` only and document the intentional deviation in `README.md`, `docs/skills.md`, and the structural harness (assert `-s` is rejected and `-f` is documented).
  - From Codex-Pragmatic: Update the argument hint, contract, parser instructions, documentation, and structural harness to use `--file` and `-s`; reject `-f` unless retaining it is an intentional compatibility alias documented by the feature owner.
  - From Codex-Requirements: Accept `-s` as an alias for `--file` throughout argument parsing, frontmatter, documentation, and the structural harness; do not treat `-s` as an invalid flag
  - From Cursor-dyn-Auto Filing Contract Auditor: Accept -s as an alias for --file in Step 1 or document a deliberate rejection with README/docs/skills.md aligned to -f only; do not silently drop -s
  - From Codex-dyn-Auto Filing Contract Auditor: Add `-s` as the supported alias for `--file`; do not reject it, and update the frontmatter, parser rules, structural harness, and documentation accordingly


### FINDING_2: Hook-contract residuals are missing from `--file` filing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Auto Filing Contract Auditor
- **Severity**: major
- **Concern**: The report and default follow-up flow recognize hook-shaped residuals, but the `--file` categories omit them and the invariant template is inappropriate for hook work. Hook proposals could therefore be dropped or filed with the wrong body shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add hook-contract proposals as an explicit sixth residual category in the --file branch with filing bodies that name hooks.json, hook scripts, sibling docs, harness updates, and verification; keep them separate from invariant-file issues; pin the category in the structural harness
  - From Cursor-Innovation: Add a hook-proposal filing branch (hook config, script, sibling docs, harness touchpoints, verification) and include hooks in the all-residual-categories list; branch filing bodies on best-home rather than always using invariants-file text
  - From Cursor-Pragmatic: `hook`-classified residuals never reach `/issue` under `--file`, so part of the feature's filing surface is missing. Add hook-contract updates as a sixth filing category with the same decision-complete body requirements as other residuals (hook config, script, sibling docs, harness, verification).
  - From Cursor-Requirements: Define a hook-contract issue template for best-home: hook items (hook config, script, sibling docs, harness, acceptance, verification) and include hooks in the --file gather/group/file set and harness category list
  - From Cursor-dyn-Auto Filing Contract Auditor: Add hook-contract proposals to --file residuals with self-contained bodies naming hooks/hooks.json, sibling docs, harness updates, acceptance checks, and backing issues


### FINDING_3: Batch issue bodies can be split by unfenced `###` headings
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Auto Filing Contract Auditor, Codex-dyn-Auto Filing Contract Auditor
- **Severity**: major
- **Concern**: Generic `/issue` batch parsing treats unfenced `###` lines as item boundaries. Detailed decision-complete bodies containing headings such as `### Acceptance criteria` or full guideline/invariant entries can therefore split, truncate, or corrupt issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the --file branch require #### or deeper for unfenced in-body headings (or fenced blocks for literal ### payloads), mandate /issue --dry-run parse validation before create, and add harness anchors for those rules plus --input-file invocation
  - From Cursor-Innovation: Require batch authoring rules in the --file branch: issue titles only on ### lines, unfenced subsections use #### or deeper, or fence any payload containing ### ; optionally run /issue --dry-run on the batch file before create.
  - From Cursor-Pragmatic: Require batch authoring rules in the `--file` branch: use `####` or deeper for unfenced subsections, fence append-ready guideline/invariant blocks, or another `/issue`-supported shape that allows nested headings. Require a parse preflight (`/issue --dry-run --input-file ...`) before the create pass, and extend `scripts/test-learn-from-bugs-structure.sh` to pin the chosen rule.
  - From Cursor-Requirements: In the --file branch, require top-level batch entries only as ### <title> and mandate #### or deeper for in-body subsections (or fenced ### blocks), plus an optional issue --dry-run parse gate before create; pin the rule in the structural harness
  - From Cursor-dyn-Auto Filing Contract Auditor: In skills/learn-from-bugs/SKILL.md require #### or deeper for in-body headings, fence append-ready text blocks, or a pre-filing issue parse-input --dry-run gate; ban unfenced ### lines inside filed bodies except the top-level item title row
  - From Codex-dyn-Auto Filing Contract Auditor: Require the generated batch file to use parser-safe headings, such as `##`, or use the exact OOS format; add a structural assertion that body content cannot introduce generic `### ` item boundaries


### FINDING_5: Existing guideline and invariant amendments are not fully specified
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The filing rules describe complete append-ready text for new entries but do not require the exact target and replacement content when changing existing guidelines or invariants. This leaves decision work for a later design step despite the zero-open-questions requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: For amendments, require filed bodies to include the exact existing entry identifier, the full replacement text, and acceptance criteria that the old wording is removed or updated; distinguish append vs amend in the completeness pass
  - From Cursor-Pragmatic: Filed issues can defer the exact edit to `/design` even though the operator asked for zero open questions. For change proposals, require the target ID/heading, the exact current text to replace (or a bounded excerpt plus location), and the complete replacement text in the filed body. Keep new-entry and change-entry rules separate in Step 4 and the `--file` expansion pass.
  - From Cursor-Requirements: Extend --file issue-body rules to require, for modifications, the target ID/section, the exact current text span, and the complete replacement or appended text; add a structural harness anchor forbidding defer-to-design language for edits


### FINDING_6: The batch `/issue` invocation omits repository passthrough
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The plan binds `REPO` during preparation but does not pass it to `/issue` in `--file` mode. When mining another repository, `/issue` may infer the current working-directory repository and file follow-up issues in the wrong place.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit --file invocation line: /issue --input-file "$RUN_DIR/batch-issues.md" --repo "$REPO" (plus sentinel if used); assert the passthrough in the structural harness
  - From Cursor-Innovation: Add an explicit invocation shape (`/issue --input-file … --repo "$REPO"`) and a structural-harness assertion for it.


### FINDING_8: Step 4 section references become stale after adding regression tests
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: minor
- **Concern**: Inserting a regression-test report section changes the numbering, but the proposal-wording range and later “Issues to file” references still use the old section numbers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update Step 4 numbering and the sections 4-7 proposal prose together when inserting Proposed regression tests
  - From Cursor-Requirements: Update Step 4 to sections 4 through 7 (or name sections explicitly) and renumber Issues to file to section 8


### FINDING_2: Route section 5 rows by `best-home`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Section 5 filing routing is underspecified for `best-home` splits. Section 5 can classify `hook`, `guideline`, `lint`, or `invariants-file`, but the plan does not fully partition those rows before `--file` batching. Rows can therefore receive the wrong body template, drop required fields, or violate the hook-body constraint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the gather step: section 4 → lint bucket; section 6 → guidelines; section 7 → regression tests; section 8 → still-broken code; section 5 rows route by `best-home` (`hook` → hook-contract, `invariants-file` → invariants-file, `guideline`/`lint` only when no matching section 4/6 proposal exists). Mirror the rule in the structural harness
  - From Cursor-Innovation: Before writing `batch-issues.md`, route each section 5 residual by `best-home`: `hook` to hook-contract bodies, `guideline` to guideline bodies, `lint` to lint bodies, and only `invariants-file` to invariant append/amendment templates; assert that partition in the harness.
  - From Cursor-Pragmatic: In the `--file` branch, partition section 5 rows by `best-home` before body generation: `invariants-file` to invariants issues, `hook` to hook-contract issues, `lint` to lint issues (dedupe section 4), `guideline` to guideline issues (dedupe section 6). Pin the rule and a harness fixed-string check in `scripts/test-learn-from-bugs-structure.sh`


### FINDING_3: Add the structural harness to `agent-lint.toml`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The new Makefile-only structural harness is not listed in the plan. Adding `scripts/test-learn-from-bugs-structure.sh` without an `agent-lint.toml` exclude entry matches the orphan pattern that fails `make agent-lint` / CI for sibling harnesses such as `test-bug-structure.sh`
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: agent-lint.toml` with an exclude entry (and optional sibling `scripts/test-learn-from-bugs-structure.md` if you follow the other structure-harness pattern) in the same change as the new harness target


### FINDING_4: Establish an untrusted-content boundary for mined issue data
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Automatic `--file` filing lacks an explicit untrusted-content boundary for mined GitHub issue data. Scenario: The new no-approval path turns issue bodies, comments, and derived digests into issue creation instructions. A malicious or compromised bug report can inject directives that alter scope, fabricate proposals, or cause unintended issue content to be filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a mandatory prompt boundary for all mined issue content and require treating it as evidence only. State that embedded commands, workflow requests, scope changes, and output-format instructions must never be followed, and that only independently verified root-cause facts may enter filed bodies.


### FINDING_5: Specify the canonical `/issue` skill fallback
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: Invoke `/issue` using the repository’s required bare-name-then-qualified-name fallback. Scenario: The planned filing path says to invoke `/issue` through the Skill tool but does not specify the mandated fallback from bare `issue` to `larch:issue` or the consumer namespace. In a consumer repo where bare lookup fails, `--file` cannot file issues even though the feature is otherwise ready.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify the canonical Skill-tool invocation: try bare `issue` first, then retry with the fully qualified plugin namespace only when the result is `Unknown skill`, while preserving the existing anti-halt continuation and result parsing.


### FINDING_6: Forward `--repo` into preparation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Step 2 never forwards Step 1 `--repo` into `learn-from-bugs prepare`. Scenario: The contract parses `--repo`, but the Step 2 fence always calls prepare with only `--root "$PWD"`. `REPO` in stdout therefore comes from the cwd repo, so `--file` can file into a different repo than the one whose bugs were mined when the operator passed `--repo`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add conditional `--repo "$REPO"` to the prepare invocation when Step 1 binds it, and pin that wiring in the structural harness.


### FINDING_7: Preserve retryability when automatic filing fails
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The durable scan marker is committed before automatic filing, while the generated report and batch file remain only under temporary RUN_DIR. Scenario: If `/issue --dry-run` or the create pass fails, the scan marker still advances and a later run may skip the same closed issues; the unfiled proposals have no durable retry artifact, so the requested filing can be permanently lost
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: For `--file`/`-s`, either commit the scan marker only after filing completes successfully, or persist the report and batch input in a durable retry location and retain a pending marker until all proposals are handled; keep the existing marker ordering for default approval-gated mode


### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: plan.txt:7
- **Concern**: [SCOPE-REDUCTION] Explicitly rejecting `-f` and every unknown flag breaks the existing contract that all unrecognized arguments are verbal search text. Scenario: An operator can currently mine bugs involving a CLI flag with input such as `--admin permission failures` or `-f handling`; the proposed parser would abort instead of translating that text into a GitHub search
- **Proposed resolution**: Parse `--file` and `-s` as new Boolean flags, validate values only for recognized value-taking flags, and preserve all other tokens as verbal description text; omit `-f` from the documented and recognized aliases without explicitly rejecting it


