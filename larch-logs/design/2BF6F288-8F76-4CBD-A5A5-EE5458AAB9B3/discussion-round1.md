## Decision 1: Cutover completeness
- **Question**: Should the design rewrite orchestrator-facing prose to delegate to the new helpers, or add helpers only?
- **Resolution**: Full cutover — rewrite `stall-recovery.md` steps 7-8 and `SKILL.md` Step 18b `_wfr_` block to call the new `clear-stall` / `seed-terminal-state` subcommands and the E2 wrapper, replacing the hand-executed sequences.
- **Source**: user

## Decision 2: E2 wrapper home
- **Question**: Where should the E2 final-report EMIT_BODY wrapper live?
- **Resolution**: New standalone script under `skills/implement/scripts/` (with sibling `.md` + test harness); `write-final-report.sh` stays the pure renderer (single responsibility).
- **Source**: user

## Decision 3: Preserved invariants (hard constraints)
- **Question**: What existing behavior must be preserved exactly?
- **Resolution**: (a) three-layer `STALL_TRACKING` resolution (in-memory -> ship-pr-state.sh -> session-env.sh); (b) success-path "clear disk before memory" ordering (steps 7.1-7.7); (c) canonical Step-8 `ship-pr-state.sh` key shape on terminal seed (steps 8.1-8.3) incl. `BAIL_FAILURE_DETAIL_LOG` preservation when already pointing at the canonical detail log; (d) NEVER #13 (no prompt-side `finalize-state.sh` mutation); (e) NEVER #20 (verbatim `summary-final.md` emit + `.step17-printed`/`.step17-emitted` sentinels stay prompt-side; the E2 wrapper only DECIDES `EMIT_BODY`, it never emits the body or writes the emission sentinel).
- **Source**: codebase

## Decision 4: Region disjointness / non-goals
- **Question**: What is explicitly out of scope?
- **Resolution**: No changes to `ship-pr.sh` (E1=18a, E2=18b are disjoint from it). The in-memory `STALL_TRACKING` clear (step 7.6), bug-comment generation/posting, dry-run eval, and `ISSUE_NUMBER` load remain prompt-side. `write-final-report` coverage stays green; the E1 subcommands extend `test-stall-recovery-report.sh`.
- **Source**: codebase + user
