## Decision 1: Port style
- **Question**: Should `dispatch-code-voters.sh` become a full in-process Python port, or a gzip-shim façade that delegates to embedded bash?
- **Resolution**: Full in-process port. Translate the bash logic to Python under `python/`, add colocated pytest, delete the bash script and harness. No shim, no embedded-bash delegation. Matches the C1a DoD (importable functions, no shims, pytest replaces harness) and the C1a5 waterfall precedent (`python/agent_waterfall.py`).
- **Source**: user

## Decision 2: Retirement-sweep breadth
- **Question**: How wide is the "final retirement sweep"?
- **Resolution**: Aggressive. The codebase shows every other C1a "Absorbs" script is already retired (launch-review, collect-agent-results, dispatch-with-waterfall, check-reviewers, wait-for-reviewers, run-negotiation-round, classify-diff-mode, gather-branch-context, compose-collector-failure-log); only `dispatch-code-voters.sh` remains on disk. So "aggressive" means a thorough stale-reference and dead-hook hunt across the whole C1a domain, not more script retirements. Hunt for: lingering text references to any already-retired C1a path, vestigial env-override hooks left after the port, and incomplete-cutover artifacts.
- **Source**: user + codebase

## Decision 3: Behavior to preserve (hard constraints)
- **Question**: What runtime behavior must the port preserve exactly?
- **Resolution**: All of: shrink-not-backfill panel sizing; the #3704 parallel dispatch (Claude voter launches concurrently with the external waterfall, no serial gate); `--no-fallback` waterfall with tool-name (not positional) slot mapping; parse-rate `NOT_SUBSTANTIVE` single retry with first-pass sidecar; voter `.done` sentinel barrier before size-based failure classification; prompt-integrity guard (render voter exit-code check + "Read the ballot" assertion); voter-failure logging to `execution-issues.md`; and every `VOTER_*` / `DISPATCH_OK` / `DEGRADED_PANEL_WARNING` / `VOTER_PATHS_FILE` KV emitted byte-identically (downstream `review core` / tally parse them).
- **Source**: issue + codebase

## Decision 4: C1b legacy review shells out of scope
- **Question**: Does the sweep also retire the C1b legacy review shells (`review-core.sh` and siblings)?
- **Resolution**: No. They stay in place. The port only retargets `review-core.sh`'s call site (the `REVIEW_CORE_DISPATCH_VOTERS_SH` default at line 92) to invoke `agent dispatch-voters`. Porting/retiring the C1b shells is #3677's domain.
- **Source**: issue + codebase

## Decision 5: Consumer cutover surface
- **Question**: Which live consumers must be retargeted off `dispatch-code-voters.sh`?
- **Resolution**: `python/legacy_review_shell/review-core.sh` call site; `docs/review-agents.md` and `docs/agents.md`; Makefile harness target; `agent-lint.toml` and any lint allowlists; `scripts/test-review-structure.sh` assertions (which currently require SKILL.md to name the bash script); the `python/test_voting.py` retired-path literal; and `skills/review/SKILL.md` references. Add the deleted paths to `python/migrated-scripts.tsv` with `#4170`, then make `lint-retired-scripts`, `py-test`, and `lint` green.
- **Source**: codebase
