## Goal
Implement issue #4848: [IMPLEMENTING] [BUG] /design Step 3 plan-review: reviewer-status.tsv has no producer; post-notification reviewer-status table never renders.

## Implementation Plan
## Summary

In `/design` Step 3 plan review, the SKILL.md "Compact reviewer status table" cannot render its post-notification (final) form because the artifact it reads is never produced. `skills/design/SKILL.md` reads `$DESIGN_TMPDIR/latest-reviewer-status.tsv` (primary) or `$DESIGN_TMPDIR/plan-review/round-N/reviewer-status.tsv` (fallback), but **no code writes `round-N/reviewer-status.tsv`**. Two sites only *copy* it to `latest-reviewer-status.tsv` when it already exists, so neither file is ever created. The per-reviewer status data does exist (in `collector-results.env`) but is never materialized into the expected `reviewer-status.tsv` shape. Impact is cosmetic: plan-review correctness is unaffected, but the live per-slot reviewer-status table never shows during Step 3.

## Original report

Observed live during a `/design` run (larch 51.1.9, `/design 4677`, run `B962AB70-3C3D-413F-8760-905398E1CB8A`, repo HEAD `2f0337930`). Plan review completed normally: `STEP3_REVIEW_LOOP_STATUS=complete`, 2 rounds, 18 findings applied, `DEGRADED_PANEL=0`. When the orchestrator went to render the SKILL.md "Compact reviewer status table" post-notification (the second of the twice-per-wait Step 3 prints), **both** source files were absent. `find "$DESIGN_TMPDIR" -name '*reviewer-status*'` returned nothing: neither `latest-reviewer-status.tsv` nor `plan-review/round-2/reviewer-status.tsv` existed. The orchestrator had to summarize instead of showing per-slot status icons and elapsed times. Outcome was not corrupted; the panel converged and applied findings normally.

## Reproduction scenario

1. Run `/design <issue>` with both Codex and Cursor present so Step 3 launches a full static panel.
2. Let the plan-review loop run and settle (any terminal `STEP3_REVIEW_LOOP_STATUS`, e.g. `complete` or `cap-hit`).
3. After the `<task-notification>`, follow SKILL.md's post-notification reviewer-status table: read `$DESIGN_TMPDIR/latest-reviewer-status.tsv`, else `$DESIGN_TMPDIR/plan-review/round-${FINAL_ROUND_NUM}/reviewer-status.tsv`.
4. Run `find "$DESIGN_TMPDIR" -name '*reviewer-status*'`.

Observed: zero results. Both the primary and the per-round fallback are absent on every run, not just degraded ones, because the file has no producer.

## Expected behavior

After each completed or settled Step 3 round, `$DESIGN_TMPDIR/plan-review/round-N/reviewer-status.tsv` and `$DESIGN_TMPDIR/latest-reviewer-status.tsv` exist, with one row per reviewer slot (for example slot, status, elapsed), so the SKILL.md post-notification compact reviewer-status table renders per-slot done/failed/skipped plus elapsed times.

## Observed behavior

Neither file is created on any run. The `if round_status.is_file()` guard at both copy sites is always false, so `latest-reviewer-status.tsv` is never written. The orchestrator cannot render the specified table and must fall back to a prose summary.

## Root cause analysis

The `round-N/reviewer-status.tsv` producer is missing; the feature is half-wired (consumers present, producer absent).

`git grep reviewer-status` (whole repo, excluding `larch-logs`) returns only consumers:
- `python/plan_review.py:1270-1274` copies `round-N/reviewer-status.tsv` to `latest-reviewer-status.tsv` only `if round_status.is_file()` (the `RUN_STEP3_PLAN_REVIEW_LOOP_SH` subprocess branch).
- `python/plan_review_round.py:603-607` does the same `if round_status.is_file()` copy at the tail of `run_plan_review_round`.
- `python/plan_review.py:1552` lists `reviewer-status.tsv` only in the round-dir preservation allowlist.
- `skills/design/SKILL.md:52` reads it for the post-notification table.

No site writes the file. In `python/plan_review_round.py`, the round body writes `collector-results.env` (line 454, from `agent collect-results` stdout, which carries per-reviewer `STATUS` / `REVIEWER_FILE` records), `findings-classification.tsv` (548), `round-summary.env`, the ballot, and findings files, but never `reviewer-status.tsv`. The per-reviewer status data therefore exists in `collector-results.env` (and is parseable via `collect_results.parse_collector_records`), but is never transformed into the `reviewer-status.tsv` shape the copy sites and SKILL.md expect.

This is likely a port regression. `git log -S reviewer-status --all -- '*.sh'` shows shell scripts once referenced `reviewer-status` (issues #3680, #4157, #4633); no `.sh` references it today. The producer plausibly lived in the old shell plan-review loop and was dropped during the sh-to-py migration while the copy-to-`latest` consumer was preserved.

## Evidence

- `git grep -n reviewer-status -- ':!larch-logs'` returns exactly six lines, all consumers (two copy-source path assignments, two `latest` copy-destinations, one preservation-allowlist entry, one SKILL.md read). None writes the file.
- `python/plan_review_round.py:603-607`: `round_status = design / "plan-review" / f"round-{round_num}" / "reviewer-status.tsv"`; `latest = design / "latest-reviewer-status.tsv"`; `if round_status.is_file() and not round_status.is_symlink(): shutil.copyfile(round_status, latest)`.
- `python/plan_review.py:1270-1274`: identical copy-if-exists guard in the `RUN_STEP3_PLAN_REVIEW_LOOP_SH` subprocess branch of `_run_round_body`.
- `python/plan_review_round.py:454`: `(design / "collector-results.env").write_text(collect_out ...)` where `collect_out` is `agent collect-results` stdout (per-reviewer records). This is the natural data source for a producer.
- Live run `B962AB70-3C3D-413F-8760-905398E1CB8A`: `find "$DESIGN_TMPDIR" -name '*reviewer-status*'` returned nothing; `plan-review/round-1` and `round-2` held per-reviewer `*-output.txt` artifacts and `round-summary.env` but no `reviewer-status.tsv`.
- Repo HEAD `2f0337930` (Release v51.1.9), branch `main`.

## Affected files

- `python/plan_review_round.py` — `run_plan_review_round` tail (around line 603) holds the copy; the natural producer site is right after `collector-results.env` is written (around line 454). Primary fix site for the in-process round path.
- `python/plan_review.py` — `_run_round_body` (1270-1274) copy-if-exists for the subprocess round path; `1552` preservation allowlist.
- `skills/design/SKILL.md` — line 52 documents the post-notification table cadence that depends on the missing artifact.

## Suggested fix(es)

Preferred: make the round body materialize `round-N/reviewer-status.tsv` from the collector records right after `collector-results.env` is written, with one row per reviewer slot (for example `slot<TAB>status<TAB>elapsed`). The existing copy-to-`latest` logic and the SKILL.md table then work unchanged. Cover both round paths (the in-process `plan_review_round.py` path and the `RUN_STEP3_PLAN_REVIEW_LOOP_SH` subprocess path in `plan_review.py`). Add a regression test asserting that `round-N/reviewer-status.tsv` and `latest-reviewer-status.tsv` exist after a settled round and contain one row per launched slot.

Alternative: if the live per-slot table is intentionally abandoned, remove the two dead copy sites, the preservation-allowlist entry, and the SKILL.md post-notification table cadence so SKILL.md and the code agree.

## Open questions

- Implement the producer (preferred) or retire the table feature?
- Closely related to #4838 ("Stale /design review breadcrumb"). #4838 reports that the *post-launch* (first) print of this same compact reviewer-status table is static/stale and proposes removing it, and asks to "audit /design and /implement for other stale breadcrumbs like this". This issue is that audit's result for the *post-notification* (second) print: it has no data producer, so it can never render. The two are facets of the same `SKILL.md` Step 3 table cadence with different defects (stale static content vs missing artifact producer). They should likely be resolved together: either implement the producer and make both prints meaningful, or remove the whole cadence (which resolves both). Consider folding into #4838 or tracking as a linked pair.
- Exact column schema for `reviewer-status.tsv` (slot, status, elapsed; what icon mapping / status vocabulary)?
- Should the producer fire on degraded and bypass terminals (`panel-failed`, `tally-error`, `degraded-empty-collector`, `cap-hit`) so the table renders on those Step 3 waits too, not only `complete`?
- Distinct from #4841 (dynamic plan-review prompts skip the render scaffold). That is a prompt-content/grounding defect for dynamic scout slots; this is a missing-artifact-producer defect. Same `/design` Step 3 plan-review area, different root cause; this run had no dynamic scout slots, so #4841 did not manifest. Should both be tracked under one umbrella or kept separate?

## Test plan
(no test plan section in plan-file)
