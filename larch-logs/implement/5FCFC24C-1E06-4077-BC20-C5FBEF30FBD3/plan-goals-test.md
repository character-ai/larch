## Goal
Implement issue #7540: [IMPLEMENTING] contract-unification [DEDUP] Port logic-bearing implement step scripts and share the bgjob-wait stem.

## Implementation Plan
#### Problem

Five implement step scripts still carry orchestration logic in Bash and copy the same helper cluster: `rehydrate_plugin_root()` four times (10-22 lines each, identical awk-fallback body), `read_session_key()` four times, and `rehydrate_larch_triplet()` byte-identical between `step-0-bootstrap.sh` and `step-0-degraded-gate.sh`. Three design step scripts (`design-step3-mav.sh:71`, `design-step35.sh:65`, `design-step3-review.sh:149`) copy the same `_cpr_literal` unexpanded-placeholder guard. AGENTS.md bans shared terminal Bash libraries, so these copies cannot be deduplicated in Bash. Separately, the bgjob WAIT/DEAD/DONE contract stem is re-inlined across skill prose: `skills/design/SKILL.md` carries 4 occurrences (three byte-identical), `skills/implement/SKILL.md` still re-inlines 5 blockquote stems while 7 other sites already point at `skills/shared/bgjob-wait.md`, and two research reference files inline it too.

#### Goal

Port the remaining logic-bearing step scripts in-process, following the #7483, #7484, and #7485 pattern, and make `skills/shared/bgjob-wait.md` the only home of the wait-contract stem.

#### Required implementation

- Port `step-0-bootstrap.sh`, `step-0-degraded-gate.sh`, `step-8-ship.sh`, `step-8-seed-initial.sh`, and `step-18.sh` (all under `skills/implement/scripts/`) onto `python3 python/cli.py implement ...` verbs. Leave 8-line thin wrappers like their converted siblings.
- Move the `_cpr_literal` guard into the shared Python entry the three design scripts call, or port those scripts the same way if they are thin enough.
- Replace each re-inlined bgjob stem with the standard one-line pointer to `skills/shared/bgjob-wait.md`, keeping only per-step routing KVs inline.
- Update `scripts/residual-bash-paths.txt` per the migration playbook. No shims.

#### Exclusions

`hook_emit` copies stay; BASH_AUTHORING.md blesses per-hook local definitions. Do not add a manifest-listed Bash include unless the port is infeasible for a specific script; justify any exception in the PR.

#### Size and acceptance

Expected change: 600-1,000 lines. Split (scripts port vs prose stems) if oversize. `make lint-bash32`, the bare-grep-probe lint, skill structure tests, and the implement harnesses stay green. The tracked Bash line count drops.

## Test plan
(no test plan section in plan-file)
