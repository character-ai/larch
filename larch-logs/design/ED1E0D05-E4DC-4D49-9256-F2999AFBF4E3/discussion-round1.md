## Decision 1: Refactor strictness
- **Question**: Pure behavior-preserving extraction, or allow opportunistic cleanups?
- **Resolution**: Small cleanups allowed. Bounded to the extracted glue (consolidate the two Step 3 fences, improve readability, emit one consistent KV set). MUST preserve all observable behavior: the full `LOOP_STATUS` allow-list values, every post-loop branch outcome, emitted KV names, artifacts (`ballot.txt`, `voting-tally.md`, round forensics, `.step3-plan-review-result.env`), and `review-round-count.txt` persist-vs-rollback semantics. `plan-review-loop.sh` internals are untouched.
- **Source**: user

## Decision 2: Build a shared phase-driver foundation
- **Question**: Build only the Step 3 driver, or also a reusable shared skeleton/lib for the other umbrella #3133 drivers?
- **Resolution**: Build a shared foundation in addition to the Step 3 driver.
- **Source**: user

## Decision 3: Foundation form (language)
- **Question**: The issue defers the implementation language ("pick the language when the foundation lands"). How does the shared foundation take shape now?
- **Resolution**: Create an actual shared **Bash** lib now (e.g. `lib-phase-driver.sh`), sourced by `run-step3-review.sh` and intended for the other 5 drivers. This **deliberately overrides** the issue's "Bash-vs-Python out of scope / language deferred" note. Accepted risk: the shared layer may need re-homing when the planned Python infra lands — surface this in the plan's tradeoffs/failure-modes.
- **Source**: user

## Decision 4: Resume / idempotency
- **Question**: Implement a working `--resume-from` flag now, or preserve existing idempotency?
- **Resolution**: Preserve the existing idempotency surface — SKILL.md `.completed/step-3` completion sentinel + `review-round-count.txt` persist/rollback. Document the convention in the `.md` sibling. NO new `--resume-from` flag (mirrors `run-step2-dispatch.sh`, which has none).
- **Source**: user

## Decision 5: Work-item boundary
- **Question**: Does this design cover sibling umbrella #3133 drivers?
- **Resolution**: No. Scope is ONLY #3244 — the Step 3 plan-review phase driver — plus the shared foundation it establishes. The shared contract is specified generically, but only Step 3 is wired to it now. The other 5 drivers remain separate work items.
- **Source**: codebase / issue

## Decision 6: LLM boundary preserved
- **Question**: What stays in the orchestrator vs. moves into the driver?
- **Resolution**: The driver owns the deterministic state machine (cap guard, HARD round-cursor read/advance, `plan-review-loop.sh` invocation, result-env parse + stdout-KV fallback, `LOOP_STATUS` normalization, round-count persist/rollback). It STOPS at the LLM boundary: semantic finding dedup (Anti-pattern #6), Gate B (Step 3.5), and the `main-agent-vote-required` ballot adjudication all stay in the orchestrator. The driver emits a normalized status and hands back; the orchestrator dispatches gates and re-invokes.
- **Source**: issue

## Decision 7: Cross-cutting deliverables (mandatory)
- **Question**: What supporting artifacts must ship in the same PR?
- **Resolution**: `.md` sibling per new `.sh`; `test-*.sh` harness(es) + Makefile wiring; `scripts/test-design-structure.sh` fence-count / literal-anchor pin updates for the removed inline blocks; source-env + pause-check prelude preserved on every remaining Step 3 fence; file-based state handoff only (`source-env.sh` + result `.env`); quiet contract (`lib-quiet.sh` `emit_kv`, bulk → file); call `design-driver.sh` ACTIONs where applicable (do not duplicate the dispatcher). Also update `.claude/rules/launcher-argv-test-coverage.md` to register the new driver→harness mapping.
- **Source**: issue cross-cutting + repo rules
