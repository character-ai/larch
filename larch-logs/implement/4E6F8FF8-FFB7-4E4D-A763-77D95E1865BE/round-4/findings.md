### FINDING_1: code-quality: skills/design/scripts/lib-plan-optional-trailers.md:37-39
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Octal guard docs omit block_len exclusion for 08/09 lines. A maintainer “fixing” octal handling might only clear keys/values while leaving block_len inflated, breaking plan-size subtraction without failing keys/has_key tests. Document that 0[89] strict lines do not increment block_len; point to octal-rejected / octal-then-valid harness cases.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/test-trailer-awk.sh:180-189
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] values mode never asserts block-boundary (diff_added=5). A values-only regression on last-match-wins inside the metadata block could slip past while parse/keys still pass. Add assert_values for block-boundary with diff_added=5.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] PR mixes #3204 with #3212, #3209, version bumps, and larch-logs. Harder review/bisect; unrelated failures can block the trailer harness PR. Prefer stacked PRs or a #3204-only branch for merge if policy allows.
- **Suggested revision**: Address the concern above.

### FINDING_4: **Awk harness** — Fixtures and assertions match `lib-plan-optional-trailers.awk`: upward scan, `block_len` as physical line count (including duplicate `diff_added:` → `2\n2\n-\nfalse`), last-match-wins (`octal-then-valid`, `duplicate-diff-added`), `0[89]` rejection vs `010` retention, `mechanical_churn` true/false, block boundary split (`block-boundary` rc=0 vs `boundary-orphan-only` / `blank-before-diff-lines` rc=1), and `set +e`/`set -e` on all expected `has_key` failures.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Awk harness** — Fixtures and assertions match `lib-plan-optional-trailers.awk`: upward scan, `block_len` as physical line count (including duplicate `diff_added:` → `2\n2\n-\nfalse`), last-match-wins (`octal-then-valid`, `duplicate-diff-added`), `0[89]` rejection vs `010` retention, `mechanical_churn` true/false, block boundary split (`block-boundary` rc=0 vs `boundary-orphan-only` / `blank-before-diff-lines` rc=1), and `set +e`/`set -e` on all expected `has_key` failures.
- **Suggested revision**: Address the concern above.

### FINDING_5: **`trailer_nr`** — Same computation as the wrapper (`_plan_optional_trailer_nr` in `lib-plan-optional-trailers.sh`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **`trailer_nr`** — Same computation as the wrapper (`_plan_optional_trailer_nr` in `lib-plan-optional-trailers.sh`).
- **Suggested revision**: Address the concern above.

### FINDING_6: **Structural pins** — Only weak `snapshot` greps replaced with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` on `$APPROVAL_MD` and `$DISCUSSION_MD`; preservation greps and `$SKILL_MD` pins untouched. Anchors exist in the reference docs.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Structural pins** — Only weak `snapshot` greps replaced with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` on `$APPROVAL_MD` and `$DISCUSSION_MD`; preservation greps and `$SKILL_MD` pins untouched. Anchors exist in the reference docs.
- **Suggested revision**: Address the concern above.

### FINDING_7: **Wiring** — `test-trailer-helpers.sh` invokes the executable harness; SKILL.md cites both new `.md` files; no Makefile/shard churn.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Wiring** — `test-trailer-helpers.sh` invokes the executable harness; SKILL.md cites both new `.md` files; no Makefile/shard churn. Round 2/3 review fixes closed earlier gaps (blank-line boundary, octal-then-valid, `none-present` `has_key` for all three keys, `boundary-orphan-only`, extra `keys` cases). ---
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/test-trailer-awk.sh` — No fixture where the last non-empty line is `diff_lines:` but trailing blank lines follow (only `trailer_nr` contract in docs). **Scenario:** If `trailer_nr` were computed from physical EOF instead of last non-empty line, the harness would not catch a regression. **Suggested fix:** Add a fixture with `diff_lines:` then blank lines and assert parse/keys unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **correctness** `skills/design/scripts/test-trailer-awk.sh` — `has_key` does not probe `diff_deleted: 08` alone (only `diff_added: 08` and `diff_deleted: 09` in `octal-rejected`). **Scenario:** A broken `substr`/offset for `diff_deleted` could slip through while `diff_added` octal tests pass. **Suggested fix:** Add `diff_deleted: 08` on its own line in a small fixture.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **correctness** `skills/cleanup/scripts/cleanup.sh` — Top-level `/tmp` and cache scans use `find … ! -type l`, so symlink entries matching larch patterns are never candidates for removal (unlike the prior `[[ -e || -L ]]` loop). **Scenario:** A stale symlink like `larch4-review.diff` → old target persists indefinitely. **Suggested fix:** If symlink cleanup is desired, add an explicit `-type l` pass with safe age rules. *(#3212 / #3209 / `larch-logs` changes are separate from #3204; not expanded here per scope.)*
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `HEAD` (multi-commit branch) — The PR bundles #3204 with #3212 (`cleanup`), #3209 (`ship-pr`), and `review-and-fix` changes, each with expanded harnesses in the same diff. A red `make test-harnesses-N` cell may come from an unrelated commit; bisect by commit (`d33cdfb70` vs later) before treating it as a #3204 regression. **Suggested fix:** Split or label PR/commits for review; run `make test-trailer-helpers` and `make test-design-structure` on the #3204 commit in isolation when debugging.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `skills/design/scripts/test-trailer-{dedup,has-any,validate}.sh` — The four pre-existing thin adapters still have no `.md` siblings; the plan explicitly keeps that state (S030 flags orphaned `.md`, not `.sh` without docs). **Suggested fix:** None for #3204; optional follow-up only if script-md-siblings policy tightens beyond S030 citation rules.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/review-and-fix/scripts/review-and-fix.sh` (pre-branch behavior) — Prior round-mode commits used `git add -A`, which could stage **untracked** files left by an external coder (including accidental secret files). This branch’s manifest staging excludes untracked paths and fails closed on untracked-only dirt; that is a hardening fix, not a regression introduced here.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/cleanup/scripts/cleanup.sh` (pre-existing TOCTOU class) — Age-pass still lists candidates with `find` then deletes with `rm -rf` without re-validating the entry node type; a local race replacing a directory with a symlink after listing is the same class of trust-boundary caveat called out in `SECURITY.md` for operator-owned session roots, not newly introduced by the mtime refactor.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/review-and-fix.sh:954-987
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Selective round staging omits untracked coder outputs from manifest and post-commit checks. Coder creates only new untracked fix files; round commit succeeds with CODER_STATUS=applied while fixes never enter the branch. Include untracked paths in collect_round_stage_paths/staging or fail closed when ?? entries remain after commit.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2856-2869
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-rebase larch-logs fixup ignores untracked dirtiness. Untracked files under larch-logs/ leave the tree dirty through drop-bump Guard 1 despite the #3209 fixup block. Extend dirty detection and git add to untracked larch-logs/ or document the tracked-only scope.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] correctness: skills/design/scripts/test-trailer-awk.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness does not cover trailing blank lines after diff_lines:. Malformed plan tails are untested; unlikely in production plans. Add an optional fixture asserting parse/keys behavior when blank lines follow diff_lines:.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/test-trailer-awk.sh:220` — Plan text asks for an explicit trailing `exit 0` after `echo "PASS: test-trailer-awk.sh"`; the harness relies on implicit success exit. **Suggested fix:** Add `exit 0` for literal plan alignment (behavior unchanged).
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **correctness** `skills/design/scripts/lib-plan-optional-trailers.md:37-39` — Octal guard documents rejection but not that invalid `08`/`09` lines are skipped for `block_len` without stopping the upward scan (`octal-then-valid` in the harness). **Suggested fix:** Add one sentence under “Octal guard” describing skip-vs-break behavior. --- **Summary:** Implementation matches the #3204 plan: awk unit harness with normative edge coverage, cited docs, tightened `(3175)` pins, helpers wiring, and unchanged unit-under-test. Remaining gaps are documentation/minor exit-style nits, not functional plan misses.
- **Suggested revision**: Address the concern above.

### FINDING_20: **correctness** `skills/review-and-fix/scripts/review-and-fix.sh:328-336` — `collect_round_stage_paths` unions `git diff --name-only`, `git diff --name-only --cached`, and `git status --porcelain … | awk '{print $2}'`. For paths with spaces, Git emits quoted porcelain (e.g. ` M "path with spaces.txt"`), but field splitting yields a bogus token (`"path`), which is deduped separately from the correct path from `git diff --name-only`. `stage_round_dirty_paths` then runs `git add --` on every manifest line; the malformed token makes `git add` fail with exit 128 even when the real path was already listed, so round-mode commits can fail closed (`CODER_STATUS=failed`) on otherwise valid coder edits. **Suggested fix:** Drop porcelain from manifest collection and build the manifest only from `git diff --name-only` / `--cached` (same pattern as `scripts/lint-fix-loop.sh:110-114`), or parse porcelain with a path-safe extractor (e.g. strip the two status columns and leading space, or use `git status --porcelain=v1 -z` and NUL-delimited reads).
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/review-and-fix.sh:328-336` — `collect_round_stage_paths` unions `git diff --name-only`, `git diff --name-only --cached`, and `git status --porcelain … | awk '{print $2}'`. For paths with spaces, Git emits quoted porcelain (e.g. ` M "path with spaces.txt"`), but field splitting yields a bogus token (`"path`), which is deduped separately from the correct path from `git diff --name-only`. `stage_round_dirty_paths` then runs `git add --` on every manifest line; the malformed token makes `git add` fail with exit 128 even when the real path was already listed, so round-mode commits can fail closed (`CODER_STATUS=failed`) on otherwise valid coder edits. **Suggested fix:** Drop porcelain from manifest collection and build the manifest only from `git diff --name-only` / `--cached` (same pattern as `scripts/lint-fix-loop.sh:110-114`), or parse porcelain with a path-safe extractor (e.g. strip the two status columns and leading space, or use `git status --porcelain=v1 -z` and NUL-delimited reads).
- **Suggested revision**: Address the concern above.

### FINDING_21: **correctness** `skills/review-and-fix/scripts/review-and-fix.sh:328-336` — On renames, porcelain looks like `R  old -> new` while `git diff --name-only` lists the new path (`new`). `awk '{print $2}'` adds the **old** path to `coder-stage-paths.txt`; `git add -- old` then fails (`pathspec did not match any files`) after `git add -- new` would succeed, so rename-only coder deltas break round staging. **Suggested fix:** Rely on `git diff --name-only` (+ `--cached`) for the manifest and omit porcelain path tokens, or special-case rename lines to stage the destination path (and/or use `git diff --name-status` / `-z` parsing).
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/review-and-fix.sh:328-336` — On renames, porcelain looks like `R  old -> new` while `git diff --name-only` lists the new path (`new`). `awk '{print $2}'` adds the **old** path to `coder-stage-paths.txt`; `git add -- old` then fails (`pathspec did not match any files`) after `git add -- new` would succeed, so rename-only coder deltas break round staging. **Suggested fix:** Rely on `git diff --name-only` (+ `--cached`) for the manifest and omit porcelain path tokens, or special-case rename lines to stage the destination path (and/or use `git diff --name-status` / `-z` parsing).
- **Suggested revision**: Address the concern above.

### FINDING_22: **correctness** `skills/review-and-fix/scripts/review-and-fix.sh:328-336` — The manifest is the union of all currently unstaged and **all** cached paths, not only files touched by the coder in this round. Any path staged before the Step 5 coder dispatch (unrelated WIP) is included via `git diff --name-only --cached` and gets committed inside `Address code review feedback (round N)`, which contradicts the documented “post-dispatch tracked delta” contract in `skills/review-and-fix/scripts/review-and-fix.md:54`. **Suggested fix:** Snapshot pre-dispatch `HEAD` and cached index paths (or diff against `pre-review-head.txt`) and intersect the post-dispatch dirty set with that baseline delta, instead of blind union with the full index diff.
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/review-and-fix.sh:328-336` — The manifest is the union of all currently unstaged and **all** cached paths, not only files touched by the coder in this round. Any path staged before the Step 5 coder dispatch (unrelated WIP) is included via `git diff --name-only --cached` and gets committed inside `Address code review feedback (round N)`, which contradicts the documented “post-dispatch tracked delta” contract in `skills/review-and-fix/scripts/review-and-fix.md:54`. **Suggested fix:** Snapshot pre-dispatch `HEAD` and cached index paths (or diff against `pre-review-head.txt`) and intersect the post-dispatch dirty set with that baseline delta, instead of blind union with the full index diff.
- **Suggested revision**: Address the concern above.

### FINDING_23: **correctness** `skills/review-and-fix/scripts/review-and-fix.sh:351-358` — `round_tracked_dirty_outside_manifest` also derives paths with `awk '{print $2}'` only. For quoted paths and renames it compares the wrong tokens against the manifest, so the outside-manifest guard can false-negative (allow commit while real dirty paths remain unstaged) or false-positive depending on porcelain shape; the new `test-review-and-fix.sh` manifest-outside case passes only because it dirties a simple unquoted path. **Suggested fix:** Use the same path extraction as the manifest (ideally `git diff --name-only` for remaining dirty tracked files after staging, or shared porcelain `-z` parsing) so guard tokens match manifest entries.
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/review-and-fix.sh:351-358` — `round_tracked_dirty_outside_manifest` also derives paths with `awk '{print $2}'` only. For quoted paths and renames it compares the wrong tokens against the manifest, so the outside-manifest guard can false-negative (allow commit while real dirty paths remain unstaged) or false-positive depending on porcelain shape; the new `test-review-and-fix.sh` manifest-outside case passes only because it dirties a simple unquoted path. **Suggested fix:** Use the same path extraction as the manifest (ideally `git diff --name-only` for remaining dirty tracked files after staging, or shared porcelain `-z` parsing) so guard tokens match manifest entries.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] **#3204 (`test-trailer-awk.sh`, `test-design-structure.sh`, docs):** No correctness defects found relative to `lib-plan-optional-trailers.awk`; fixtures match upward-scan, last-match-wins, `block_len`, octal `0[89]` rejection, and `set +e`/`set -e` `has_key` probes. `.awk`/`.sh` are byte-stable in the diff.
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **#3204 (`test-trailer-awk.sh`, `test-design-structure.sh`, docs):** No correctness defects found relative to `lib-plan-optional-trailers.awk`; fixtures match upward-scan, last-match-wins, `block_len`, octal `0[89]` rejection, and `set +e`/`set -e` `has_key` probes. `.awk`/`.sh` are byte-stable in the diff.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] **`skills/review-and-fix/scripts/test-review-and-fix.sh`:** New hook-residue and untracked-only cases do not exercise rename porcelain, quoted paths with spaces, or pre-existing staged paths outside the coder delta; those gaps align with the parsing issues above.
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **`skills/review-and-fix/scripts/test-review-and-fix.sh`:** New hook-residue and untracked-only cases do not exercise rename porcelain, quoted paths with spaces, or pre-existing staged paths outside the coder delta; those gaps align with the parsing issues above.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] **Other branch commits** (`ship-pr.sh`, `cleanup.sh`, version bump, run logs): Not reviewed for staging-path parsing; scout scope was `review-and-fix` manifest collection.
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **Other branch commits** (`ship-pr.sh`, `cleanup.sh`, version bump, run logs): Not reviewed for staging-path parsing; scout scope was `review-and-fix` manifest collection.
- **Suggested revision**: Address the concern above.

### FINDING_27: **correctness** `skills/cleanup/scripts/cleanup.sh:33-48,59-76` — Retention now uses paired `find -mtime +N` (age-pass) and `find -mtime -N` (fresh descendant) day buckets instead of the removed `date +%s` / `stat_mtime` second cutoff. On both BSD and GNU `find`, files whose mtime falls in the exact *n*-day bucket can match neither `+N` nor `-N`, so a stale top-level session candidate can pass the `+N` gate while a descendant whose only activity is at the retention floor fails `-N` and the tree is deleted. The old path kept anything with `newest >= NOW - N*86400`. **Suggested fix:** Add a `test-cleanup.sh` case that seeds a stale top-level mtime and a child at the retention boundary (not only `20000101` / `20990101` extremes), or combine `find` with a `stat`-based second check for the descendant probe; document the coarser semantics if intentional.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/cleanup.sh:33-48,59-76` — Retention now uses paired `find -mtime +N` (age-pass) and `find -mtime -N` (fresh descendant) day buckets instead of the removed `date +%s` / `stat_mtime` second cutoff. On both BSD and GNU `find`, files whose mtime falls in the exact *n*-day bucket can match neither `+N` nor `-N`, so a stale top-level session candidate can pass the `+N` gate while a descendant whose only activity is at the retention floor fails `-N` and the tree is deleted. The old path kept anything with `newest >= NOW - N*86400`. **Suggested fix:** Add a `test-cleanup.sh` case that seeds a stale top-level mtime and a child at the retention boundary (not only `20000101` / `20990101` extremes), or combine `find` with a `stat`-based second check for the descendant probe; document the coarser semantics if intentional.
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `skills/cleanup/scripts/cleanup.sh:36` — `entry_has_fresh_descendant` runs an unbounded `find "$entry" -mindepth 1 ! -type l -mtime "-${RETENTION_DAYS}"` with no `-maxdepth`. When no descendant matches, `find` must walk the full session tree before returning; on large `larch-logs/implement/…` trees this reintroduces the hang/latency class #3212 addressed at the top level, while `test-cleanup.sh` only stress-tests flat `/tmp` breadth (`large-tmp-scales`), not deep cache interiors. **Suggested fix:** Use a documented depth cap for the freshness probe (e.g. implement run-log depth + margin) or another bounded activity signal; add a harness with nested depth representative of production session layout and a time budget.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/cleanup.sh:36` — `entry_has_fresh_descendant` runs an unbounded `find "$entry" -mindepth 1 ! -type l -mtime "-${RETENTION_DAYS}"` with no `-maxdepth`. When no descendant matches, `find` must walk the full session tree before returning; on large `larch-logs/implement/…` trees this reintroduces the hang/latency class #3212 addressed at the top level, while `test-cleanup.sh` only stress-tests flat `/tmp` breadth (`large-tmp-scales`), not deep cache interiors. **Suggested fix:** Use a documented depth cap for the freshness probe (e.g. implement run-log depth + margin) or another bounded activity signal; add a harness with nested depth representative of production session layout and a time budget.
- **Suggested revision**: Address the concern above.

### FINDING_29: **correctness** `skills/cleanup/scripts/cleanup.sh:36-38` — Freshness detection depends on `find … | grep -q .` and `PIPESTATUS[0]` for `find` errors. If `grep` fails independently while `find` exits 0 with no matches, the function returns 1 (no fresh descendant) and the entry can be deleted; if `grep` fails while `find` printed a path, a fresh tree could be deleted. **Suggested fix:** Drop the `grep` pipe: use `find … -print -quit` exit status alone (`find` exits 0 when a match is found on BSD/GNU), or capture output to a variable and branch on `find`’s exit code without piping through `grep`.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/cleanup.sh:36-38` — Freshness detection depends on `find … | grep -q .` and `PIPESTATUS[0]` for `find` errors. If `grep` fails independently while `find` exits 0 with no matches, the function returns 1 (no fresh descendant) and the entry can be deleted; if `grep` fails while `find` printed a path, a fresh tree could be deleted. **Suggested fix:** Drop the `grep` pipe: use `find … -print -quit` exit status alone (`find` exits 0 when a match is found on BSD/GNU), or capture output to a variable and branch on `find`’s exit code without piping through `grep`.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] **#3204 (awk harness + Gate A/B pins):** The branch matches the plan: `lib-plan-optional-trailers.awk` / `.sh` are byte-stable vs `main`; `test-trailer-awk.sh` covers the four awk modes and the listed edge cases (including `set +e`/`set -e` for expected `has_key` failures, `block_len` vs last-match-wins, octal `08`/`09`, and `test-design-structure.sh` `(3175)` pins now use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` on `approval-gates.md` and `discussion-rounds.md` only where specified.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **#3204 (awk harness + Gate A/B pins):** The branch matches the plan: `lib-plan-optional-trailers.awk` / `.sh` are byte-stable vs `main`; `test-trailer-awk.sh` covers the four awk modes and the listed edge cases (including `set +e`/`set -e` for expected `has_key` failures, `block_len` vs last-match-wins, octal `08`/`09`, and `test-design-structure.sh` `(3175)` pins now use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` on `approval-gates.md` and `discussion-rounds.md` only where specified.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **`skills/cleanup/scripts/test-cleanup.md:14`:** Still describes “bounded descendant activity” while `entry_has_fresh_descendant` is unbounded — doc drift, not a runtime bug by itself.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **`skills/cleanup/scripts/test-cleanup.md:14`:** Still describes “bounded descendant activity” while `entry_has_fresh_descendant` is unbounded — doc drift, not a runtime bug by itself.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **`skills/review-and-fix/scripts/review-and-fix.sh`:** Round-mode manifest-only staging and fail-closed `untracked-only` behavior are documented in `review-and-fix.md` and covered by new harness cases (`untracked-only`, hook-residue follow-up); intentional, not a regression.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **`skills/review-and-fix/scripts/review-and-fix.sh`:** Round-mode manifest-only staging and fail-closed `untracked-only` behavior are documented in `review-and-fix.md` and covered by new harness cases (`untracked-only`, hook-residue follow-up); intentional, not a regression.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] **Other branch commits:** `ship-pr.sh` pre-rebase `larch-logs/` fixup (#3209) and version/changelog bumps are scoped and tested in `test-ship-pr.sh`; no additional correctness issues identified in that slice from the diff review.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **Other branch commits:** `ship-pr.sh` pre-rebase `larch-logs/` fixup (#3209) and version/changelog bumps are scoped and tested in `test-ship-pr.sh`; no additional correctness issues identified in that slice from the diff review. **Commits (since merge-base with `main`):** `9adc5533b`, `00e93c876`, `3ccb5434a`, `34616d633`, `d33cdfb70`, `a8183aa1c`, `c45f52e55`.
- **Suggested revision**: Address the concern above.

### FINDING_34: **correctness** `skills/review-and-fix/scripts/test-review-and-fix.sh:460-476` — The new `manifest-outside-guard` block only white-box-tests `round_tracked_dirty_outside_manifest` after `eval "$(sed -n '/^round_tracked_dirty_outside_manifest/,/^}/p' "$SCRIPT")"`; it never runs `run_review_and_fix` with a dirty tracked path outside the coder delta. A regression that removes or bypasses the call at `skills/review-and-fix/scripts/review-and-fix.sh:488-491` (or passes the wrong manifest path) would leave production unprotected while this test still passes. **Suggested fix:** Add an orchestrator-level case (same style as `round-hook-residue` / `untracked-only-dirty`) that leaves a tracked dirty file outside `coder-stage-paths.txt`, runs `run_review_and_fix` with `--round-num 1`, and asserts exit **2**, `CODER_STATUS=failed`, and no round commit; keep the sed extract only if you still want a fast unit probe.
- **Reviewer**: dyn-eval-sed-test-extraction-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/test-review-and-fix.sh:460-476` — The new `manifest-outside-guard` block only white-box-tests `round_tracked_dirty_outside_manifest` after `eval "$(sed -n '/^round_tracked_dirty_outside_manifest/,/^}/p' "$SCRIPT")"`; it never runs `run_review_and_fix` with a dirty tracked path outside the coder delta. A regression that removes or bypasses the call at `skills/review-and-fix/scripts/review-and-fix.sh:488-491` (or passes the wrong manifest path) would leave production unprotected while this test still passes. **Suggested fix:** Add an orchestrator-level case (same style as `round-hook-residue` / `untracked-only-dirty`) that leaves a tracked dirty file outside `coder-stage-paths.txt`, runs `run_review_and_fix` with `--round-num 1`, and asserts exit **2**, `CODER_STATUS=failed`, and no round commit; keep the sed extract only if you still want a fast unit probe.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-eval-sed-test-extraction-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/test-review-and-fix.sh:469` / `skills/review-and-fix/scripts/review-and-fix.sh:351-359` — For the current function body, `/^round_tracked_dirty_outside_manifest/,/^}/` terminates at the sole column-0 `}` (lines 351–359); extraction is complete, and the subshell `cd "$work_manifest_outside"` with manifest `implement/round-1/coder-stage-paths.txt` matches production’s CWD-relative `git status` + manifest usage. The pattern is brittle: any future inner `}` at column 0 (e.g. `case` arm, heredoc delimiter) would truncate the extracted definition so the test could diverge from the shipped function while still passing. Prefer `declare -f` via a controlled `source`/`bash -c` (as at `test-review-and-fix.sh:2342`) or a small sourced stub.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] **`test-trailer-awk.sh` / #3204 scope** — Direct awk harness assertions align with `lib-plan-optional-trailers.awk` behavior (`block_len`, last-match-wins, `0[89]` rejection, block boundary, `set +e`/`set -e` on `has_key`); `lib-plan-optional-trailers.awk` and `.sh` are unchanged vs `main`. No additional correctness defects found in that slice.
- **Reviewer**: dyn-eval-sed-test-extraction-output.txt
- **Concern**: - **`test-trailer-awk.sh` / #3204 scope** — Direct awk harness assertions align with `lib-plan-optional-trailers.awk` behavior (`block_len`, last-match-wins, `0[89]` rejection, block boundary, `set +e`/`set -e` on `has_key`); `lib-plan-optional-trailers.awk` and `.sh` are unchanged vs `main`. No additional correctness defects found in that slice.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] **`scripts/test-design-structure.sh:405-414`** — `(3175)` pins correctly use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` for `$APPROVAL_MD` and `$DISCUSSION_MD` without disturbing adjacent preservation greps.
- **Reviewer**: dyn-eval-sed-test-extraction-output.txt
- **Concern**: - **`scripts/test-design-structure.sh:405-414`** — `(3175)` pins correctly use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` for `$APPROVAL_MD` and `$DISCUSSION_MD` without disturbing adjacent preservation greps.
- **Suggested revision**: Address the concern above.

