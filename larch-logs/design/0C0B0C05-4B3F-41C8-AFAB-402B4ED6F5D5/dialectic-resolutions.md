## Dialectic Resolutions

### DECISION_1: Implicit vs explicit `--init-state-from-argv` mode flag
**Resolution**: Implicit — the presence of any per-key argv flag (`--branch-name` / `--issue-number` / etc.) is sufficient to opt into argv-init mode.
**Disposition**: voted
**Vote tally**: THESIS=2, ANTI_THESIS=1
**Thesis summary**: Implicit mode reuses the existing cold-start path in `ship-pr.sh:2431-2433` (`write_initial_state` already runs when `STATE_FILE` is absent); per-key flag prefixes plus required-key validation give the auditability the explicit-mode side asks for without a ceremonial mode flag at every callsite.
**Antithesis summary**: An explicit mode flag would make the state-creation boundary auditable and avoid parser-inference risk if more flags appear later; resume callers that pass argv must be loud about which run is initializing vs resuming.
**Why thesis prevails**: Judges agreed Defense A engaged the auditability concern directly (validation + namespace guards) while the antithesis leaned on speculative future-flag-reuse arguments that the cold-start guard already addresses; the ceremonial flag duplicates the implicit signal that "state file absent and new flags present" already carries.

### DECISION_2: Inline ordered key-list constant vs extract to `lib-ship-pr-state-keys.sh`
**Resolution**: Single ordered key-list constant inside `scripts/ship-pr.sh`, consumed by both `write_initial_state()` and `require_key` validation. The `skills/implement/SKILL.md` key list becomes a documentation echo, not the source.
**Disposition**: voted
**Vote tally**: THESIS=2, ANTI_THESIS=1
**Thesis summary**: ship-pr.sh is the single owner of the state-file contract; same-file drift between the emitter and the validator is impossible when both consume one in-file constant. The lib-finalize-state-keys.sh precedent only paid off because finalize-state has multiple consumers (`ship-pr.sh` + `restore-finalize-state.sh`), which is not the case here today.
**Antithesis summary**: The finalize-state precedent is concrete — `ship-pr.sh:18-19` already sources `lib-finalize-state-keys.sh`. Tests already exercise keys absent from the current `write_initial_state()` (e.g. `BAIL_FAILURE_DETAIL_LOG` in `test-ship-pr-fix-loop-2632.inc.sh`), demonstrating that schema drift between the emitter and downstream readers IS the failure mode the dedicated lib pattern guards against.
**Why thesis prevails**: Judges agreed Defense B (inline constant) was proportionate to the immediate scope (one consumer, one emitter); the dedicated lib's drift-guard value materializes only when a second consumer exists — which would happen as a follow-up change after a new caller appears, not in this PR.

### DECISION_3: Argv-init flag set — 7 caller-varying keys vs all 38
**Resolution**: Add flags only for the 7 caller-varying keys: `--branch-name`, `--issue-number`, `--run-id`, `--manifest-path`, `--tool-label`, `--expected-session-id`, `--expected-tmpdir-basename-prefix`. The constants (PHASE=checks, HAS_BUMP=true, all =false defaults, counters=0, empty strings) stay in `write_initial_state()`. Existing flags (`--merge`, `--draft`, `--forked`, `--repo`, `--implement-tmpdir`, `--no-logs-commit`) cover the remaining orchestrator-varying inputs.
**Disposition**: voted
**Vote tally**: THESIS=3, ANTI_THESIS=0
**Thesis summary**: The 38-key surface is dominated by state-machine internals (counters, phase flags, bail fields) with no legitimate caller-override use case today; the 7-flag interface is proportionate to the actual orchestrator-heredoc replacement need and avoids inflating the resume-must-match-flags hazard documented around `ship-pr-state.sh`.
**Antithesis summary**: Full 38-flag coverage would give tests and alternate orchestrators a complete, explicit injection surface, eliminating any "constant" inside `write_initial_state()` that future callers might need to override; the cost is ~30 additional `case` arms but they mostly duplicate literals already centralized.
**Why thesis prevails**: Unanimous judge agreement that the 7-key set is tightly scoped to demonstrated caller-varying inputs; speculative future caller flexibility does not justify a ~30-flag CLI surface expansion. If a near-term caller needs to seed a different constant value, a targeted follow-up flag is cheaper than carrying 38 flags from day one.
