## Proposed Design Outline

### Goals
- Delete the inert task-notification defense stack: guard hooks, `bg_wait.py`, guard-only lints/harnesses, four env knobs, notification-era prose.
- Repoint the 11 Section E dual-use sentinels' consumers to the bgjob result env and delete the sentinels; KEEP only where a consumer cannot be repointed. Record a per-row decision.
- Pass all 7 acceptance criteria: extinct-token check plus clean `make lint`, `test-harnesses`, `py-lint`, `py-test`.

### Non-goals
- No behavior change to the bgjob machinery itself (criterion 7).
- Keep the coverage lint, the generic repeated-Read branch of `hook-anti-read-poll.sh`, and the replacement NEVER rule.
- No consumer migration; stale sidecars go inert and age out via `/cleanup`.

### Approach sketch
- A: delete `hook-bg-poll-guard.*` and `hook-no-progress-guard.*`, split `hook-anti-read-poll.sh` to the generic branch, prune `hooks/hooks.json`.
- B: delete `bg_wait.py` and call sites; strip marker/sidecar blocks from the six migrated wrappers; drop four env knobs.
- C: delete writer-parity lint and guard-only harnesses; trim mixed harnesses; fix `Makefile` targets/shards; keep coverage lint.
- D: delete `design-background-wait.md` and `wrapper-sentinel-before-stdout.md`, repoint referrers, apply verbatim replacement rules, sweep leftover prose.
- E: per-row sentinel audit; repoint to `bgjob/<step>.result.env`, update manifest and `migrated-scripts.tsv`, preserve pause/resume (I-Pause-1).

### Surfaces in scope
- `scripts/`, `hooks/hooks.json`, `Makefile`, `python/larch/{implement,design,state,lint,review}/`
- `skills/{design,implement,research}/`, `skills/shared/`, `.claude/rules/`, `AGENTS.md`, `docs/`, `SECURITY.md`
- `python/wire-artifact-manifest.json`, `python/migrated-scripts.tsv`, new extinct-token harness pin

### Open questions
- None. Sentinel posture resolved in Round 1 (full repoint-and-delete). Plan size may trigger the Step 2b.5 split.
