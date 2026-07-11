# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_4: Frozen fallback accepts untrusted or pre-existing provenance
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-baseline-provenance
- **Severity**: major
- **Concern**: Frozen fallback trusts pre-seeded or persisted sidecar entries when their current file digests match, without proving that the entries came from this run’s verified porcelain observation or another run-owned change marker. Pre-existing dirty or untouched plan paths can therefore be treated as implemented, clearing `disposition_required`. In addition, paths authored by a later run-owned commit can be dropped when the worktree becomes clean and the persisted signature no longer matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-baseline-provenance: On frozen fallback, when porcelain is clean, also attribute plan paths from run-owned commits (for example `git diff --name-only <trusted-baseline>..HEAD` against a stored live merge-base SHA, or HEAD-range commits recorded at first coverage compute), or refresh/update provenance signatures for paths that reappear in porcelain instead of skipping paths already present in `retained`.


### FINDING_7: Remote symbolic-ref validation permits revision-expression syntax
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Remote symbolic-ref validation may allow values such as `origin/main^` or `origin/main:path`, which Git can interpret as revision expressions. Passing such values to `git merge-base` can select an unintended baseline and corrupt coverage attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Validate the complete ref with git check-ref-format or an equivalent strict allowlist, and add tests for revision-expression characters
