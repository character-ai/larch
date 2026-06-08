### FINDING_1: Makefile mermaid lint target would drop retained setup and SIGPIPE checks
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `lint-mermaid` repoint only swaps in the Python mermaid linter, but fails to preserve the existing composite Makefile recipe: conditional `npm ci`, the mermaid lint invocation, and the SIGPIPE harness. This would make `make lint-mermaid` diverge from current local behavior and CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out the full retained recipe: keep the npm ci guard, swap only the linter invocation to python3 python/cli.py lint mermaid-fences --changed-only, and keep bash scripts/test-pipe-sigpipe-safety.sh as the final step. Mirror the same split in docs/linting.md if it describes the target.


### FINDING_2: Plan omits explicitly scoped `check-contains-pins` Python port
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan defers or excludes `check-contains-pins.sh` even though the supplied scope requires it to be ported as part of this P1 linter suite. Landing the plan as written would leave a required doc-facing linter in bash, without Python CLI registration, parity tests, consumer rewiring, retired-path manifest updates, and deletion of the bash source/harness/docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Remove the deferral and add the check-contains-pins Python port, CLI registration, pytest parity coverage, consumer rewiring, retired-path manifest entries, docs sweep, and deletion of the bash source/harness/siblings
  - From Codex-Edge: Either restore those surfaces to this plan, or block implementation until #3687 is actually re-scoped and the plan is regenerated against the amended issue
  - From Codex-Pragmatic: Revise the plan to include `check-contains-pins` plus the relevant-checks/lint-fix-loop cutover, or do not proceed under this issue until the binding issue scope is already changed outside the implementation plan
  - From Codex-Requirements: Add the `check-contains-pins` Python port, CLI registry row, fixture pytest from `scripts/test-check-contains-pins.sh`, caller repoints, retired-path manifest entries, and deletion steps.


### FINDING_3: Plan omits required `relevant-checks` / `lint-fix-loop` orchestration cutover
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan defers or excludes the required orchestration cutover from bash wrappers to `python/checks.py`. Landing as written would leave `ship-pr` and related flows calling `run-relevant-checks-captured.sh`, `lint-fix-loop.sh`, `surface-lint-fix-stderr-tail.sh`, or `scripts/relevant-checks.sh`, so the requested absorbed-bash deletion and Python dispatcher cutover would not happen.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Restore the orchestration cutover to this plan: repoint callers to the Python checks implementation, retire run-relevant-checks-captured.sh lint-fix-loop.sh surface-lint-fix-stderr-tail.sh and relevant harness/docs as specified, and update Makefile CI pre-commit docs and migrated-scripts.tsv accordingly
  - From Codex-Edge: Either restore those surfaces to this plan, or block implementation until #3687 is actually re-scoped and the plan is regenerated against the amended issue
  - From Codex-Pragmatic: Revise the plan to include `check-contains-pins` plus the relevant-checks/lint-fix-loop cutover, or do not proceed under this issue until the binding issue scope is already changed outside the implementation plan
  - From Codex-Requirements: Add the orchestration cutover: make `python/checks.py` run the relevant checks directly, repoint live consumers, retire/delete the absorbed bash wrappers and docs/harness references, update `migrated-scripts.tsv`, and keep/adjust existing `python/test_checks*.py` validation.


### FINDING_4: `gh-body-inline` parity contract narrows file discovery and misses untracked/fallback/exclusion behavior
- **Reviewer(s)**: Codex-Edge, Codex-dyn-parity-contract
- **Severity**: important
- **Concern**: The plan’s `gh-body-inline` contract describes scanning tracked `.sh`/`.py` files, but the current bash linter scans cached plus untracked non-ignored files, supports a non-git fallback, and excludes `larch-logs`. A Python port following the narrowed contract could miss fresh untracked violations or false-fail on excluded runtime artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update the plan contract to preserve git ls-files --cached --others --exclude-standard, the non-git find fallback, and larch-logs exclusions; keep the untracked-file pytest case
  - From Codex-dyn-parity-contract: Revise the contract to require git ls-files --cached --others --exclude-standard for .sh/.py, the non-git find fallback, symlink behavior, and larch-logs exclusion


### FINDING_5: Mermaid parity contract misses lazy `mmdc` resolution for zero-fence inputs
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The mermaid parity contract does not state that `mmdc` is resolved only after at least one mermaid fence is found. A port that checks for `mmdc` before scanning would fail no-fence Markdown or skipped `larch-logs` cases that currently exit successfully without Node tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add to the mermaid-fences parity contract and pytest: resolve mmdc only when fence_count>0; assert exit 0 with no mmdc for zero-fence inputs and for the explicit larch-logs skip case.


### FINDING_6: Mermaid parity contract misses `larch-logs/*` exclusion
- **Reviewer(s)**: Cursor-dyn-parity-contract
- **Severity**: important
- **Concern**: The mermaid parity contract omits the current `larch-logs/*` path filtering in both changed-only and explicit-file modes. A Python port following the plan could lint runtime artifacts and diverge from retained bash behavior and tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-parity-contract: Add larch-logs/* filtering to the mermaid-fences parity contract (and pytest), matching bash filtering and INFO: no Markdown files to lint when nothing remains


