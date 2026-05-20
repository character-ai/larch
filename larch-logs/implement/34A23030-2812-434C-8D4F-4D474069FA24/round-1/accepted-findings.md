### FINDING_1: **architecture** `skills/implement/SKILL.md:64` and `skills/implement/SKILL.md:1727` — NEVER #16’s “How to apply” and the Step 8+ blockquote both instruct recovery as `ship-pr.sh --resume-phase $PHASE` after reading `PHASE` from `ship-pr-state.sh`, but [`scripts/ship-pr.sh`](scripts/ship-pr.sh) only accepts a fixed set of `--resume-phase` values (`force-push-gate`, `bump`, `pr-create`, `ci-initial`, `ci-merge`, `evaluate-failure`, `postmerge` at lines 1673–1681), while the state file’s `PHASE` can be values such as `checks` or `pr-prep` (see the main loop at lines 1685–1704), for which that flag form is invalid or misleading. **Suggested fix:** Tighten recovery wording to match the script: e.g. resume with the same foreground `ship-pr.sh` invocation **without** `--resume-phase` when continuing the persisted `PHASE` main loop, and reserve `--resume-phase <token>` for the tokens and situations already spelled out in the Step 8+ exit-code matrix (e.g. `skills/implement/SKILL.md` around lines 1755–1759), or explicitly map which `PHASE` values require which resume flag.
- **Reviewer**: dyn-prose-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:64` and `skills/implement/SKILL.md:1727` — NEVER #16’s “How to apply” and the Step 8+ blockquote both instruct recovery as `ship-pr.sh --resume-phase $PHASE` after reading `PHASE` from `ship-pr-state.sh`, but [`scripts/ship-pr.sh`](scripts/ship-pr.sh) only accepts a fixed set of `--resume-phase` values (`force-push-gate`, `bump`, `pr-create`, `ci-initial`, `ci-merge`, `evaluate-failure`, `postmerge` at lines 1673–1681), while the state file’s `PHASE` can be values such as `checks` or `pr-prep` (see the main loop at lines 1685–1704), for which that flag form is invalid or misleading. **Suggested fix:** Tighten recovery wording to match the script: e.g. resume with the same foreground `ship-pr.sh` invocation **without** `--resume-phase` when continuing the persisted `PHASE` main loop, and reserve `--resume-phase <token>` for the tokens and situations already spelled out in the Step 8+ exit-code matrix (e.g. `skills/implement/SKILL.md` around lines 1755–1759), or explicitly map which `PHASE` values require which resume flag.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/implement/SKILL.md:1727
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] The pre-Invoke blockquote repeats PHASE to --resume-phase $PHASE. Same as NEVER #16: operator following the prominent warning before Invoke can hit unknown --resume-phase for common PHASE values. Match ship-pr.sh entry contract or prefer resuming without --resume-phase when PHASE is not in the allowlist.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/implement/SKILL.md:1727
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 8+ warning repeats PHASE-to---resume-phase mapping. Same invalid --resume-phase values as NEVER #16 when PHASE is not in the allowlist. Mirror the corrected recovery wording from NEVER #16.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/implement/SKILL.md:64
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] NEVER #16 says re-invoke with --resume-phase $PHASE after reading PHASE from ship-pr-state.sh. PHASE values such as checks or pr-prep are not accepted by ship-pr.sh --resume-phase; the script dies with unknown --resume-phase before resuming the loop, so post-timeout recovery instructions can fail. Describe recovery as foreground re-invocation with the same Step 8+ args and no --resume-phase when appropriate, or only pass --resume-phase values that ship-pr.sh allows (or RESUME_PHASE per Exit 5).
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/implement/SKILL.md:64
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] NEVER #16 maps state PHASE directly to --resume-phase. Operators following the doc may run e.g. --resume-phase checks or pr-prep; ship-pr.sh rejects unknown --resume-phase and exits via die_usage instead of resuming. Document foreground re-run from ship-pr-state.sh PHASE via the normal invocation without --resume-phase unless the value is in the ship-pr.sh resume allowlist; align wording with scripts/ship-pr.sh.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/implement/SKILL.md:64,1727
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] NEVER #16 and the Step 8+ warning equate state key PHASE with the CLI --resume-phase argument, but ship-pr.sh only accepts a fixed token set for --resume-phase. Following the doc after timeout when ship-pr-state.sh has PHASE=checks (or pr-prep, done, etc.) produces ship-pr.sh … --resume-phase checks and immediate die_usage unknown --resume-phase instead of resuming the state machine. Document generic recovery as a foreground re-run of the Invoke block without --resume-phase when state is intact; use --resume-phase only with whitelisted tokens or the RESUME_PHASE-driven paths already in the exit-code table.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/implement/SKILL.md:64,1727
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] NEVER #16 and the Step 8+ blockquote equate persisted PHASE with a valid --resume-phase argument. After timeout or turn end while PHASE is checks or pr-prep, ship-pr.sh rejects --resume-phase checks|pr-prep (die_usage), so the documented recovery breaks instead of resuming the state machine. Document foreground re-invoke using the Invoke block without --resume-phase when PHASE is not in ship-pr.sh's --resume-phase whitelist; use --resume-phase only for allowed tokens and existing RESUME_PHASE-driven paths.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/implement/SKILL.md:64,1727-1728
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] NEVER #16 and the Step 8+ warning equate state PHASE with the --resume-phase CLI value for generic timeout/turn-end recovery. After an unexpected turn end while ship-pr-state.sh has PHASE=checks or pr-prep, a literal --resume-phase $PHASE re-run can fail ship-pr.sh with unknown --resume-phase instead of resuming. Restrict --resume-phase to supported tokens or document re-invoking without --resume-phase when PHASE is not a valid resume token; align with ship-pr.sh case list and existing exit-code guidance.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/implement/SKILL.md:64
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] NEVER #16 claims --auto stalls with no recovery path beside the #2454 user-intervention story. Operators may dismiss user continuation as a recovery path and mis-prioritize tooling fixes. Rephrase to no automatic recovery until a new user-driven turn.
- **Suggested revision**: Address the concern above.


### FINDING_2: **architecture** `skills/implement/SKILL.md:64` — In the **Why** clause, “In `--auto` mode this stalls indefinitely **with no recovery path**” sits awkwardly next to issue #2454’s “requiring user intervention to recover” and the **How to apply** `--resume-phase` recovery text; together they read as if there were no way forward in auto mode even though a subsequent turn can still mechanically resume once the operator or host un-stalls the session. **Suggested fix:** Qualify “no recovery path” as **no automatic / unattended** recovery (or similar) so it does not contradict the recovery paragraph and the cited incident.
- **Reviewer**: dyn-prose-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:64` — In the **Why** clause, “In `--auto` mode this stalls indefinitely **with no recovery path**” sits awkwardly next to issue #2454’s “requiring user intervention to recover” and the **How to apply** `--resume-phase` recovery text; together they read as if there were no way forward in auto mode even though a subsequent turn can still mechanically resume once the operator or host un-stalls the session. **Suggested fix:** Qualify “no recovery path” as **no automatic / unattended** recovery (or similar) so it does not contradict the recovery paragraph and the cited incident.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/implement/SKILL.md:64,1727
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Doc asserts the Bash tool timeout is 10 minutes and always covers CI wait. If the effective Bash timeout is lower or CI exceeds 10 minutes, ship-pr.sh is killed mid-run despite the stated guarantee. Soften or qualify the timeout claim or reference the actual configured limit.
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: skills/implement/SKILL.md:64,1727
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Text asserts the default 10-minute Bash timeout covers CI wait. Long CI or merge queues can exceed 10 minutes; paired with wrong --resume-phase advice this overpromises resilience. Soften the timeout claim and tie recovery to correct resume semantics.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/implement/SKILL.md:64,1727
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Text asserts the 10-minute Bash timeout covers CI wait. Long CI runs can exceed 10 minutes; readers may treat this as a guarantee and be surprised by tool timeout despite the doc. Soften language to reflect variable CI duration or mention configuring longer waits where supported.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: skills/implement/SKILL.md:64-1727
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Doc claims 10-minute Bash timeout covers CI wait. Long CI or repeated loops can exceed the tool cap; operators hit timeout despite following foreground guidance. Soften absolute wording or note host-specific timeout/extension.
- **Suggested revision**: Address the concern above.


### FINDING_3: **architecture** `skills/implement/SKILL.md:64` — NEVER #16 claims the Bash tool’s **10-minute** timeout is enough for `ship-pr.sh` (CI+merge state machine), which conflicts with existing long-blocking guidance for synchronous `ci-wait.sh` in the same orchestration surface (`timeout: 1860000` / 31 minutes in [`skills/implement/references/rebase-rebump-subprocedure.md`](skills/implement/references/rebase-rebump-subprocedure.md) around line 173) and understates realistic wall-clock for multi-step CI loops inside `ship-pr.sh`. **Suggested fix:** Drop the “10 minutes covers the wait” assurance or replace it with language that matches the established long-timeout policy (or explicitly requires an orchestrator-configured Bash timeout large enough for the full delegated loop, with a pointer to the same reference as `ci-wait.sh`).
- **Reviewer**: dyn-prose-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:64` — NEVER #16 claims the Bash tool’s **10-minute** timeout is enough for `ship-pr.sh` (CI+merge state machine), which conflicts with existing long-blocking guidance for synchronous `ci-wait.sh` in the same orchestration surface (`timeout: 1860000` / 31 minutes in [`skills/implement/references/rebase-rebump-subprocedure.md`](skills/implement/references/rebase-rebump-subprocedure.md) around line 173) and understates realistic wall-clock for multi-step CI loops inside `ship-pr.sh`. **Suggested fix:** Drop the “10 minutes covers the wait” assurance or replace it with language that matches the established long-timeout policy (or explicitly requires an orchestrator-configured Bash timeout large enough for the full delegated loop, with a pointer to the same reference as `ci-wait.sh`).
- **Suggested revision**: Address the concern above.


