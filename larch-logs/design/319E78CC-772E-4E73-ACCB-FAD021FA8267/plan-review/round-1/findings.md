### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:80-81
- **Concern**: Makefile lint-mermaid repoint omits the existing npm ci guard and bundled SIGPIPE step. Scenario: The current Makefile:1146-1149 recipe is a three-part composite (conditional npm ci, mermaid --changed-only, then test-pipe-sigpipe-safety.sh). Repointing only the middle line to python3 python/cli.py lint mermaid-fences --changed-only drops local Node bootstrap and skips the SIGPIPE harness that CI still runs in the lint-mermaid job; make lint-mermaid then diverges from today and from CI.
- **Proposed resolution**: Spell out the full retained recipe: keep the npm ci guard, swap only the linter invocation to python3 python/cli.py lint mermaid-fences --changed-only, and keep bash scripts/test-pipe-sigpipe-safety.sh as the final step. Mirror the same split in docs/linting.md if it describes the target.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:7-9; scripts/relevant-checks.sh:369-381
- **Concern**: Plan defers check-contains-pins even though the binding scope explicitly includes porting check-contains-pins.sh. Scenario: After the PR lands, relevant-checks still invokes scripts/check-contains-pins.sh, so one of the specified doc-facing linters remains in bash and the Definition of Done is incomplete
- **Proposed resolution**: Remove the deferral and add the check-contains-pins Python port, CLI registration, pytest parity coverage, consumer rewiring, retired-path manifest entries, docs sweep, and deletion of the bash source/harness/siblings

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:7-9; scripts/ship-pr.sh:138-142; scripts/ship-pr.sh:805-833; scripts/ship-pr.sh:913-924
- **Concern**: Plan defers the relevant-checks and lint-fix-loop orchestration cutover that the binding scope requires. Scenario: After the PR lands, ship-pr and related flows still call run-relevant-checks-captured.sh and lint-fix-loop.sh instead of the existing python/checks.py path, so the requested cutover and absorbed-bash deletion do not happen
- **Proposed resolution**: Restore the orchestration cutover to this plan: repoint callers to the Python checks implementation, retire run-relevant-checks-captured.sh lint-fix-loop.sh surface-lint-fix-stderr-tail.sh and relevant harness/docs as specified, and update Makefile CI pre-commit docs and migrated-scripts.tsv accordingly

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:7-9; python/checks.py:281; scripts/relevant-checks.sh:369-373
- **Concern**: Plan defers explicitly scoped check-contains-pins and relevant-checks/lint-fix-loop cutover work. Scenario: The supplied #3687 scope requires check-contains-pins and orchestration cutover; implementing this plan as-is leaves check-contains-pins in bash and leaves python/checks.py shelling out to scripts/relevant-checks.sh, so the stated DoD is unmet
- **Proposed resolution**: Either restore those surfaces to this plan, or block implementation until #3687 is actually re-scoped and the plan is regenerated against the amended issue

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:29; scripts/lint-gh-body-inline.sh:45-58; scripts/test-lint-gh-body-inline.sh:250-259
- **Concern**: gh-body parity contract narrows scanning to tracked files. Scenario: The current linter scans tracked plus untracked non-ignored .sh/.py files and the harness expects an untracked scripts/untracked-git-bad.sh violation; a port implemented from the plan line would silently miss untracked inline gh --body/--notes before commit
- **Proposed resolution**: Update the plan contract to preserve git ls-files --cached --others --exclude-standard, the non-git find fallback, and larch-logs exclusions; keep the untracked-file pytest case

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:26-27 / scripts/lint-mermaid-fences.sh:211-244
- **Concern**: Mermaid parity contract omits lazy mmdc resolution when a file has zero extracted fences. Scenario: Bash only calls ensure_mmdc inside the per-fence loop; markdown with no mermaid fences (or only larch-logs skips) exits 0 even if mmdc is missing. A port that resolves mmdc before scanning fences would fail local/CI runs without Node tooling on no-fence changes.
- **Proposed resolution**: Add to the mermaid-fences parity contract and pytest: resolve mmdc only when fence_count>0; assert exit 0 with no mmdc for zero-fence inputs and for the explicit larch-logs skip case.

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:3-9
- **Concern**: The plan defers `check-contains-pins.sh` and the relevant-checks/lint-fix-loop cutover even though the binding P1 scope explicitly includes them. Scenario: The PR would land only six leaf linters while leaving required P1 work incomplete against the current issue definition
- **Proposed resolution**: Revise the plan to include `check-contains-pins` plus the relevant-checks/lint-fix-loop cutover, or do not proceed under this issue until the binding issue scope is already changed outside the implementation plan

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:3-9
- **Concern**: The plan defers `check-contains-pins.sh` even though the binding scope explicitly lists it as a ported linter.. Scenario: P1 would ship without a required Python linter, CLI verb, pytest coverage, consumer repointing, migrated-scripts entry, and deletion of `scripts/check-contains-pins.sh` plus its harness/docs.
- **Proposed resolution**: Add the `check-contains-pins` Python port, CLI registry row, fixture pytest from `scripts/test-check-contains-pins.sh`, caller repoints, retired-path manifest entries, and deletion steps.

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:7-9,19,130-138
- **Concern**: The plan excludes the required `relevant-checks` / `lint-fix-loop` orchestration cutover and instead keeps the bash wrappers alive.. Scenario: After the PR, the feature still would not cut `relevant-checks.sh`, `run-relevant-checks-captured.sh`, `lint-fix-loop.sh`, or `surface-lint-fix-stderr-tail.sh` over to `python/checks.py`; current integration points such as `python/checks.py:243-281` still shell out to `scripts/relevant-checks.sh`.
- **Proposed resolution**: Add the orchestration cutover: make `python/checks.py` run the relevant checks directly, repoint live consumers, retire/delete the absorbed bash wrappers and docs/harness references, update `migrated-scripts.tsv`, and keep/adjust existing `python/test_checks*.py` validation.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-parity-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-mermaid-fences.sh:110-122
- **Concern**: Parity contract omits larch-logs/* path exclusion in both --changed-only and explicit-file modes. Scenario: A Python port driven only by the plan contract would still lint runtime artifacts under larch-logs/, diverging from bash and failing the retained test-mermaid-fragments.sh explicit-skip case (~269-288)
- **Proposed resolution**: Add larch-logs/* filtering to the mermaid-fences parity contract (and pytest), matching bash filtering and INFO: no Markdown files to lint when nothing remains

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-parity-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:29; scripts/lint-gh-body-inline.sh:45-64; scripts/test-lint-gh-body-inline.sh:236-259
- **Concern**: F1 gh-body-inline contract says scan tracked .sh/.py, but bash scans git cached plus untracked non-ignored files, has a non-git fallback, and skips larch-logs. Scenario: The Python port can miss a fresh untracked bad .sh/.py under pass_filenames false, or false-fail on larch-logs, breaking parity and the ported harness
- **Proposed resolution**: Revise the contract to require git ls-files --cached --others --exclude-standard for .sh/.py, the non-git find fallback, symlink behavior, and larch-logs exclusion

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-consumer-sweep
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .github/workflows/requirements-lint.txt:1-4
- **Concern**: PyYAML sync comment still ties requirements-lint.txt to lint-skill-invocations additional_dependencies. Scenario: Plan drops lint-skill-invocations hook additional_dependencies (stdlib port) but line 1 still says both must stay in sync; basename git grep for the six retired script paths never matches this file, and it is not in the explicit UPDATED list
- **Proposed resolution**: A named step: rewrite the header to document PyYAML only for remaining consumers (check-topology-rule-paths hook additional_dependencies and CI pre-commit env), not lint-skill-invocations

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-consumer-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/pre-commit-shellcheck.md:25
- **Concern**: PyYAML edit-in-sync rule still names lint-skill-invocations additional_dependencies and scripts/lint-skill-invocations.md. Scenario: After the hook moves to language: system and scripts/lint-skill-invocations.md is deleted, this rule is wrong; implementers following scripts/*.md contracts may retain or mis-apply a dead two-way pin
- **Proposed resolution**: Add an explicit UPDATED bullet (or tighten the stale-reference sweep) to retarget the pin rule at check-topology-rule-paths (and requirements-lint.txt), drop the deleted .md pointer, and note lint-skill-invocations no longer uses PyYAML

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-consumer-sweep
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/sanitize-mermaid-fragment.md:5,18
- **Concern**: Retained contract still points broader validation at scripts/lint-mermaid-fences.sh. Scenario: Only test-mermaid-fragments.sh is named for update; these .md siblings are left to the generic scripts/*.md sweep and are easy to miss after the .sh is deleted
- **Proposed resolution**: Include scripts/sanitize-mermaid-fragment.md and scripts/test-mermaid-fragments.md in the explicit stale-reference checklist (or repoint to python3 python/cli.py lint mermaid-fences)

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-consumer-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.tsv.md:34; scripts/pre-commit-shellcheck.md:25
- **Concern**: Stale-reference sweep omits retired .md sibling paths. Scenario: The plan appends/deletes linter .md siblings in python/migrated-scripts.tsv, but the concrete sweep only targets the six .sh/.py linter paths. These retained docs still cite scripts/lint-readability-preamble.md and scripts/lint-skill-invocations.md, so lint retired-scripts would fail after the manifest append.
- **Proposed resolution**: Expand the sweep to grep every manifest-added retired path, including .md siblings, and update these retained docs.

### OOS_1:
- **Description**: Retaining test-lint-readability-preamble as a pytest wrapper duplicates coverage already exercised by make py-test. Scenario: Same pytest module runs in shard 20 and again in the python-tests job; extra wall-clock only, not a functional gap.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: Makefile:578-579 / .github/workflows/ci.yaml:592
- **Phase**: design

### OOS_2:
- **Description**: Historical note still cites scripts/lint-readability-preamble.sh as the fixed em-dash example. Scenario: Stale prose only; no runtime coupling once the bash linter is retired
- **Reviewer**: Cursor-dyn-consumer-sweep
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/lint-awk-multibyte-regex.md:6,27
- **Phase**: design
