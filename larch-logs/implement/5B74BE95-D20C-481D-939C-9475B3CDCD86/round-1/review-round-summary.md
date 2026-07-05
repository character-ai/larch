# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: refresh precedence can overwrite the persisted repo root
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-design-root
- **Severity**: important
- **Concern**: `write-design-env` refresh without `--repo-root` can prefer ambient `CLAUDE_PROJECT_DIR` / `REPO_ROOT` over the existing `source-env.sh` root, so a later refresh can rewrite `REPO_ROOT` to the wrong consumer path and make Gate C miss `ARCHITECTURAL_GUIDELINES.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Recover prior REPO_ROOT before env fallbacks when --repo-root is omitted; add refresh test with misleading CLAUDE_PROJECT_DIR
  - From codex-specialist-edge-cases: recover REPO_ROOT from the prior source-env.sh first and only use ambient env values when no persisted root exists
  - From dyn-dyn-design-root: On refresh when `--repo-root` is omitted, prefer the prior `source-env.sh` `REPO_ROOT` over ambient env fallbacks (keep env fallback only for first write when no prior file exists), or normalize env candidates through `consumer_repo_root` and reject paths that are not the git toplevel


