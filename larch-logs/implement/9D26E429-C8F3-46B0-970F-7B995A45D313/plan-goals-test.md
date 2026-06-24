## Goal
Implement issue #5260: [IMPLEMENTING] [BUG] OOS issues filed with empty Description: /issue parser drops review-path body.

## Implementation Plan
## Summary

Review-surfaced (Step 5) accepted out-of-scope (OOS) observations are filed as public GitHub issues with an **empty body**: the title carries the summary, but the rendered `## Description` is blank. Root cause is a format mismatch at the `/issue` OOS input parser, plus a missing malformed-item guard in the OOS filer. Reproduced against `main` at HEAD `547bbd471`. Live example: issue #5256.

## Original report

Investigate whether the root cause for OOS issue #5256 having been created with an effectively empty body is already fixed in `main`. It is **not** fixed (reproduced against HEAD). Issue #5256 was filed with the OOS template intact but an empty `## Description`, `Surfaced by: N/A`, `Vote tally: N/A`, `Phase: implement` (all defaults). The originating accepted block had a full Concern and suggested fix; all of it was dropped before filing.

## Reproduction scenario

Against a clean `main` (HEAD `547bbd471`):

```
python3 python/cli.py issue parse-input \
  --input-file larch-logs/implement/89F8C10B-95B7-472F-8409-737D750A889A/round-1/oos-accepted-review.md \
  --output-dir /tmp/out
```

Observed stdout:

```
ITEM_1_TITLE=[OUT_OF_SCOPE] Stale plan-review.md severity rubric cross-reference
ITEM_1_MALFORMED=true
ITEMS_TOTAL=1
```

No `ITEM_1_BODY_FILE` is emitted and `/tmp/out` stays empty. The downstream filer (`python3 python/cli.py oos file`) then creates the issue anyway with that empty body. The committed source block uses the FINDING-block field labels `- **Concern**:` and `- **Reviewer(s)**:`; the filed `oos-issues.ndjson` records stable ID `oos-accepted-review:OOS_1` and Filed URL `https://github.com/character-ai/larch/issues/5256`.

## Expected behavior

A review-surfaced accepted OOS block, whatever its internal field labels, should be filed with a non-empty `## Description` containing the Concern text and suggested fix. If a block genuinely cannot be parsed into a body, the filer should **not** create a public issue with an empty Description; it should skip the item and surface a loud breadcrumb.

## Observed behavior

The entire body of the accepted OOS block is silently discarded during parsing, the item is flagged `MALFORMED=true` with no body file, and the OOS filer ignores that flag and files a public issue whose `## Description` is empty.

## Root cause analysis

Two distinct defects compound. This is a **structural** mismatch, not a one-off.

**Defect 1 — body loss in the OOS input parser.** `parse_issue_input` in `python/issue_create.py` recognizes only the documented OOS contract field labels: `- **Description**:` (`DESC_RE`, line 28) and `- **Reviewer**:` (`REVIEWER_RE`, line 29). Step-5 review-surfaced accepted OOS are written to `oos-accepted-review.md` by `python/review_tally.py` (`_normalize_oos_header_text(artifact_text)`, ~lines 813-820), which preserves the **FINDING-block format**: `- **Reviewer(s)**:`, `- **Severity**:`, `- **Concern**:`, `- **Suggested revisions (informational for voters; coder decides)**:`. The parser sets `in_body = False` immediately after the `### OOS_N:` heading (line 162). Because none of the FINDING-block labels match the field regexes (`Concern` ≠ `Description`; `Reviewer(s)` ≠ `Reviewer`), each line falls through to the `elif state.in_body:` branch (False) and is silently dropped. `current_body` stays empty, the item is emitted with `malformed = not self.current_body` (line 97), and `parse_input_main` writes no body file (line 244, `if item.body:` is False).

**Defect 2 — the OOS filer files the malformed item anyway.** `python/oos_filer.py` `_file` calls `issue parse-input` (line 670), then loops over `create_order` calling `issue create-one` (line 695) with the title and the missing/empty body from `_body_files_for_item` (line 603). It never checks `ITEM_N_MALFORMED`. `_wrap_oos_body("")` (line 479) renders the OOS template with an empty `## Description`, and a public empty issue is created.

The main-agent dual-write path and the external-implementer manifest path are unaffected: `python/file_oos.py` `materialize_manifest_oos` emits the contract labels `- **Description**:` and `- **Reviewer**:`, which the parser accepts. Only the review-pipeline OOS path is broken. The Codex combine pass is best-effort and Codex-gated and does not normalize field labels, so it does not prevent the bug.

## Evidence

- Issue #5256 body is the `_wrap_oos_body` template with an empty Description and all-default metadata (`Surfaced by: N/A`, `Vote tally: N/A`, `Phase: implement`), confirming reviewer/vote/phase fields were also dropped.
- Committed source block `larch-logs/implement/89F8C10B-95B7-472F-8409-737D750A889A/round-1/oos-accepted-review.md` uses `- **Concern**:` and `- **Reviewer(s)**:` (FINDING-block format).
- Committed `larch-logs/implement/89F8C10B-95B7-472F-8409-737D750A889A/oos-issues.ndjson` records the Filed URL for #5256 with stable ID `oos-accepted-review:OOS_1`, proving the filing went through the `python/oos_filer.py` (`oos file`) path.
- Empirical `parse-input` run (above) emits `ITEM_1_MALFORMED=true` and no body file.
- Documented OOS contract format is `skills/implement/references/execution-issues-tracking.md` lines 80-86 (`- **Description**:` / `- **Reviewer**:`).
- Parser regexes: `python/issue_create.py:28-31`. Post-heading `in_body = False`: `python/issue_create.py:162`. Malformed emit: `python/issue_create.py:97`, `python/issue_create.py:244`.
- Filer create loop with no malformed guard: `python/oos_filer.py:670,685,695,603,479`.
- Producer: `python/review_tally.py:813-820`, `_normalize_oos_header_text` rewrites only the heading, preserving FINDING-block fields.
- No existing **open** issue covers this (all 35 open checked). Two **closed** issues are the same OOS-empty-body symptom family but a **different root cause**, and neither touches `parse_issue_input`:
  - #5097 (closed 2026-06-22, PR #5134) fixed body loss in the **combine / cap-rollup** path (`cli.py oos issue-cap` aggregation).
  - #5132 (closed 2026-06-23, PR #5164) fixed source-body preservation under **GitHub body-size splitting** (`_split_to_github_limit`). Its own issue body is itself empty, demonstrating the same symptom.
- #5256 was filed **2026-06-24**, after both fixes merged, and is still empty. This is direct proof the parser/`parse_issue_input` root cause described here survives both prior fixes; it is a distinct, third OOS-body-loss mechanism.

## Affected files

- `python/issue_create.py` — the OOS input parser (`parse_issue_input`) that drops FINDING-format body content. Primary fix site for Defect 1 (option a).
- `python/oos_filer.py` — the OOS filer that ignores `ITEM_N_MALFORMED` and files empty bodies. Fix site for Defect 2 (harden).
- `python/review_tally.py` — the producer that writes FINDING-format blocks into `oos-accepted-review.md`. Alternative fix site for Defect 1 (option b: normalize to the contract).
- `python/test_issue_create.py`, `python/test_oos_filer.py` — regression coverage to add.

## Suggested fix(es)

**Primary — close the format gap (pick one):**

- (a) Make the OOS parser capture the full block body when no `- **Description**:` line is present: after a `### OOS_N:` heading, accumulate non-metadata lines into the body, and treat `- **Concern**:` as a Description-equivalent and `- **Reviewer(s)**:` as a Reviewer-equivalent. This is the single chokepoint all OOS filing flows pass through. When changing the `in_body` default, preserve the issue #129 / #131 / #132 subheading-absorption and continuation behaviors (`test_parse_input_issue_129_*`, `_131_*`, `_132_*`).
- (b) Normalize review-pipeline accepted-OOS blocks into the documented `- **Description**:` / `- **Reviewer**:` contract before they reach `/issue` (map Concern + Suggested revisions into Description), at the `review_tally.py` writer or in the OOS combine/materialize step.

**Harden — never publish empty issues:** `python/oos_filer.py` should respect `ITEM_N_MALFORMED=true` / empty body by skipping that item and appending a `Tool Failures` breadcrumb (fail loud), instead of creating an empty public issue. This is a defense-in-depth net independent of the chosen primary fix.

**Regression test:** a FINDING-format `oos-accepted-review.md` block must round-trip through `parse-input` to a non-empty body and through `_wrap_oos_body` to a non-empty `## Description`.

## Open questions

- Preferred fix locus: parser tolerance (option a) vs. producer normalization (option b). Option (a) fixes all current and future producers at one point; option (b) keeps the parser contract strict and conformant. Recommendation: option (a) as primary plus the Defect 2 harden, but `/design` should decide.
- Should the filed Description include the suggested-fix sub-bullets, or only the Concern line? Capturing the full block (option a) preserves them; a Concern-only mapping would drop them.
- Should already-filed empty issues such as #5256 be backfilled or closed, or only future filings fixed?

## Test plan
(no test plan section in plan-file)
