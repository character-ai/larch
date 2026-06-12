## Proposed Design Outline

### Goals
- Enable Tier B (`/implement` consumer and forked runs) to file failure reports cross-repo to the upstream larch repo, replacing chat-print-only behavior.
- Port terminal-failure and escalation-event reporting to `/design` with full stall-state machinery (state files, classification, attempts, escalation ledger), reusing the shared core from `stall-recovery-report.sh`.

### Non-goals
- No changes to Tier A behavior (larch dev clone filing via `/larch:issue` is unchanged).
- No changes to Tier B content composition (allowlists, TSV fields, bounded prose validation are unchanged).
- No failure reporting for non-terminal `/design` events (warnings already go to `execution-issues.md`).
- No new retry/recovery logic beyond what already exists.

### Approach sketch
- New `scripts/resolve-upstream-larch-repo.sh`: parse `.claude-plugin/plugin.json` `repository` URL, strip to `OWNER/REPO`.
- New `scripts/file-failure-report-cross-repo.sh`: signature dedup pre-pass via `gh issue list -R`, then `gh issue create -R` or `gh issue comment` ("+1 occurrence"), with chat-print fallback on failure.
- Extend `stall-recovery-report.sh compose-report`: Tier B path calls cross-repo filer; on success emits short filed notice; on failure falls back to existing chat-print path.
- Extend `stall-recovery-report.sh` with `--skill design` and `--artifact-prefix` flags for design-scoped parameterization.
- New `/design` teardown wiring in Step 6: detect terminal failure events, run design-side classification + escalation ledger recording, call the shared reporting engine.
- Update `SECURITY.md` and docs for cross-repo filing and consumer GitHub identity.

### Surfaces in scope
- `scripts/resolve-upstream-larch-repo.sh` (new)
- `scripts/resolve-upstream-larch-repo.md` (new sibling)
- `scripts/file-failure-report-cross-repo.sh` (new)
- `scripts/file-failure-report-cross-repo.md` (new sibling)
- `skills/implement/scripts/stall-recovery-report.sh`
- `skills/implement/scripts/stall-recovery-report.md`
- `skills/implement/scripts/test-stall-recovery-report.sh`
- `skills/implement/references/stall-recovery.md`
- `skills/design/scripts/design-failure-report.sh` (new)
- `skills/design/scripts/design-failure-report.md` (new sibling)
- `/design` SKILL.md (Step 6 wiring)
- `skills/design/references/design-failure-surface.md` (new)
- `SECURITY.md`

### Open questions
- Does the `/design` failure tracking need a dedicated new step in SKILL.md (like Step 18a), or can it be wired into Step 6 cleanup without a visible step number?
