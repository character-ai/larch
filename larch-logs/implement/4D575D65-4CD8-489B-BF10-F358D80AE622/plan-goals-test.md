## Goal
Implement issue #4808: [IMPLEMENTING] [BUG] /design plan-review loop re-accepts the same findings every round.

## Implementation Plan
## Summary

The `/design` Step 3 plan-review loop does not converge: it re-raises and re-accepts the **same** findings on every round until the round cap or a chance vote flip. The plan content stabilizes after round 1 (a dedup-sweep strips the re-applied duplicate lines), but the loop keeps counting the same findings as freshly accepted, so it burns extra review rounds and inflates the accepted/suggestion counts in the run summary.

## Original report

Recent `/design` runs show identical per-round review rows. Investigation of merged run logs shows the same findings are produced and accepted every round.

- Run `04E1791D` (issue #4756): rounds 1-3 each accepted the **same 4 findings** (FINDING_1=Cursor-Arch, FINDING_2=Cursor-Innovation, FINDING_3=Codex-Innovation, FINDING_4=Cursor-Pragmatic); 5 suggestions / 4 accepted every round; round 4 was 5/0 and the loop stopped.
- Run `34B683D0` (issue #4675): all 5 rounds were 4 suggestions / 4 accepted (every finding accepted), hit `ROUND_CAP=5`, Total rendered 20/20.

The vote pattern is the tell. For run `04E1791D` (v1=Claude, v2=Codex, v3=Cursor), F1-F4:

| Round | Claude | Codex | Cursor | Result |
|---|---|---|---|---|
| 1 | YES | YES | YES | accepted |
| 2 | NO (false-positive) | YES | YES | accepted 2/3 |
| 3 | NO (false-positive) | YES | YES | accepted 2/3 |
| 4 | NO | YES | NO | neutral 1/3 (loop stops) |

Claude correctly flags F1-F4 as already-applied false-positives by round 2, but Codex + Cursor re-accept them, so the loop continues.

## Reproduction scenario

Run `/design <issue>` on an issue where external reviewers raise stable, re-flaggable findings (for example a refactor where reviewers keep asking for more specificity). Observe that successive review rounds re-raise and re-accept the same findings rather than converging. Empirically, on plugin v51.1.7 the loop runs multiple rounds with identical accepted sets.

Direct evidence is in committed run logs: `larch-logs/design/<RUN_ID>/plan-review/round-N/findings-classification.tsv` for the two runs above shows the same finding IDs, reviewer attribution, and severity across all rounds.

## Expected behavior

The loop converges. A finding that was accepted and applied in round N should not be re-raised and re-accepted in round N+1. Per-round accepted/suggestion counts should taper across rounds (the historical norm, e.g. run `058F6917`: 6/5, 4/4, 2/2, 5/4, 6/2). The loop should stop once it stops finding genuinely new actionable issues, not after a chance vote flip on a stable finding set.

## Observed behavior

The same findings recur every round and are re-accepted (2 of 3 external-leaning voters keep voting YES even when Claude votes NO/false-positive). The loop runs to the round cap or until a voter happens to flip. This wastes review rounds (cost and wall-clock) and re-applies the same findings (masked because a dedup-sweep removes the duplicate lines).

## Root cause analysis

No cross-round dedup or suppression of already-accepted-and-applied findings:

- **Panel/voter inputs carry no prior-round state.** The panel (`python/plan_review_panel.py`) is launched with only `--plan-file` plus the static scope anchor; voters get the ballot plus scope anchor. Neither receives the prior round's accepted/applied findings. `accepted-plan-findings.md` is overwritten each round; `accepted-plan-findings-all.md` cumulates for reporting only. So reviewers re-raise, and Codex/Cursor re-accept, items already applied.
- **Apply + dedup-sweep hide it.** Each round re-applies via `plan revise-waterfall`, then `gate-b-dedup --dedup` (`python/plan_review.py:613` prints "dedup-sweep: removed N duplicate line(s)") strips byte-identical duplicate lines, so the plan content stays stable while the loop keeps re-counting acceptances.
- **Continuation inspects only the current round.** `plan_review_continuation` (`python/plan_review.py:1039`) sets continue=true whenever the current round accepts a high-severity finding (`high > 0`), with no check that those findings duplicate a prior round. `ROUND_CAP=5` (`python/plan_review.py:24`) is the only backstop.

Regression onset and suspected cause are in **Evidence**. It is not certain whether the suspected commit introduced the recurrence or merely unmasked a pre-existing convergence gap by restoring finding flow; both readings point at the same change.

## Evidence

- **New as of 06-19.** Committed multi-round runs converge normally through 06-18 (47 sampled; example `058F6917`: 6/5 4/4 2/2 5/4 6/2). Zero pre-06-19 runs show the stagnation signature. Both broken runs (`04E1791D` = #4756, `34B683D0` = #4675) are dated 06-19.
- **Version boundary.** Runs execute on plugin v51.1.7 (release `0f989ef03`, 06-19).
- **Suspected regression commit.** The only loop-touching functional commit on 06-19 is `7000ef8ca` (Fixes #4790, "Plan-review panel silently drops all reviewer findings"). It rewired the collector to findings pipeline in `python/plan_review_round.py` (`_compose_findings_from_collector`, collector `KEY=VALUE` parsing, new `_classify_round_loop_status`) so reviewer findings flow into the ballot again. Before it, the consumer parsed the wrong delimiter and silently dropped every reviewer finding. Suggested confirmation: A/B run one issue with `7000ef8ca` reverted vs applied.
- **Per-round TSVs** for `04E1791D` show identical reviewer to finding-ID mapping and severity across all 4 rounds, with the vote pattern in **Original report**.
- **Cost impact**: `34B683D0` burned all 5 rounds (~$41.92); `04E1791D` ran 4 rounds (~$27.92).

## Affected files

- `python/plan_review.py` - `plan_review_continuation` (~line 1039) drives continuation on the current round's `high`/`non_nit` accepted counts; `gate_b_dedup` dedup-sweep (~line 613); `ROUND_CAP` (line 24).
- `python/plan_review_round.py` - per-round panel dispatch and finding composition (`_compose_findings_from_collector`); the file rewired by the suspected regression commit.
- `python/plan_review_panel.py` - panel and voter dispatch; what reviewers and voters are shown (currently no prior-round accepted findings).

## Suggested fix(es)

- Dedupe accepted findings across rounds (key on location + concern) and/or exclude already-applied findings from the `high`/`non_nit` counts that drive `plan_review_continuation`, so a re-raised already-applied finding does not re-trigger continuation.
- Optionally feed prior-round accepted/applied findings to the panel and voters (as "already addressed, do not re-raise / default-deny") so external voters stop re-accepting them.
- Investigate whether the new `KEY=VALUE` collector composition in `_compose_findings_from_collector` deterministically re-emits identical findings each round.
- Add a convergence regression test: a fixture where round 2 re-raises round 1's accepted findings must not re-accept them and must stop.

## Open questions

- Did `7000ef8ca` (#4790) introduce the recurrence, or unmask a latent convergence gap? (Bisect / A-B revert recommended.)
- Should convergence be enforced at the panel layer (stop re-raising), the voter layer (default-deny already-applied), or the continuation layer (ignore duplicate accepts)? A combination is likely safest.

## Test plan
(no test plan section in plan-file)
