## Dialectic Resolutions

### DECISION_1: Merge mechanism for log-flush PR
**Resolution**: Direct `gh pr merge --squash --admin --delete-branch` (not merge-pr.sh)
**Disposition**: fallback-to-synthesis
**Thesis summary**: (no debate — thesis output truncated after `<claim>` opener; missing 4 required tags and RECOMMEND line)
**Antithesis summary**: Extending merge-pr.sh with a `--logs-only` mode preserves one audited admin-merge path and reuses OID recovery and `MERGE_RESULT` emission; the dedicated publisher that bypasses it forks merge semantics.
**Why fallback**: missing_tag — Cursor thesis output truncated; debate quorum not met (thesis side failed tag/RECOMMEND checks)

### DECISION_2: Helper script location
**Resolution**: `scripts/design-log-publish.sh`
**Disposition**: fallback-to-synthesis
**Thesis summary**: Step 5 already calls top-level `scripts/timing-ledger.sh`, `redact-secrets.sh`, `plan-block-write.sh`; `scripts/larch-log-flush.sh`, `create-pr.sh`, `merge-pr.sh` are all top-level precedents; top-level placement keeps `skills/design/SKILL.md` as a caller.
**Antithesis summary**: The proposed helper bundles `/design`-specific completion policy (issue title, logs, PR, cleanup) and is not a reusable repo-wide primitive; co-locating under `skills/design/scripts/` makes design-specific ownership clear.
**Why fallback**: 1-1 tie with 2 voters — Cursor judge ineligible (no vote line emitted); Codex-1 voted DEFENSE_A (`skills/design/scripts/`), Codex-2 voted DEFENSE_B (`scripts/`)
