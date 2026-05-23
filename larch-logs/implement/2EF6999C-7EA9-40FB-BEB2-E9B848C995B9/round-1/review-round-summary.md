# Review Round 1

- Mode: `diff`
- 10 accepted, 2 rejected (1 exonerated)

## Accepted Findings

### FINDING_1: Cross-session recovery mis-binds URLs to OOS blocks (`sort -u` vs filing order)

- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-regex-pattern-accuracy-output.txt
- **Concern**: Recovery walks URLs in an order derived from the sentinel (including `sort -u` / lexicographic ordering) and assigns them to the first N `### OOS_*` blocks missing `Filed URL` in document scan order, instead of using the same pairing as `cmd_annotate` (`oos-design-filing-order.txt`, `ISSUE_<i>_URL`, declaration order). When lexical URL order differs from batch/OOS index order, a later `/design` session can stamp the wrong GitHub issue URL on the wrong OOS block while still treating the step as successfully skipped (`skip-sentinel`), breaking strict downstream expectations and operator trust in which issue tracks which finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-regex-pattern-accuracy-output.txt: persist a deterministic mapping for recovery (for example extend the cached sentinel to `OOS_<n><TAB><url>` lines written alongside the sorted URL list, or drop `sort -u` for the cache copy only and preserve declaration order), and drive recovery with the same keyed logic as the annotate Python (`cmd_annotate` `skills/design/scripts/file-design-oos.sh:287-305`).

---


### FINDING_11: Recovery Python succeeds with unconsumed sentinel URLs

- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-validation-gaps-output.txt
- **Concern**: Recovery can stop with URLs still unconsumed (e.g. more URLs than unfiled blocks) while Python still exits `0`, so shell treats recovery as success and can emit `skip-sentinel` without full `Filed URL` parity—desynchronizing sentinel vs `oos-accepted-design.md` and under-counting in strict modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-validation-gaps-output.txt: Have the Python step detect leftover URLs after the loop (or `ui != len(urls)` after completion), exit non-zero, or emit a distinct stderr file so the shell path logs a warning and avoids `skip-sentinel` success without full annotation parity.

---


### FINDING_14: Strict `Filed URL` line ERE is stricter than other pipeline patterns (space before colon)

- **Reviewer(s)**: dyn-regex-pattern-accuracy-output.txt
- **Concern**: Strict-line ERE requires `\*\*:` immediately before the colon, whereas other helpers allow optional whitespace before `:`; manually edited lines like `- **Filed URL** : https://…` could be ignored by `count_filed_url_field_lines`, under-counting `filed_urls`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-regex-pattern-accuracy-output.txt: align the strict prefix with the looser “optional whitespace before colon” convention, e.g. `\*\*Filed[[:space:]]URL\*\*[[:space:]]*:` in the `grep -E` pattern, or normalize accepted markdown before counting.

---


### FINDING_16: `--clear-cross-session-cache` accepted globally but only honored in `prepare`

- **Reviewer(s)**: dyn-validation-gaps-output.txt
- **Concern**: `--clear-cross-session-cache` is parsed for every phase, but only `cmd_prepare` reads `FILEDESIGN_CLEAR_CROSS_SESSION_CACHE`; an `annotate ... --clear-cross-session-cache` invocation clears nothing, emits no error, and can mislead operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-validation-gaps-output.txt: After argument parsing (once `PHASE` is known), if `PHASE` is `annotate` and `FILEDESIGN_CLEAR_CROSS_SESSION_CACHE` is true, print a clear stderr message, print `usage`, and exit **2**; optionally add a negative test in `skills/design/scripts/test-file-design-oos.sh`.

---

This output contains one or more `### FINDING_N:` blocks, so **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this file.

### FINDING_2: Recovery failure after sentinel copy still succeeds as `skip-sentinel`

- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: If `recover_oos_accepted_from_sentinel_urls` fails after copying cross-session cache into the in-session sentinel, `prepare` can still exit `0` with `skip-sentinel`, leaving `oos-issues-created.md` populated while `oos-accepted-design.md` may lack matching `Filed URL` fields. Downstream strict disposition / counters can under-count or assume filing complete while design markdown and GitHub drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: On recover failure do not emit skip-sentinel as success; fall back to ready/error or clear the copied sentinel and continue the normal pipeline.

---


### FINDING_4: Cross-session cache sync on partial annotate / `ISSUES_FAILED`

- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `sync_cross_session_oos_cache` can run when annotate will exit non-zero for `ISSUES_FAILED>0`, publishing cache from an incomplete sentinel. A later session may skip re-filing based on cache despite incomplete GitHub/issue or annotation state, conflicting with success-tied cache semantics and idempotency expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_5: Inconsistent absent-or-empty sentinel wording (SKILL vs contract doc)

- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [nit] In-session sentinel wording differs between `SKILL.md` and the contract doc for empty-file cases; operators may misunderstand when cross-session recovery triggers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---


### FINDING_6: Documentation order vs implemented control flow (in-session sentinel vs cache)

- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Written plan / Step 5b / step-9 narrative describes cache recovery before the in-session sentinel check (or “cache before in-session”), while `cmd_prepare` checks the in-session sentinel first, then the cache. Behavior may match intended precedence (in-session wins), but operator/debug narrative is misleading about ordering and when cache applies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Reword to cache-only after confirming in-session sentinel missing/empty; remove incorrect sequencing claim.

---


### FINDING_7: `oos-disposition-gate.md` strict-rule prose vs gate / table

- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Documentation claims disposition passes when `filed_urls >= non_security_oos` but describes (or implies) a different pass rule than the disjunctive implementation; readers may “fix” gate logic or tests to match the wrong bullet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---


### FINDING_8: Unvalidated issue number in cross-session cache paths (`rm`/`cp`/`mv`)

- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: [important] Issue number is interpolated into cache paths without validation; `rm`/`cp`/`mv` use that path. Values with `..`, slashes, or other path metacharacters under `ISSUE_NUMBER` / `--issue-number` can resolve outside the intended `~/.cache/larch/design-oos-filed` subtree and delete or clobber unrelated files under the operator’s home compared to the documented single-file sentinel contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---


