## Goal
Implement issue #7296: [IMPLEMENTING] Sweep stale SECURITY.md file pointers and add a doc-pointer-paths lint.

## Implementation Plan
## Plan

## Approach

Update stale security-control references before enabling the lint. Implement one focused Python lint behind `python/cli.py`. Keep its scope fixed to `AGENTS.md` and `SECURITY.md`.

Confidence: high. The stale pointers, current module locations, and lint integration points are directly visible.

## Files to modify/create

### UPDATED: SECURITY.md

- Replace moved flat-module pointers with their current package paths under `python/larch/` and `python/tests/`.
- Rewrite or remove passages for deleted machinery, including the retired Step 3.6 assessor lane.
- Explicitly update the Step 0 session-setup row to the current `python/cli.py bootstrap invoke` and session setup workflow.
- Update the run-log publication row and breadcrumb block to the Python implementation: `python/cli.py run-log publish-breadcrumbs` and `python/larch/report/run_log_commit.py`.
- Sweep every stale citation in the affected security-control passages, including bare backticked `*.sh` names and other unprefixed deleted machinery; do not treat the 24 prefix-filtered occurrences as exhaustive.
- Describe gitignored developer-local generated artifacts without path-shaped inline-backtick tokens, including the local settings and generated hook-audit log. Retain accurate generated-artifact guidance without relying on suppression or local filesystem state.
- Do not retain dead pointers through suppression. When removing rather than repointing a SECURITY.md passage, record a one-line deletion rationale for that row in the PR description.
- Re-run the specified enumeration and confirm it prints nothing for both Tier-1 documents.

### NEW: python/larch/lint/lint_doc_pointer_paths.py

- Expose `main(argv) -> int` with the standard `0` clean, `1` findings, and `2` tool-error contract.
- Resolve the repository root from `--root`, defaulting to the checkout root. Accept no positional document-path arguments; the lint always scans both required Tier-1 documents.
- Scan only `AGENTS.md` and `SECURITY.md` as UTF-8 regular files. Fail loudly on missing, unreadable, symlinked, or non-regular required inputs.
- Track Markdown fence state by toggling when a stripped line starts with three backticks. Skip all fenced content.
- Extract inline-backtick tokens. Keep only tokens with an approved prefix, a slash, and none of the forbidden placeholder characters or whitespace.
- Explicitly ignore `larch-logs/` run-generated paths.
- Strip a trailing `::symbol` or `#fragment` before checking the root-relative file path. Reject candidates that escape the repository root.
- Support `<!-- lint-doc-pointer-paths: ok <reason> -->` on the same line. A non-empty reason suppresses that line; an empty-reason pragma is a finding even when no dead pointer is present.
- Emit deterministic findings keyed by document, line, and token. Include all three fields in each diagnostic and report multiple dead tokens independently.
- Use no baseline. Existing violations must be fixed in this change.

### NEW: python/tests/lint/test_lint_doc_pointer_paths.py

- Build isolated Tier-1 document fixtures and cover:
  - dead pointers fail with file, line, and token;
  - live pointers pass;
  - multiple tokens produce separate deterministic findings;
  - fenced examples are skipped;
  - placeholder and whitespace-bearing tokens are skipped;
  - `larch-logs/` paths are skipped;
  - `::symbol` and `#fragment` suffixes check only the file portion;
  - reason-bearing same-line suppressions pass;
  - missing-reason suppressions fail;
  - root-escaping candidates do not pass by resolving to an external file;
  - unreadable, missing, symlinked, or malformed required inputs return the tool-error exit.
- Exercise the public `main` contract and the CLI registration path.

### UPDATED: python/larch/cli.py

- Register `("lint", "doc-pointer-paths")` to `larch.lint.lint_doc_pointer_paths.main`.

### UPDATED: python/lint-module-manifest.json

- Add the sorted `lint_doc_pointer_paths.py` record as `new-module-justified`.
- Cite the active commissioning issue and explain why a dedicated Tier-1 Markdown path scanner is the smallest suitable host.

### UPDATED: Makefile

- Add `lint-doc-pointer-paths` and its focused test target to `.PHONY`.
- Add the lint to `py-lint-checks-fast` beside `markdown-heading-fence-state`.
- Add it to the local `lint` battery so local and Python-lint CI paths stay aligned.

### UPDATED: .pre-commit-config.yaml

- Add an always-run `lint-doc-pointer-paths` hook invoking the registered CLI verb.
- Use `language: system` and `pass_filenames: false`, because the command accepts no positional paths and always scans both Tier-1 documents.
- Scope its `files:` regex to `AGENTS.md`, `SECURITY.md`, the lint implementation, its tests, and `python/lint-module-manifest.json`.
- This makes the existing CI `lint-only` job enforce the rule without a new workflow job.

### UPDATED: docs/linting.md

- Add the lint to the table.
- Document its two-file scope, fence and placeholder handling, suffix stripping, reason-bearing suppression syntax, no-baseline policy, direct command, Make target, CI coverage, and focused test path.

## Edge cases

- A line may contain several dead tokens but only one valid suppression comment.
- Fence delimiter lines are not scanned.
- Runtime-generated paths must not force fake committed placeholders or remain as path-shaped inline tokens in the Tier-1 documents.
- Fragment or symbol suffixes must not become part of the filesystem probe.
- A path that starts with an allowed prefix but escapes through `..` must fail.

## Failure modes

- Return `2` when the scan cannot establish trustworthy input or repository-root state.
- Return `1` for dead pointers and malformed suppressions.
- Keep findings stable and complete so CI identifies every offending token in one run.
- Do not add a baseline that would allow the current stale set to survive.

## Testing strategy

- Run `python3 -m pytest python/tests/lint/test_lint_doc_pointer_paths.py`.
- Run `python3 python/cli.py lint doc-pointer-paths` in a clean tree or fixture tree without gitignored developer-local artifacts.
- Run the supplied enumeration procedure and confirm it prints nothing for both documents.
- Inspect the final SECURITY.md diff against acceptance criterion 7 and include a one-line PR-description deletion rationale for every removed, rather than repointed, security-control passage.
- Run `python3 python/cli.py lint module-manifest`.
- Run the focused pre-commit hook for the changed Tier-1 documents and lint files.
- Verify the existing `lint-only` and `py-lint-checks-fast` CI entrypoints include the new lint.

## Acceptance

- Run `python3 -m pytest python/tests/lint/test_lint_doc_pointer_paths.py`.
- Run `python3 python/cli.py lint doc-pointer-paths` in a clean tree or fixture tree without gitignored developer-local artifacts.
- Run the supplied enumeration procedure and confirm it prints nothing for both documents.
- Inspect the final SECURITY.md diff against acceptance criterion 7 and include a one-line PR-description deletion rationale for every removed, rather than repointed, security-control passage.
- Run `python3 python/cli.py lint module-manifest`.
- Run the focused pre-commit hook for the changed Tier-1 documents and lint files.
- Verify the existing `lint-only` and `py-lint-checks-fast` CI entrypoints include the new lint.

oversize_override: operator
diff_lines: 445

## Test plan
(no test plan section in plan-file)
