### FINDING_10: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **correctness** `skills/cleanup/scripts/cleanup.sh` — Top-level `/tmp` and cache scans use `find … ! -type l`, so symlink entries matching larch patterns are never candidates for removal (unlike the prior `[[ -e || -L ]]` loop). **Scenario:** A stale symlink like `larch4-review.diff` → old target persists indefinitely. **Suggested fix:** If symlink cleanup is desired, add an explicit `-type l` pass with safe age rules. *(#3212 / #3209 / `larch-logs` changes are separate from #3204; not expanded here per scope.)*
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_11: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `HEAD` (multi-commit branch) — The PR bundles #3204 with #3212 (`cleanup`), #3209 (`ship-pr`), and `review-and-fix` changes, each with expanded harnesses in the same diff. A red `make test-harnesses-N` cell may come from an unrelated commit; bisect by commit (`d33cdfb70` vs later) before treating it as a #3204 regression. **Suggested fix:** Split or label PR/commits for review; run `make test-trailer-helpers` and `make test-design-structure` on the #3204 commit in isolation when debugging.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `skills/design/scripts/test-trailer-{dedup,has-any,validate}.sh` — The four pre-existing thin adapters still have no `.md` siblings; the plan explicitly keeps that state (S030 flags orphaned `.md`, not `.sh` without docs). **Suggested fix:** None for #3204; optional follow-up only if script-md-siblings policy tightens beyond S030 citation rules.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_13: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/review-and-fix/scripts/review-and-fix.sh` (pre-branch behavior) — Prior round-mode commits used `git add -A`, which could stage **untracked** files left by an external coder (including accidental secret files). This branch’s manifest staging excludes untracked paths and fails closed on untracked-only dirt; that is a hardening fix, not a regression introduced here.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/cleanup/scripts/cleanup.sh` (pre-existing TOCTOU class) — Age-pass still lists candidates with `find` then deletes with `rm -rf` without re-validating the entry node type; a local race replacing a directory with a symlink after listing is the same class of trust-boundary caveat called out in `SECURITY.md` for operator-owned session roots, not newly introduced by the mtime refactor.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_15: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/review-and-fix.sh:954-987
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Selective round staging omits untracked coder outputs from manifest and post-commit checks. Coder creates only new untracked fix files; round commit succeeds with CODER_STATUS=applied while fixes never enter the branch. Include untracked paths in collect_round_stage_paths/staging or fail closed when ?? entries remain after commit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2856-2869
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-rebase larch-logs fixup ignores untracked dirtiness. Untracked files under larch-logs/ leave the tree dirty through drop-bump Guard 1 despite the #3209 fixup block. Extend dirty detection and git add to untracked larch-logs/ or document the tracked-only scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] correctness: skills/design/scripts/test-trailer-awk.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness does not cover trailing blank lines after diff_lines:. Malformed plan tails are untested; unlikely in production plans. Add an optional fixture asserting parse/keys behavior when blank lines follow diff_lines:.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/test-trailer-awk.sh:220` — Plan text asks for an explicit trailing `exit 0` after `echo "PASS: test-trailer-awk.sh"`; the harness relies on implicit success exit. **Suggested fix:** Add `exit 0` for literal plan alignment (behavior unchanged).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **correctness** `skills/design/scripts/lib-plan-optional-trailers.md:37-39` — Octal guard documents rejection but not that invalid `08`/`09` lines are skipped for `block_len` without stopping the upward scan (`octal-then-valid` in the harness). **Suggested fix:** Add one sentence under “Octal guard” describing skip-vs-break behavior. --- **Summary:** Implementation matches the #3204 plan: awk unit harness with normative edge coverage, cited docs, tightened `(3175)` pins, helpers wiring, and unchanged unit-under-test. Remaining gaps are documentation/minor exit-style nits, not functional plan misses.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] **#3204 (`test-trailer-awk.sh`, `test-design-structure.sh`, docs):** No correctness defects found relative to `lib-plan-optional-trailers.awk`; fixtures match upward-scan, last-match-wins, `block_len`, octal `0[89]` rejection, and `set +e`/`set -e` `has_key` probes. `.awk`/`.sh` are byte-stable in the diff.
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **#3204 (`test-trailer-awk.sh`, `test-design-structure.sh`, docs):** No correctness defects found relative to `lib-plan-optional-trailers.awk`; fixtures match upward-scan, last-match-wins, `block_len`, octal `0[89]` rejection, and `set +e`/`set -e` `has_key` probes. `.awk`/`.sh` are byte-stable in the diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] **`skills/review-and-fix/scripts/test-review-and-fix.sh`:** New hook-residue and untracked-only cases do not exercise rename porcelain, quoted paths with spaces, or pre-existing staged paths outside the coder delta; those gaps align with the parsing issues above.
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **`skills/review-and-fix/scripts/test-review-and-fix.sh`:** New hook-residue and untracked-only cases do not exercise rename porcelain, quoted paths with spaces, or pre-existing staged paths outside the coder delta; those gaps align with the parsing issues above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] **Other branch commits** (`ship-pr.sh`, `cleanup.sh`, version bump, run logs): Not reviewed for staging-path parsing; scout scope was `review-and-fix` manifest collection.
- **Reviewer**: dyn-staging-path-parsing-output.txt
- **Concern**: - **Other branch commits** (`ship-pr.sh`, `cleanup.sh`, version bump, run logs): Not reviewed for staging-path parsing; scout scope was `review-and-fix` manifest collection.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_3: [OUT_OF_SCOPE] architecture: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] PR mixes #3204 with #3212, #3209, version bumps, and larch-logs. Harder review/bisect; unrelated failures can block the trailer harness PR. Prefer stacked PRs or a #3204-only branch for merge if policy allows.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] **#3204 (awk harness + Gate A/B pins):** The branch matches the plan: `lib-plan-optional-trailers.awk` / `.sh` are byte-stable vs `main`; `test-trailer-awk.sh` covers the four awk modes and the listed edge cases (including `set +e`/`set -e` for expected `has_key` failures, `block_len` vs last-match-wins, octal `08`/`09`, and `test-design-structure.sh` `(3175)` pins now use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` on `approval-gates.md` and `discussion-rounds.md` only where specified.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **#3204 (awk harness + Gate A/B pins):** The branch matches the plan: `lib-plan-optional-trailers.awk` / `.sh` are byte-stable vs `main`; `test-trailer-awk.sh` covers the four awk modes and the listed edge cases (including `set +e`/`set -e` for expected `has_key` failures, `block_len` vs last-match-wins, octal `08`/`09`, and `test-design-structure.sh` `(3175)` pins now use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` on `approval-gates.md` and `discussion-rounds.md` only where specified.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] **`skills/cleanup/scripts/test-cleanup.md:14`:** Still describes “bounded descendant activity” while `entry_has_fresh_descendant` is unbounded — doc drift, not a runtime bug by itself.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **`skills/cleanup/scripts/test-cleanup.md:14`:** Still describes “bounded descendant activity” while `entry_has_fresh_descendant` is unbounded — doc drift, not a runtime bug by itself.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] **`skills/review-and-fix/scripts/review-and-fix.sh`:** Round-mode manifest-only staging and fail-closed `untracked-only` behavior are documented in `review-and-fix.md` and covered by new harness cases (`untracked-only`, hook-residue follow-up); intentional, not a regression.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **`skills/review-and-fix/scripts/review-and-fix.sh`:** Round-mode manifest-only staging and fail-closed `untracked-only` behavior are documented in `review-and-fix.md` and covered by new harness cases (`untracked-only`, hook-residue follow-up); intentional, not a regression.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] **Other branch commits:** `ship-pr.sh` pre-rebase `larch-logs/` fixup (#3209) and version/changelog bumps are scoped and tested in `test-ship-pr.sh`; no additional correctness issues identified in that slice from the diff review.
- **Reviewer**: dyn-find-mtime-depth-portability-output.txt
- **Concern**: - **Other branch commits:** `ship-pr.sh` pre-rebase `larch-logs/` fixup (#3209) and version/changelog bumps are scoped and tested in `test-ship-pr.sh`; no additional correctness issues identified in that slice from the diff review. **Commits (since merge-base with `main`):** `9adc5533b`, `00e93c876`, `3ccb5434a`, `34616d633`, `d33cdfb70`, `a8183aa1c`, `c45f52e55`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-eval-sed-test-extraction-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/test-review-and-fix.sh:469` / `skills/review-and-fix/scripts/review-and-fix.sh:351-359` — For the current function body, `/^round_tracked_dirty_outside_manifest/,/^}/` terminates at the sole column-0 `}` (lines 351–359); extraction is complete, and the subshell `cd "$work_manifest_outside"` with manifest `implement/round-1/coder-stage-paths.txt` matches production’s CWD-relative `git status` + manifest usage. The pattern is brittle: any future inner `}` at column 0 (e.g. `case` arm, heredoc delimiter) would truncate the extracted definition so the test could diverge from the shipped function while still passing. Prefer `declare -f` via a controlled `source`/`bash -c` (as at `test-review-and-fix.sh:2342`) or a small sourced stub.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_36: [OUT_OF_SCOPE] **`test-trailer-awk.sh` / #3204 scope** — Direct awk harness assertions align with `lib-plan-optional-trailers.awk` behavior (`block_len`, last-match-wins, `0[89]` rejection, block boundary, `set +e`/`set -e` on `has_key`); `lib-plan-optional-trailers.awk` and `.sh` are unchanged vs `main`. No additional correctness defects found in that slice.
- **Reviewer**: dyn-eval-sed-test-extraction-output.txt
- **Concern**: - **`test-trailer-awk.sh` / #3204 scope** — Direct awk harness assertions align with `lib-plan-optional-trailers.awk` behavior (`block_len`, last-match-wins, `0[89]` rejection, block boundary, `set +e`/`set -e` on `has_key`); `lib-plan-optional-trailers.awk` and `.sh` are unchanged vs `main`. No additional correctness defects found in that slice.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_37: [OUT_OF_SCOPE] **`scripts/test-design-structure.sh:405-414`** — `(3175)` pins correctly use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` for `$APPROVAL_MD` and `$DISCUSSION_MD` without disturbing adjacent preservation greps.
- **Reviewer**: dyn-eval-sed-test-extraction-output.txt
- **Concern**: - **`scripts/test-design-structure.sh:405-414`** — `(3175)` pins correctly use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` for `$APPROVAL_MD` and `$DISCUSSION_MD` without disturbing adjacent preservation greps.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/test-trailer-awk.sh` — No fixture where the last non-empty line is `diff_lines:` but trailing blank lines follow (only `trailer_nr` contract in docs). **Scenario:** If `trailer_nr` were computed from physical EOF instead of last non-empty line, the harness would not catch a regression. **Suggested fix:** Add a fixture with `diff_lines:` then blank lines and assert parse/keys unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **correctness** `skills/design/scripts/test-trailer-awk.sh` — `has_key` does not probe `diff_deleted: 08` alone (only `diff_added: 08` and `diff_deleted: 09` in `octal-rejected`). **Scenario:** A broken `substr`/offset for `diff_deleted` could slip through while `diff_added` octal tests pass. **Suggested fix:** Add `diff_deleted: 08` on its own line in a small fixture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

