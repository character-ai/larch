## Goal
Implement issue #7553: [IMPLEMENTING] Remove migrated local linters after agent-lint adoption.

## Implementation Plan
## Summary

Remove larch's local copies of general-purpose agent and skill linters after agent-lint ships equivalent coverage.

## Blocker

Blocked by: https://github.com/zhupanov/agent-lint/issues/107

Do not start removal until the agent-lint issue is closed by a tagged release that larch can pin.

## Local checks to retire

- `agent-tool-contract`
- `skill-invocations`
- `skill-md-flag-signature`
- `skill-awk-field-refs`
- `skill-description-length`
- `bare-grep-probe`
- the local stronger `consecutive-bash`
- `skill-closure-growth`
- `tier1a-size`
- `doc-pointer-paths`
- `gh-body-inline`
- `renderer-substitution-safety`
- `bash32`
- `awk-multibyte-regex`

## Work

1. Upgrade and pin agent-lint to the release that closes the blocker.
2. Configure the new rules to preserve larch's intended strictness, including the checked-in prompt-closure budget, the Tier-1a root-import caps, and the 200-character skill description cap.
3. Translate valid local suppressions or baselines into agent-lint configuration. Remove stale exceptions instead of copying them.
4. Run agent-lint against the whole larch tree and compare its findings with every local check before deleting code. For `skill-closure-growth` and `tier1a-size`, expect semantic differences rather than byte parity: the generalized closure scanner need not reproduce larch's eager/conditional classification or content-token metrics. Retire each only if the configured agent-lint budget still blocks the growth the local ratchet exists to catch; otherwise keep that check local and narrow this issue.
5. Remove the retired Python lint modules, thin wrappers, the Bash linter, companion tests and fixtures, CLI registry rows, Makefile targets, pre-commit hooks, baseline files, `python/lint-module-manifest.json` rows, `scripts/residual-bash-paths.txt` rows for retired shell wrappers, and `docs/linting.md` entries. Update the `BASH_AUTHORING.md` sections that reference retired lint commands and pragma grammars (`make lint-bash32`, `lint-bare-grep-probe`, renderer substitution) to point at the pinned agent-lint rules; the authoring guidance itself stays.
6. Keep larch-only checks and unrelated general language linters unchanged, including the explicitly kept-local `em-dash-output`, `literal-counts`, and `git-push-refspec` (see the blocker issue's scope boundary).

## Acceptance

- The pinned agent-lint release covers every retired check.
- Each local check passes immediately before removal, and agent-lint passes immediately after removal on the same tree.
- No retired lint command, hook, test target, baseline, manifest row, residual-bash manifest row, or documentation entry remains, including in `BASH_AUTHORING.md`.
- `make lint`, `make py-lint`, `make py-test`, and the relevant changed-file checks pass.
- The larch issue has a verified native blocked-by relation to the agent-lint issue, or a cross-repository blocker link if GitHub does not permit the native relation.

*Amended 2026-07-16 after a completeness audit: added `skill-description-length` and `tier1a-size` to the retire list, the byte-parity expectation for the closure checks, the kept-local note, and the `BASH_AUTHORING.md` / residual-bash removal surface.*

## Test plan
(no test plan section in plan-file)
