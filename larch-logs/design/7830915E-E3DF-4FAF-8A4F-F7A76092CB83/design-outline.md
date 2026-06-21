## Proposed Design Outline

### Goals
- Make OOS reviewer points fate-aware: a filed OOS issue that dies unfixed or is combined away stops counting as a durable `+1`.
- Report a fate-adjusted OOS scoreboard built from committed run logs joined to current GitHub issue fate.
- Feed `/combine-issues` and `/analyze-issues` outcomes into that adjustment.

### Non-goals
- No change to the live tally: `python/voting.py::classify_result` and the OOS `+1` award stay as-is (provisional).
- No rewrite of committed `larch-logs/*` TSVs; no new committed reviewer ledger; nothing auto-committed.
- No `-1` penalty; still-open and stale `[OOS]` points are left unchanged.

### Approach sketch
- Add a retroactive reconciler in `python/analyze_issues.py`. Join proposer label → filed OOS issue URL → current GitHub fate from committed run-log OOS artifacts.
- Classify fate: closed by a fixing/merged PR keeps `+1`; closed-unfixed (wontfix / not-planned) and combined-away map to `0`; still-open stays provisional.
- Surface a "Fate-adjusted OOS scoring" section in the `/analyze-issues` report (diagnostic only, like `/voter-calibration`).
- Teach `/combine-issues` to durably record a combined-away mapping so that fate is unambiguous.

### Surfaces in scope
- `python/analyze_issues.py` + `python/test_analyze_issues.py`
- `/combine-issues` skill and its `python/cli.py combine-issues` backing (durable combined-away record)
- Committed `larch-logs/{design,implement}/` OOS artifacts (TSVs, `oos-issues.ndjson`, `oos-accepted-*.md`)
- Docs: `docs/point-competition.md`, `skills/shared/voting-protocol.md` (note provisional/fate-aware semantics)

### Open questions
- OOS origin coverage: default covers filed OOS from committed run logs regardless of skill (`/design` + `/review`), keyed by proposer label + filed issue URL; primary evidence from `/design`. Confirm, or narrow to `/design`-only.
- Report home: a new section inside `/analyze-issues` output (default) vs a separate focused report.
