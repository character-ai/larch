### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: **correctness** `skills/cleanup/scripts/cleanup.sh:33-48,59-76` — Retention now uses paired `find -mtime +N` (age-pass) and `find -mtime -N` (fresh descendant) day buckets instead of the removed `date +%s` / `stat_mtime` second cutoff. On both BSD and GNU `find`, files whose mtime falls in the exact *n*-day bucket can match neither `+N` nor `-N`, so a stale top-level session candidate can pass the `+N` gate while a descendant whose only activity is at the retention floor fails `-N` and the tree is deleted. The old path kept anything with `newest >= NOW - N*86400`. **Suggested fix:** Add a `test-cleanup.sh` case that seeds a stale top-level mtime and a child at the retention boundary (not only `20000101` / `20990101` extremes), or combine `find` with a `stat`-based second check for the descendant probe; document the coarser semantics if intentional.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/cleanup.sh:33-48,59-76` — Retention now uses paired `find -mtime +N` (age-pass) and `find -mtime -N` (fresh descendant) day buckets instead of the removed `date +%s` / `stat_mtime` second cutoff. On both BSD and GNU `find`, files whose mtime falls in the exact *n*-day bucket can match neither `+N` nor `-N`, so a stale top-level session candidate can pass the `+N` gate while a descendant whose only activity is at the retention floor fails `-N` and the tree is deleted. The old path kept anything with `newest >= NOW - N*86400`. **Suggested fix:** Add a `test-cleanup.sh` case that seeds a stale top-level mtime and a child at the retention boundary (not only `20000101` / `20990101` extremes), or combine `find` with a `stat`-based second check for the descendant probe; document the coarser semantics if intentional.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: **correctness** `skills/cleanup/scripts/cleanup.sh:36-38` — Freshness detection depends on `find … | grep -q .` and `PIPESTATUS[0]` for `find` errors. If `grep` fails independently while `find` exits 0 with no matches, the function returns 1 (no fresh descendant) and the entry can be deleted; if `grep` fails while `find` printed a path, a fresh tree could be deleted. **Suggested fix:** Drop the `grep` pipe: use `find … -print -quit` exit status alone (`find` exits 0 when a match is found on BSD/GNU), or capture output to a variable and branch on `find`’s exit code without piping through `grep`.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/cleanup.sh:36-38` — Freshness detection depends on `find … | grep -q .` and `PIPESTATUS[0]` for `find` errors. If `grep` fails independently while `find` exits 0 with no matches, the function returns 1 (no fresh descendant) and the entry can be deleted; if `grep` fails while `find` printed a path, a fresh tree could be deleted. **Suggested fix:** Drop the `grep` pipe: use `find … -print -quit` exit status alone (`find` exits 0 when a match is found on BSD/GNU), or capture output to a variable and branch on `find`’s exit code without piping through `grep`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: **Awk harness** — Fixtures and assertions match `lib-plan-optional-trailers.awk`: upward scan, `block_len` as physical line count (including duplicate `diff_added:` → `2\n2\n-\nfalse`), last-match-wins (`octal-then-valid`, `duplicate-diff-added`), `0[89]` rejection vs `010` retention, `mechanical_churn` true/false, block boundary split (`block-boundary` rc=0 vs `boundary-orphan-only` / `blank-before-diff-lines` rc=1), and `set +e`/`set -e` on all expected `has_key` failures.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Awk harness** — Fixtures and assertions match `lib-plan-optional-trailers.awk`: upward scan, `block_len` as physical line count (including duplicate `diff_added:` → `2\n2\n-\nfalse`), last-match-wins (`octal-then-valid`, `duplicate-diff-added`), `0[89]` rejection vs `010` retention, `mechanical_churn` true/false, block boundary split (`block-boundary` rc=0 vs `boundary-orphan-only` / `blank-before-diff-lines` rc=1), and `set +e`/`set -e` on all expected `has_key` failures.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: **`trailer_nr`** — Same computation as the wrapper (`_plan_optional_trailer_nr` in `lib-plan-optional-trailers.sh`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **`trailer_nr`** — Same computation as the wrapper (`_plan_optional_trailer_nr` in `lib-plan-optional-trailers.sh`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: **Structural pins** — Only weak `snapshot` greps replaced with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` on `$APPROVAL_MD` and `$DISCUSSION_MD`; preservation greps and `$SKILL_MD` pins untouched. Anchors exist in the reference docs.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Structural pins** — Only weak `snapshot` greps replaced with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` on `$APPROVAL_MD` and `$DISCUSSION_MD`; preservation greps and `$SKILL_MD` pins untouched. Anchors exist in the reference docs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: **Wiring** — `test-trailer-helpers.sh` invokes the executable harness; SKILL.md cites both new `.md` files; no Makefile/shard churn.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Wiring** — `test-trailer-helpers.sh` invokes the executable harness; SKILL.md cites both new `.md` files; no Makefile/shard churn. Round 2/3 review fixes closed earlier gaps (blank-line boundary, octal-then-valid, `none-present` `has_key` for all three keys, `boundary-orphan-only`, extra `keys` cases). ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

