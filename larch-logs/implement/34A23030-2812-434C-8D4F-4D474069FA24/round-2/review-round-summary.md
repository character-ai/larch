# Review Round 2

- Mode: `diff`
- Accepted findings: 1
- Rejected findings: 0
- Exonerated findings: 2
- Neutral findings: 1

## Accepted Findings

### FINDING_2: **correctness** `skills/implement/SKILL.md:64` — NEVER #16’s recovery clause tells the reader to read `ship-pr-state.sh` and then re-invoke `ship-pr.sh` with the same argv as the Step 8+ `Invoke:` block, but `scripts/ship-pr.sh` keeps `--auto-mode` and `--no-admin-fallback` only as per-invocation CLI globals (`AUTO_MODE`, `NO_ADMIN_FALLBACK` around lines 28–29 and 143–144 in `scripts/ship-pr.sh`), not as durable keys in the initial `ship-pr-state.sh` template (`write_initial_state` around lines 268–305 in `scripts/ship-pr.sh`). After a timeout or turn break, an operator can faithfully read `PHASE`/`MERGE`/`DRAFT`/`REPO`/`FORKED_TARGET`/`NO_LOGS_COMMIT` from state yet still guess wrong `--auto-mode` / `--no-admin-fallback` values, so the guidance slightly over-implies that `ship-pr-state.sh` alone is enough context for a bit-perfect replay of the `Invoke:` argv. **Suggested fix:** In NEVER #16’s “How to apply” recovery sentence, spell out that flags not represented in `ship-pr-state.sh` (at minimum `--auto-mode` and `--no-admin-fallback`, matching `scripts/ship-pr.sh`’s argv model) must be taken from the same sources the orchestrator used originally (e.g. `$IMPLEMENT_TMPDIR/session-env.sh` for `LARCH_AUTO_MODE` where applicable, plus the originating `/implement` flag memory), while `ship-pr-state.sh` remains the authority for persisted `PHASE` / resume semantics.
- **Reviewer**: dyn-resume-phase-token-accuracy-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:64` — NEVER #16’s recovery clause tells the reader to read `ship-pr-state.sh` and then re-invoke `ship-pr.sh` with the same argv as the Step 8+ `Invoke:` block, but `scripts/ship-pr.sh` keeps `--auto-mode` and `--no-admin-fallback` only as per-invocation CLI globals (`AUTO_MODE`, `NO_ADMIN_FALLBACK` around lines 28–29 and 143–144 in `scripts/ship-pr.sh`), not as durable keys in the initial `ship-pr-state.sh` template (`write_initial_state` around lines 268–305 in `scripts/ship-pr.sh`). After a timeout or turn break, an operator can faithfully read `PHASE`/`MERGE`/`DRAFT`/`REPO`/`FORKED_TARGET`/`NO_LOGS_COMMIT` from state yet still guess wrong `--auto-mode` / `--no-admin-fallback` values, so the guidance slightly over-implies that `ship-pr-state.sh` alone is enough context for a bit-perfect replay of the `Invoke:` argv. **Suggested fix:** In NEVER #16’s “How to apply” recovery sentence, spell out that flags not represented in `ship-pr-state.sh` (at minimum `--auto-mode` and `--no-admin-fallback`, matching `scripts/ship-pr.sh`’s argv model) must be taken from the same sources the orchestrator used originally (e.g. `$IMPLEMENT_TMPDIR/session-env.sh` for `LARCH_AUTO_MODE` where applicable, plus the originating `/implement` flag memory), while `ship-pr-state.sh` remains the authority for persisted `PHASE` / resume semantics.
- **Suggested revision**: Address the concern above.


