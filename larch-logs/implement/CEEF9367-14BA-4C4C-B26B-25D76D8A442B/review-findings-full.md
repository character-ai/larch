### FINDING_1: panel [code-review/accepted]

## ### Plan and requirements verification

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## ### Structured TSV (sidecar not written — read-only review mode)

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **(1) NEVER bullet** — Implemented via `grep -qE` in [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (lines 54–56). Matches current NEVER #13 prose (backtick + `` `$IMPLEMENT_TMPDIR` ``): `correctness` + `both`.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **(1) NEVER bullet** — Implemented via `grep -qE` in [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (lines 54–56). Matches current NEVER #13 prose (backtick + `` `$IMPLEMENT_TMPDIR` ``): `correctness` + `both`.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **(2) Step 18 order** — Awk scan from `<!-- step:18` with restore before `implement-finalize.sh` teardown inside fenced blocks: `correctness` + `both`. Matches current SKILL (restore at 1917, teardown at 1922 in the same `` ```bash `` block).

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **(2) Step 18 order** — Awk scan from `<!-- step:18` with restore before `implement-finalize.sh` teardown inside fenced blocks: `correctness` + `both`. Matches current SKILL (restore at 1917, teardown at 1922 in the same `` ```bash `` block).
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **(3) restore script + sibling doc + executable** — File checks at 96–98: `correctness` + `both`.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **(3) restore script + sibling doc + executable** — File checks at 96–98: `correctness` + `both`.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **(4) lib script + sibling doc + references in restore and ship-pr** — 100–105: `correctness` + `both` (substring check is slightly weaker than “sourced”; see finding).

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **(4) lib script + sibling doc + references in restore and ship-pr** — 100–105: `correctness` + `both` (substring check is slightly weaker than “sourced”; see finding).
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Commits reviewed** (`git merge-base HEAD main`..HEAD):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Docs** — [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md) updated: `both`.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Docs** — [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md) updated: `both`.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Extra diff** — [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) from commit `4dc2d2da` is outside the written plan/feature bullets (repo already tracks many similar manifests); scope note only.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Extra diff** — [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) from commit `4dc2d2da` is outside the written plan/feature bullets (repo already tracks many similar manifests); scope note only.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## **Important** `correctness` — `scripts/test-implement-structure.sh:102-105` only greps for the literal filename, so the “must source `lib-finalize-state-keys.sh`” assertion passes on comments or error strings. Concrete failing scenario: remove the actual `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line from `scripts/ship-pr.sh:20` but leave the adjacent shellcheck comment or sentinel error text; `bash scripts/test-implement-structure.sh` still passes even though the contract is violated. Match an executable source statement instead, for example a regex anchored to `source`/`.` plus `$SCRIPT_DIR/lib-finalize-state-keys.sh`, and apply it to both `scripts/restore-finalize-state.sh` and `scripts/ship-pr.sh`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `scripts/test-implement-structure.sh:102-105` only greps for the literal filename, so the “must source `lib-finalize-state-keys.sh`” assertion passes on comments or error strings. Concrete failing scenario: remove the actual `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line from `scripts/ship-pr.sh:20` but leave the adjacent shellcheck comment or sentinel error text; `bash scripts/test-implement-structure.sh` still passes even though the contract is violated. Match an executable source statement instead, for example a regex anchored to `source`/`.` plus `$SCRIPT_DIR/lib-finalize-state-keys.sh`, and apply it to both `scripts/restore-finalize-state.sh` and `scripts/ship-pr.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## **Important** · **correctness** · [`scripts/test-implement-structure.sh:102-105`](scripts/test-implement-structure.sh:102-105) · Assertion (d) uses `grep -qF 'lib-finalize-state-keys.sh'`, which matches any line containing that substring, including the `# shellcheck source=scripts/lib-finalize-state-keys.sh` directive. That contradicts the feature text (“**sourced** by both …”) and the plan’s own manual negative test (“remove `source` line from ship-pr.sh → assertion (d) fails”), because removing the runtime `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line while leaving the shellcheck comment (a common edit) still satisfies the grep. **Scenario:** `ship-pr.sh` / `restore-finalize-state.sh` no longer load the library at runtime, but CI stays green. **Fix:** Assert a real top-level `source` (or `.`) invocation, e.g. match `^[[:space:]]*source[[:space:]].*lib-finalize-state-keys\.sh` (and the same for `restore-finalize-state.sh`), or otherwise exclude pure-comment matches.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Important** · **correctness** · [`scripts/test-implement-structure.sh:102-105`](scripts/test-implement-structure.sh:102-105) · Assertion (d) uses `grep -qF 'lib-finalize-state-keys.sh'`, which matches any line containing that substring, including the `# shellcheck source=scripts/lib-finalize-state-keys.sh` directive. That contradicts the feature text (“**sourced** by both …”) and the plan’s own manual negative test (“remove `source` line from ship-pr.sh → assertion (d) fails”), because removing the runtime `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line while leaving the shellcheck comment (a common edit) still satisfies the grep. **Scenario:** `ship-pr.sh` / `restore-finalize-state.sh` no longer load the library at runtime, but CI stays green. **Fix:** Assert a real top-level `source` (or `.`) invocation, e.g. match `^[[:space:]]*source[[:space:]].*lib-finalize-state-keys\.sh` (and the same for `restore-finalize-state.sh`), or otherwise exclude pure-comment matches.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## **Important** · **risk-integration** · [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) (new file) · The branch adds a committed `/implement` run manifest (`chore(larch-logs): flush implement run …`) that is outside the supplied feature description and implementation plan (which only scoped `scripts/test-implement-structure.{sh,md}`). That file records local provenance (`operator_cwd`, `operator_repo_root`, issue 2177, `status: in-progress`) and is unrelated to enforcing the finalize-state write prohibition. **Scenario:** Reviewers merge expecting a harness-only PR but ship session metadata and an incomplete run log stub. **Fix:** Drop or revert that commit / path from the PR so the diff matches the plan’s file list.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** · **risk-integration** · [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) (new file) · The branch adds a committed `/implement` run manifest (`chore(larch-logs): flush implement run …`) that is outside the supplied feature description and implementation plan (which only scoped `scripts/test-implement-structure.{sh,md}`). That file records local provenance (`operator_cwd`, `operator_repo_root`, issue 2177, `status: in-progress`) and is unrelated to enforcing the finalize-state write prohibition. **Scenario:** Reviewers merge expecting a harness-only PR but ship session metadata and an incomplete run log stub. **Fix:** Drop or revert that commit / path from the PR so the diff matches the plan’s file list.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## **Important** — **correctness** — [`scripts/test-implement-structure.sh:102-105`](scripts/test-implement-structure.sh) — The checks use `grep -qF 'lib-finalize-state-keys.sh'`, but the failure strings claim the scripts “must **source**” the library. **Scenario:** Remove the live `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line from [`scripts/restore-finalize-state.sh:44-46`](scripts/restore-finalize-state.sh) or [`scripts/ship-pr.sh:19-21`](scripts/ship-pr.sh) while leaving the `# shellcheck source=...lib-finalize-state-keys.sh` comment (or any prose mentioning the filename). CI still passes, yet `write_finalize_state` / ship-pr paths lose the keyed state contract and can fail at runtime with missing keys or wrong defaults. **Fix:** Assert an actual `source` invocation (e.g. `grep -E` on `^[[:space:]]*source[[:space:]].*lib-finalize-state-keys\.sh` or equivalent), and align failure messages with what is enforced.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** — **correctness** — [`scripts/test-implement-structure.sh:102-105`](scripts/test-implement-structure.sh) — The checks use `grep -qF 'lib-finalize-state-keys.sh'`, but the failure strings claim the scripts “must **source**” the library. **Scenario:** Remove the live `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line from [`scripts/restore-finalize-state.sh:44-46`](scripts/restore-finalize-state.sh) or [`scripts/ship-pr.sh:19-21`](scripts/ship-pr.sh) while leaving the `# shellcheck source=...lib-finalize-state-keys.sh` comment (or any prose mentioning the filename). CI still passes, yet `write_finalize_state` / ship-pr paths lose the keyed state contract and can fail at runtime with missing keys or wrong defaults. **Fix:** Assert an actual `source` invocation (e.g. `grep -E` on `^[[:space:]]*source[[:space:]].*lib-finalize-state-keys\.sh` or equivalent), and align failure messages with what is enforced.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## **Important**, **security**, [larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:5-6](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json): The new manifest records `operator_cwd` and `operator_repo_root` as absolute paths (`/Users/zhupanov/larch2`), which embeds the operator’s OS username in the committed tree. Anyone with clone access learns host layout and identity-adjacent metadata; forks/PRs amplify exposure if this pattern repeats. **Suggested fix:** Drop this file from the PR, add generation-time redaction (e.g. store only a hash or `REDACTED`), or ensure `larch-logs/**` stays out of version control for machine-local paths.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Important**, **security**, [larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:5-6](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json): The new manifest records `operator_cwd` and `operator_repo_root` as absolute paths (`/Users/zhupanov/larch2`), which embeds the operator’s OS username in the committed tree. Anyone with clone access learns host layout and identity-adjacent metadata; forks/PRs amplify exposure if this pattern repeats. **Suggested fix:** Drop this file from the PR, add generation-time redaction (e.g. store only a hash or `REDACTED`), or ensure `larch-logs/**` stays out of version control for machine-local paths.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## **Latent** (`correctness`) [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh):58-94 — The awk scanner records the **first** `restore-finalize-state.sh` and **first** `implement-finalize.sh … teardown` in **any** fenced `bash` block after `<!-- step:18`. **Scenario:** A later doc edit adds an earlier Step 18 `bash` fence that quotes or demonstrates `implement-finalize.sh teardown` before the real teardown block; `teardown_line` is set early, `restore_line` is still 0 until the final block, and the check exits 11 (“teardown not found”) or 12 (wrong order) even if the load-bearing block still has restore before teardown. **Fix:** Restrict to the last relevant bash block, or match the specific `if [ -f …/ship-pr-state.sh ]` / restore / teardown sequence.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Latent** (`correctness`) [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh):58-94 — The awk scanner records the **first** `restore-finalize-state.sh` and **first** `implement-finalize.sh … teardown` in **any** fenced `bash` block after `<!-- step:18`. **Scenario:** A later doc edit adds an earlier Step 18 `bash` fence that quotes or demonstrates `implement-finalize.sh teardown` before the real teardown block; `teardown_line` is set early, `restore_line` is still 0 until the final block, and the check exits 11 (“teardown not found”) or 12 (wrong order) even if the load-bearing block still has restore before teardown. **Fix:** Restrict to the last relevant bash block, or match the specific `if [ -f …/ship-pr-state.sh ]` / restore / teardown sequence.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## **Latent** (`risk-integration`) [`scripts/test-implement-structure.sh:102-105`](scripts/test-implement-structure.sh): The failure strings say both scripts “must **source**” `lib-finalize-state-keys.sh`, but the check is `grep -qF 'lib-finalize-state-keys.sh'`, which is satisfied by any line containing that substring (for example the `# shellcheck source=...` directive alone if someone removed the real `source` line). **Scenario:** A bad edit drops the `source` call but leaves the shellcheck hint; CI still passes while `write_finalize_state` / restore paths break at runtime. **Fix:** Match `^[[:space:]]*source[[:space:]]` (or similar) on the same line as `lib-finalize-state-keys.sh`, and align failure copy with the predicate.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Latent** (`risk-integration`) [`scripts/test-implement-structure.sh:102-105`](scripts/test-implement-structure.sh): The failure strings say both scripts “must **source**” `lib-finalize-state-keys.sh`, but the check is `grep -qF 'lib-finalize-state-keys.sh'`, which is satisfied by any line containing that substring (for example the `# shellcheck source=...` directive alone if someone removed the real `source` line). **Scenario:** A bad edit drops the `source` call but leaves the shellcheck hint; CI still passes while `write_finalize_state` / restore paths break at runtime. **Fix:** Match `^[[:space:]]*source[[:space:]]` (or similar) on the same line as `lib-finalize-state-keys.sh`, and align failure copy with the predicate.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## **Latent** (`risk-integration`) [`scripts/test-implement-structure.sh:58-86`](scripts/test-implement-structure.sh): The Step 18 scanner records the first fenced-`bash` line matching `/\/scripts\/restore-finalize-state\.sh/` and the first matching `/\/scripts\/implement-finalize\.sh.*teardown/` on a **single** line. **Scenario:** A doc-only bash line (comment) mentioning those paths before the real calls could skew line numbers; splitting `implement-finalize.sh` and `teardown` across lines would make the teardown pattern miss and fail with exit 11 even though order is correct. **Fix:** Anchor on the real invocation (stricter regex, ignore comment-only lines, or allow multi-line patterns).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Latent** (`risk-integration`) [`scripts/test-implement-structure.sh:58-86`](scripts/test-implement-structure.sh): The Step 18 scanner records the first fenced-`bash` line matching `/\/scripts\/restore-finalize-state\.sh/` and the first matching `/\/scripts\/implement-finalize\.sh.*teardown/` on a **single** line. **Scenario:** A doc-only bash line (comment) mentioning those paths before the real calls could skew line numbers; splitting `implement-finalize.sh` and `teardown` across lines would make the teardown pattern miss and fail with exit 11 even though order is correct. **Fix:** Anchor on the real invocation (stricter regex, ignore comment-only lines, or allow multi-line patterns).
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## **Latent** `correctness` (source: `plan` / `both`) — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh):68-80 — The Step 18 scanner only enters fenced code when the fence line is exactly `` ```bash `` (`/^```bash[[:space:]]*$/`). **Concrete scenario:** If SKILL.md keeps the same restore/teardown lines but renames the fence to `` ```sh `` or `` ```shell ``, `restore_line` / `teardown_line` stay 0, awk exits 10, and CI fails with “restore-finalize-state.sh not found in Step 18 region” even though the contract is still satisfied in prose. **Fix:** Accept the same fence tags the skill uses elsewhere (e.g. allow `bash` and `sh`), or document that Step 18 teardown must stay in a `` ```bash `` block.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Latent** `correctness` (source: `plan` / `both`) — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh):68-80 — The Step 18 scanner only enters fenced code when the fence line is exactly `` ```bash `` (`/^```bash[[:space:]]*$/`). **Concrete scenario:** If SKILL.md keeps the same restore/teardown lines but renames the fence to `` ```sh `` or `` ```shell ``, `restore_line` / `teardown_line` stay 0, awk exits 10, and CI fails with “restore-finalize-state.sh not found in Step 18 region” even though the contract is still satisfied in prose. **Fix:** Accept the same fence tags the skill uses elsewhere (e.g. allow `bash` and `sh`), or document that Step 18 teardown must stay in a `` ```bash `` block.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## **Latent** — **risk-integration** — [`scripts/test-implement-structure.sh:68-71`](scripts/test-implement-structure.sh) — Step 18 ordering only scans fenced blocks that open with exactly `` ```bash `` (line-start). **Scenario:** Step 18’s teardown block is renamed to `` ```sh `` or another language tag while semantics stay the same. The awk never sets `in_bash`, exits 10 (“restore … not found”), and CI blocks a harmless doc refactor. **Fix:** Accept the same block openings the repo already allows elsewhere, or document this as an intentional pin on `` ```bash `` only.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Latent** — **risk-integration** — [`scripts/test-implement-structure.sh:68-71`](scripts/test-implement-structure.sh) — Step 18 ordering only scans fenced blocks that open with exactly `` ```bash `` (line-start). **Scenario:** Step 18’s teardown block is renamed to `` ```sh `` or another language tag while semantics stay the same. The awk never sets `in_bash`, exits 10 (“restore … not found”), and CI blocks a harmless doc refactor. **Fix:** Accept the same block openings the repo already allows elsewhere, or document this as an intentional pin on `` ```bash `` only.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## **Latent** — **risk-integration** — [`scripts/test-implement-structure.sh:79-80`](scripts/test-implement-structure.sh) — The teardown probe requires `/scripts/implement-finalize\.sh` and `teardown` on the **same line**. **Scenario:** Someone wraps the call for readability so `teardown` moves to the next line (still one shell invocation). Awk never records `teardown_line`, exits 11, and CI fails despite preserved restore-before-teardown order. **Fix:** Match across continuations (multi-line awk/perl) or key off the first line of the `implement-finalize.sh` invocation and the next non-empty line for `teardown`.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **Latent** — **risk-integration** — [`scripts/test-implement-structure.sh:79-80`](scripts/test-implement-structure.sh) — The teardown probe requires `/scripts/implement-finalize\.sh` and `teardown` on the **same line**. **Scenario:** Someone wraps the call for readability so `teardown` moves to the next line (still one shell invocation). Awk never records `teardown_line`, exits 11, and CI fails despite preserved restore-before-teardown order. **Fix:** Match across continuations (multi-line awk/perl) or key off the first line of the `implement-finalize.sh` invocation and the next non-empty line for `teardown`.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## **Nit** (`code-quality`) [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-26 — The branch bundles a new implement `manifest.json` (`status` in-progress, `operator_cwd` under a developer home path per [`docs/run-logs.md`](docs/run-logs.md) contract) with the structure-test work; the feature description only called out [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) and [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md). **Impact:** Reviewers and bisect blame must disentangle unrelated provenance churn from the harness change. **Fix:** Land the manifest flush on its own branch/PR or omit it from the structure-test PR.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Nit** (`code-quality`) [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-26 — The branch bundles a new implement `manifest.json` (`status` in-progress, `operator_cwd` under a developer home path per [`docs/run-logs.md`](docs/run-logs.md) contract) with the structure-test work; the feature description only called out [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) and [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md). **Impact:** Reviewers and bisect blame must disentangle unrelated provenance churn from the harness change. **Fix:** Land the manifest flush on its own branch/PR or omit it from the structure-test PR.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## **Nit** (`code-quality`, `plan`) [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh):102-105 — Failure strings claim the scripts “must **source**” `lib-finalize-state-keys.sh`, but `grep -qF 'lib-finalize-state-keys.sh'` is satisfied by any line containing that substring (e.g. a `# shellcheck source=…` comment without a runtime `source`). **Scenario:** A future edit removes the `source` line but leaves a comment referencing the path; CI stays green while the contract breaks. **Fix:** Match a real `source` line (e.g. `grep -E '^[[:space:]]*source[[:space:]].*lib-finalize-state-keys\.sh'`) or require both `source` and the sentinel variable check already used inside the scripts.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Nit** (`code-quality`, `plan`) [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh):102-105 — Failure strings claim the scripts “must **source**” `lib-finalize-state-keys.sh`, but `grep -qF 'lib-finalize-state-keys.sh'` is satisfied by any line containing that substring (e.g. a `# shellcheck source=…` comment without a runtime `source`). **Scenario:** A future edit removes the `source` line but leaves a comment referencing the path; CI stays green while the contract breaks. **Fix:** Match a real `source` line (e.g. `grep -E '^[[:space:]]*source[[:space:]].*lib-finalize-state-keys\.sh'`) or require both `source` and the sentinel variable check already used inside the scripts.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## **Nit** (`risk-integration`) [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json): The branch bundles a second commit that adds an in-progress implement `manifest.json` alongside the structural-test change. **Impact:** Unrelated noise for reviewers and consumers of the PR unless flushing this path is an explicit deliverable. **Fix:** Land the manifest in a separate PR or omit if accidental.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Nit** (`risk-integration`) [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json): The branch bundles a second commit that adds an in-progress implement `manifest.json` alongside the structural-test change. **Impact:** Unrelated noise for reviewers and consumers of the PR unless flushing this path is an explicit deliverable. **Fix:** Land the manifest in a separate PR or omit if accidental.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## **Nit** `correctness` (source: `both`) — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh):102-105 — Assertions use `grep -qF 'lib-finalize-state-keys.sh'`, but failure messages claim the file “must **source**” the library. **Concrete scenario:** Someone removes the runtime `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` lines but leaves a comment or `# shellcheck source=.../lib-finalize-state-keys.sh` line containing the same substring; CI still passes while `write_finalize_state` / restore would break at runtime. **Fix:** Match a real `source` invocation (e.g. anchored `^[[:space:]]*source` line including that path) or relax the failure string to “must reference …”.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Nit** `correctness` (source: `both`) — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh):102-105 — Assertions use `grep -qF 'lib-finalize-state-keys.sh'`, but failure messages claim the file “must **source**” the library. **Concrete scenario:** Someone removes the runtime `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` lines but leaves a comment or `# shellcheck source=.../lib-finalize-state-keys.sh` line containing the same substring; CI still passes while `write_finalize_state` / restore would break at runtime. **Fix:** Match a real `source` invocation (e.g. anchored `^[[:space:]]*source` line including that path) or relax the failure string to “must reference …”.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## **Nit** `risk-integration` (source: `requirements` only) — Branch includes two commits: harness (`08170256`) plus [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) (`4dc2d2da`). Not a logic bug in the new assertions, but it widens PR scope beyond the feature description’s listed files. **Fix:** Split PRs or document why the manifest belongs in the same merge.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **Nit** `risk-integration` (source: `requirements` only) — Branch includes two commits: harness (`08170256`) plus [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) (`4dc2d2da`). Not a logic bug in the new assertions, but it widens PR scope beyond the feature description’s listed files. **Fix:** Split PRs or document why the manifest belongs in the same merge.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## **Nit** — **risk-integration** — Branch includes a second commit adding [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) (operator paths, `in-progress`, issue metadata), which is outside the stated feature (structure test + doc). **Scenario:** Reviewers must disentangle behavioral test changes from run-log churn; rebases/conflicts touch unrelated paths. **Fix:** Drop that commit from this PR or document why this manifest must ship with the lint change.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Nit** — **risk-integration** — Branch includes a second commit adding [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) (operator paths, `in-progress`, issue metadata), which is outside the stated feature (structure test + doc). **Scenario:** Reviewers must disentangle behavioral test changes from run-log churn; rebases/conflicts touch unrelated paths. **Fix:** Drop that commit from this PR or document why this manifest must ship with the lint change.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## **Nit**, **correctness**, [scripts/test-implement-structure.sh:102-105](scripts/test-implement-structure.sh): Assertions use `grep -qF 'lib-finalize-state-keys.sh'` while failure text says “must **source**”. A comment or unrelated string containing the filename would satisfy the grep but not the contract. **Suggested fix:** Match a `source` line (e.g. `grep -E '^[[:space:]]*source[[:space:]].*lib-finalize-state-keys\.sh'`) or require both `source` and the path, and align the message with the check.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Nit**, **correctness**, [scripts/test-implement-structure.sh:102-105](scripts/test-implement-structure.sh): Assertions use `grep -qF 'lib-finalize-state-keys.sh'` while failure text says “must **source**”. A comment or unrelated string containing the filename would satisfy the grep but not the contract. **Suggested fix:** Match a `source` line (e.g. `grep -E '^[[:space:]]*source[[:space:]].*lib-finalize-state-keys\.sh'`) or require both `source` and the path, and align the message with the check.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## **Plan / requirements lens:** The four assertion groups and [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md) update match the stated plan; [`Makefile`](Makefile) already runs `bash scripts/test-implement-structure.sh` via `test-implement-structure` / `lint`, so CI wiring is unchanged. The plan’s manual negative tests are not encoded as automated cases (acceptable for a shell harness; no TDD obligation in the diff).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## **Read-only note:** Hard constraints forbid writing the TSV sidecar to disk. Below is the same content you can save as `diff.txt.tsv` (or your chosen path) locally.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## **Read-only note:** The instructions asked for a `.tsv` sidecar on disk; that was not created so the workspace stays non-mutating. Records below are the sidecar payload.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## **TSV (sidecar content; file not written — read-only constraint)**

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## **TSV sidecar content** (not written to disk):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## ---

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	scripts/test-implement-structure.sh:102-105	grep -qF only requires filename substring; messages claim must source	Remove source line but keep shellcheck comment mentioning lib-finalize-state-keys.sh; CI passes, runtime loses LARCH_FINALIZE_STATE_KEYS and state writes break or mis-key	Match explicit source lines or rename failure strings to match weaker grep
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	scripts/test-implement-structure.sh:102-105	lib-finalize sourcing check is substring grep that matches shellcheck comments	Removing runtime source while keeping shellcheck directive still passes CI; violates feature sourced requirement and plan negative test	Use a line anchored source pattern or otherwise require a non-comment source line
- **Suggested revision**: Address the concern above.

### FINDING_36: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk_integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json	Committed implement run manifest not in plan or feature scope	Merge ships unrelated in-progress run metadata and local operator paths while reviewers expect only test harness changes	Remove or revert the larch-logs commit so the PR matches the plan file list
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	security	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:5-6	Committed manifest embeds absolute operator paths under /Users/...	Clones and PR diffs expose local username and home-style path layout; repeats on every flushed run widen accidental PII in git history	Remove from PR; redact paths at write time; or stop committing per-machine manifests
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	scripts/test-implement-structure.sh:58-94	First restore/teardown match across all Step 18 bash fences	Earlier educational bash snippet mentioning teardown before restore makes order check fail despite correct final block	Scope awk to the teardown bash fence or last matching pair
- **Suggested revision**: Address the concern above.

### FINDING_39: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	scripts/test-implement-structure.sh:68-80	Step 18 awk only recognizes ```bash fences	If SKILL renames the teardown fence to ```sh while keeping restore/teardown lines, awk exits 10 and CI fails falsely	Allow matching fence types used in SKILL or document ```bash as required
- **Suggested revision**: Address the concern above.

### FINDING_40: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	scripts/test-implement-structure.sh:102-105	Failure messages claim scripts must source lib-finalize-state-keys.sh but grep -qF only requires substring presence.	Removing the source line while keeping a shellcheck comment line can leave CI green until runtime errors in restore or ship-pr.	Use a source-line predicate or tighten grep and update failure messages to match.
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	scripts/test-implement-structure.sh:58-86	Step 18 awk uses first-line matches for restore and single-line implement-finalize.sh.*teardown inside fenced bash.	Comment lines matching the path patterns or a line wrap splitting teardown from the script name can yield false ordering failure or a misleading first hit.	Ignore comments or match the concrete invocation lines; allow multi-line teardown if formatting changes.
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	scripts/test-implement-structure.sh:68-71	Step 18 awk only enters bash fences on exact ```bash opener	Change Step 18 fence to ```sh; restore/teardown still in doc; test exits 10	Allow ```sh or document intentional bash-only contract
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	scripts/test-implement-structure.sh:79-80	teardown pattern requires same line as implement-finalize.sh path	Split implement-finalize.sh and teardown across lines; ordering unchanged; exit 11	Multi-line match or relax line-local pattern
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-26	New implement manifest committed in same branch as structure-test-only feature description	Reviewers must separate unrelated larch-log flush from harness diff; bisect noise	Omit from PR or land as separate branch/PR
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	scripts/test-implement-structure.sh:102-105	grep -qF matches any mention; messages claim must source	Removing source while keeping a comment that names the file still passes CI	Use line-anchored source pattern or stricter contract
- **Suggested revision**: Address the concern above.

### FINDING_46: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	scripts/test-implement-structure.sh:102-105	grep -qF matches any occurrence, not necessarily source	Removing active source but keeping shellcheck/comment text with lib-finalize-state-keys.sh still passes	Assert a line-start source pattern or soften the failure message
- **Suggested revision**: Address the concern above.

### FINDING_47: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	scripts/test-implement-structure.sh:102-105	grep -qF on filename does not prove source; message claims source	Future edit could add a comment with the filename and drop the real source line while CI still passes	Anchor grep to a source line pattern or shellcheck-style comment+source pair; align failure strings with checks
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20	Committed implement run manifest rides with the test-harness feature commits.	Reviewers must triage unrelated run metadata; may confuse dirty-tree or release hygiene expectations.	Split into its own PR or omit if not required.
- **Suggested revision**: Address the concern above.

### FINDING_49: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20	Implement run manifest commit bundled with harness-only feature text	Reviewers must vet unrelated run metadata alongside assertion changes	Split commits/PRs or justify combined scope
- **Suggested revision**: Address the concern above.

### FINDING_50: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20	Unrelated implement run manifest bundled with structure-test PR	Extra review/conflict surface unrelated to finalize-state assertions	Split PR or omit manifest from this branch
- **Suggested revision**: Address the concern above.

### FINDING_51: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	architecture	skills/implement/SKILL.md:1836-1945	Awk step-region logic depends on no later <!-- step: inside Step 18	Not changed by this diff; only relevant if Step 18 gains inner step markers later	N/A (document or tighten awk if structure changes)
- **Suggested revision**: Address the concern above.

### FINDING_52: panel [code-review/accepted]

## Checking whether a removed `source` line would leave a `shellcheck` directive that still satisfies `grep -qF 'lib-finalize-state-keys.sh'`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_53: panel [code-review/accepted]

## Checking whether the committed `larch-logs` path is standard and scanning `test-implement-structure.sh` for brittleness.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_54: panel [code-review/accepted]

## Commits on branch vs `main`: `08170256` (structure-test assertions + doc), `4dc2d2da` (new `larch-logs/.../manifest.json`). Read-only review complete; **no files were written** (including the requested `.tsv` sidecar), so structured rows appear at the end of this message for copy/paste.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_55: panel [code-review/accepted]

## I ran `bash scripts/test-implement-structure.sh`; it currently passes.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_56: panel [code-review/accepted]

## No contradiction between the plan and the feature description that the code resolves the wrong way.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_57: panel [code-review/accepted]

## Plan vs diff: the four assertion groups and [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md) update match the stated plan. The extra commit adding [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) is outside the feature description’s file list.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_58: panel [code-review/accepted]

## Read-only constraint: no file was written. The requested `.tsv` sidecar cannot be created without mutating the tree; structured rows appear in the `Structured TSV` block at the end for tooling to capture manually if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_59: panel [code-review/accepted]

## Read-only mode: no file was written. Below is the TSV sidecar content that would have gone to `diff.txt.tsv` (copy out if your orchestrator expects a file).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_60: panel [code-review/accepted]

## Reading the modified script and SKILL.md Step 18 to verify patterns, ordering logic, and line numbers for the review.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_61: panel [code-review/accepted]

## Review complete. The branch adds structural tests plus a committed implement-run manifest. Per your read-only constraint, no sidecar file was written; TSV rows appear in a separate block at the end.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_62: panel [code-review/accepted]

## Reviewed the precomputed diff against the feature description and plan, verified patterns against [`skills/implement/SKILL.md`](skills/implement/SKILL.md) (Step 18 region and NEVER #13) and the shell scripts. Read-only mode prevents writing a `.tsv` file on disk; the same TSV records appear in a fenced block below.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_63: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: Gathering the branch diff and commit history for a read-only correctness review.
- **Suggested revision**: Address the concern above.

### FINDING_64: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only review. We won't write the TSV sidecar (conflicts with read-only); we'll include TSV records in the response.
- **Suggested revision**: Address the concern above.

### FINDING_65: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Gathering the diff and commit list for a read-only plan-fidelity review. We won't write the TSV sidecar (read-only constraint); we'll include TSV lines in the response if needed.
- **Suggested revision**: Address the concern above.

### FINDING_66: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only security-focused review. We won't write the TSV sidecar (read-only constraint); we'll include TSV records in the response.
- **Suggested revision**: Address the concern above.

### FINDING_67: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Gathering the diff and commit history for a read-only review. We won't write the TSV sidecar file (read-only constraint); we'll include TSV records in the response if needed.
- **Suggested revision**: Address the concern above.

### FINDING_68: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only review. We won't write the sidecar file (read-only / no edits); we'll include TSV rows in the response if needed.
- **Suggested revision**: Address the concern above.

### FINDING_69: panel [code-review/accepted]

## TSV (intended sidecar content; not written to disk due to read-only review mode):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_70: panel [code-review/accepted]

## Verification against current `skills/implement/SKILL.md`: Step 18 is the last `<!-- step:` marker (no later marker clears `in_step`), the teardown block has `restore-finalize-state.sh` then `implement-finalize.sh teardown` on consecutive lines in the same fenced `bash` block ([`SKILL.md:1916-1924`](skills/implement/SKILL.md)), and NEVER #13 matches the harness regex (backtick after `modify` is covered by the `.` in the ERE). Commits on branch: `08170256` (structure test), `4dc2d2da` (larch-logs manifest).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_71: panel [code-review/accepted]

## Verifying Step 18 markers and script content against the new checks by reading the relevant files.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_72: panel [code-review/accepted]

## Verifying Step 18 structure and NEVER-bullet text in the repo against the awk/grep logic.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_73: panel [code-review/accepted]

## Verifying Step 18 structure in SKILL.md and whether committing `larch-logs` manifests is intentional (path leakage).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_74: panel [code-review/accepted]

## Verifying Step 18 structure, NEVER bullet text, and whether `grep -qF` matches actual `source` usage. Checking the larch-logs file inclusion.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_75: panel [code-review/accepted]

## Verifying implementation against the plan by reading `skills/implement/SKILL.md` (Step 18), `scripts/restore-finalize-state.sh`, and `scripts/ship-pr.sh`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_76: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit**, **architecture**, [skills/implement/SKILL.md:1836-1945](skills/implement/SKILL.md): Step 18 is the last `<!-- step:*` marker in the file, so the awk “next step” exit rule never runs; the scan runs from that marker to EOF. This is consistent with current content and is not introduced by the test diff; called out only because future edits adding another `<!-- step:` inside Step 18 would change awk behavior.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Nit**, **architecture**, [skills/implement/SKILL.md:1836-1945](skills/implement/SKILL.md): Step 18 is the last `<!-- step:*` marker in the file, so the awk “next step” exit rule never runs; the scan runs from that marker to EOF. This is consistent with current content and is not introduced by the test diff; called out only because future edits adding another `<!-- step:` inside Step 18 would change awk behavior.
- **Suggested revision**: Address the concern above.

### FINDING_77: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: None that are pre-existing defects in unchanged code; the manifest commit follows an established repo pattern (many similar trees under `larch-logs/implement/`), so it is not scored as a harness correctness bug.
- **Suggested revision**: Address the concern above.

### FINDING_78: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: None.
- **Suggested revision**: Address the concern above.

### FINDING_79: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: None.
- **Suggested revision**: Address the concern above.

### FINDING_80: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: None.
- **Suggested revision**: Address the concern above.

### FINDING_81: panel [code-review/accepted]

## [OUT_OF_SCOPE] `08170256` — Enforce finalize-state write guard in implement structure test  

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `08170256` — Enforce finalize-state write guard in implement structure test
- **Suggested revision**: Address the concern above.

### FINDING_82: panel [code-review/accepted]

## [OUT_OF_SCOPE] `4dc2d2da` — chore(larch-logs): flush implement run CEEF9367-14BA-4C4C-B26B-25D76D8A442B  

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `4dc2d2da` — chore(larch-logs): flush implement run CEEF9367-14BA-4C4C-B26B-25D76D8A442B  
- **Suggested revision**: Address the concern above.

### FINDING_83: panel [code-review/accepted]

## ```

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_84: panel [code-review/accepted]

## ```text

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_85: panel [code-review/accepted]

## ```tsv

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_86: panel [code-review/accepted]

## schema_version

- **Reviewer**: scope
- **Concern**: severity	focus_area	location	what	scenario_or_breakage	suggested_fix
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Commits:** `4dc2d2da chore(larch-logs): flush implement run CEEF9367-...` and `08170256 Enforce finalize-state write guard in implement structure test`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** (`risk-integration`) — [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-20. The same branch bundles an implement run manifest (`operator_cwd` / `operator_repo_root` set to `/Users/zhupanov/larch2`, `status: in-progress`) unrelated to the finalize-state harness. That couples noisy, machine-specific run metadata with a focused CI contract change, complicates review, and may conflict with how you expect implement logs to land. Drop or isolate that commit from the harness PR per repo log policy.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Important** (`risk-integration`) — [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-20. The same branch bundles an implement run manifest (`operator_cwd` / `operator_repo_root` set to `/Users/zhupanov/larch2`, `status: in-progress`) unrelated to the finalize-state harness. That couples noisy, machine-specific run metadata with a focused CI contract change, complicates review, and may conflict with how you expect implement logs to land. Drop or isolate that commit from the harness PR per repo log policy.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** (`risk-integration`, `plan` / `requirements`) — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (new `lib-finalize-state-keys.sh` checks in the reviewed diff, immediately before `echo "All assertions passed."`). The diff uses `grep -qF 'lib-finalize-state-keys.sh'` while the failure text says scripts must “source” the library. Both [`scripts/restore-finalize-state.sh`](scripts/restore-finalize-state.sh) and [`scripts/ship-pr.sh`](scripts/ship-pr.sh) already contain that substring inside `# shellcheck source=...lib-finalize-state-keys.sh` comments. A contributor could delete the real `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line and CI would still pass until runtime. Tighten the check to an uncommented `source`/`.` line (or otherwise ignore comment-only matches), matching the feature text (“sourced by both”).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`, `plan` / `requirements`) — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (new `lib-finalize-state-keys.sh` checks in the reviewed diff, immediately before `echo "All assertions passed."`). The diff uses `grep -qF 'lib-finalize-state-keys.sh'` while the failure text says scripts must “source” the library. Both [`scripts/restore-finalize-state.sh`](scripts/restore-finalize-state.sh) and [`scripts/ship-pr.sh`](scripts/ship-pr.sh) already contain that substring inside `# shellcheck source=...lib-finalize-state-keys.sh` comments. A contributor could delete the real `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line and CI would still pass until runtime. Tighten the check to an uncommented `source`/`.` line (or otherwise ignore comment-only matches), matching the feature text (“sourced by both”).
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** `code-quality` [scripts/test-implement-structure.sh:102](/Users/zhupanov/larch2/scripts/test-implement-structure.sh:102) — The new “must source `lib-finalize-state-keys.sh`” assertions only grep for the filename, so they pass on comments like `# shellcheck source=scripts/lib-finalize-state-keys.sh` even if the real `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line is removed. Concrete failing scenario: delete the source line but leave the shellcheck comment in `scripts/restore-finalize-state.sh:44-45` or `scripts/ship-pr.sh:19-20`; `scripts/test-implement-structure.sh:102-105` still passes, so CI does not enforce assertion (4). Match an actual source/dot command instead, for example `grep -qE '^[[:space:]]*(source|\\.)[[:space:]].*lib-finalize-state-keys\\.sh'`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `code-quality` [scripts/test-implement-structure.sh:102](/Users/zhupanov/larch2/scripts/test-implement-structure.sh:102) — The new “must source `lib-finalize-state-keys.sh`” assertions only grep for the filename, so they pass on comments like `# shellcheck source=scripts/lib-finalize-state-keys.sh` even if the real `source "$SCRIPT_DIR/lib-finalize-state-keys.sh"` line is removed. Concrete failing scenario: delete the source line but leave the shellcheck comment in `scripts/restore-finalize-state.sh:44-45` or `scripts/ship-pr.sh:19-20`; `scripts/test-implement-structure.sh:102-105` still passes, so CI does not enforce assertion (4). Match an actual source/dot command instead, for example `grep -qE '^[[:space:]]*(source|\\.)[[:space:]].*lib-finalize-state-keys\\.sh'`.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Important** · **risk-integration** · [larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) (new file) · The branch diff adds a committed implement-run `manifest.json` with operator paths, issue number, and in-progress status, which is not mentioned in the [feature_description](feature_description) or [implementation_plan](implementation_plan) (those only name `test-implement-structure.sh` / `.md`). Reviewers and CI consumers expecting a narrowly scoped “finalize-state test assertions” PR get unrelated run-log state and extra merge noise. **Suggested fix:** Drop that commit from the PR or split it to a separate branch; keep this PR limited to the harness + doc per plan.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** · **risk-integration** · [larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json) (new file) · The branch diff adds a committed implement-run `manifest.json` with operator paths, issue number, and in-progress status, which is not mentioned in the [feature_description](feature_description) or [implementation_plan](implementation_plan) (those only name `test-implement-structure.sh` / `.md`). Reviewers and CI consumers expecting a narrowly scoped “finalize-state test assertions” PR get unrelated run-log state and extra merge noise. **Suggested fix:** Drop that commit from the PR or split it to a separate branch; keep this PR limited to the harness + doc per plan.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Important** — `risk-integration` — [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-26 — The branch adds a committed implement run manifest (`operator_cwd` / `operator_repo_root` under `/Users/zhupanov/...`, `status: in-progress`, `issue_number`, etc.), which is unrelated to the finalize-state harness and looks like session/run output rather than product source. **Concrete scenario:** This merges into `main` and permanently stores a developer-local path and a specific run id in the tree, increasing noise and risking policy/CI expectations around `larch-logs/`. **Suggested fix:** Remove this file from the PR (or replace with whatever the repo’s run-log contract actually requires) so the change set only contains the structural-test work.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Important** — `risk-integration` — [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-26 — The branch adds a committed implement run manifest (`operator_cwd` / `operator_repo_root` under `/Users/zhupanov/...`, `status: in-progress`, `issue_number`, etc.), which is unrelated to the finalize-state harness and looks like session/run output rather than product source. **Concrete scenario:** This merges into `main` and permanently stores a developer-local path and a specific run id in the tree, increasing noise and risking policy/CI expectations around `larch-logs/`. **Suggested fix:** Remove this file from the PR (or replace with whatever the repo’s run-log contract actually requires) so the change set only contains the structural-test work.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Important**, `risk-integration`, [larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-20 — The branch adds a **second** commit that only introduces this manifest under a new run id, with `status: "in-progress"`, `pr_number: null`, and `operator_cwd` / `operator_repo_root` set to a developer-local absolute path. That is unrelated to the finalize-state structure-test work and is not a complete committed run like the existing fixture tree on `main` (for example [larch-logs/implement/00A7A5AB-F063-45A4-AE92-6248CB151F9F/](larch-logs/implement/00A7A5AB-F063-45A4-AE92-6248CB151F9F/), which includes the full batch set and a terminal `done` manifest). **Concrete impact:** reviewers and future automation see a dangling, mid-run directory in the canonical repo, mixed into a PR whose stated goal is CI assertions for `finalize-state`; it adds noise and provenance churn without delivering the usual flushed batch artifacts. **Suggested fix:** drop that commit or move the flush to a separate PR; if the intent is a new fixture, add the full expected batch set and a coherent terminal `status` per [docs/run-logs.md](docs/run-logs.md).

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important**, `risk-integration`, [larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-20 — The branch adds a **second** commit that only introduces this manifest under a new run id, with `status: "in-progress"`, `pr_number: null`, and `operator_cwd` / `operator_repo_root` set to a developer-local absolute path. That is unrelated to the finalize-state structure-test work and is not a complete committed run like the existing fixture tree on `main` (for example [larch-logs/implement/00A7A5AB-F063-45A4-AE92-6248CB151F9F/](larch-logs/implement/00A7A5AB-F063-45A4-AE92-6248CB151F9F/), which includes the full batch set and a terminal `done` manifest). **Concrete impact:** reviewers and future automation see a dangling, mid-run directory in the canonical repo, mixed into a PR whose stated goal is CI assertions for `finalize-state`; it adds noise and provenance churn without delivering the usual flushed batch artifacts. **Suggested fix:** drop that commit or move the flush to a separate PR; if the intent is a new fixture, add the full expected batch set and a coherent terminal `status` per [docs/run-logs.md](docs/run-logs.md).
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Latent** (`risk-integration`, `plan`) — [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md) (new finalize-state paragraph in the diff). The prose claims “source references from restore and ship-pr,” but the diff’s substring-only `grep -qF` does not actually prove sourcing once comments satisfy the pattern. Align wording with the enforced predicate or strengthen the assertion (same fix as finding 1).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Latent** (`risk-integration`, `plan`) — [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md) (new finalize-state paragraph in the diff). The prose claims “source references from restore and ship-pr,” but the diff’s substring-only `grep -qF` does not actually prove sourcing once comments satisfy the pattern. Align wording with the enforced predicate or strengthen the assertion (same fix as finding 1).
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Latent** · **correctness** · [feature_description](feature_description) clause (4) vs [scripts/test-implement-structure.sh](scripts/test-implement-structure.sh) · The feature text ties `ship-pr.sh` to `write_finalize_state`; the test matches the implementation_plan’s weaker `grep -qF` over the whole script (which is satisfied by the existing top-level `source` and is practically sufficient today). **Scenario:** A future edit could remove the top-level `source` while leaving the filename only in a comment or dead block; the test could still pass. **Suggested fix:** If you need literal alignment with the feature line, anchor a check to `write_finalize_state()`’s region or assert a `source …lib-finalize-state-keys` before the function definition.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. **Latent** · **correctness** · [feature_description](feature_description) clause (4) vs [scripts/test-implement-structure.sh](scripts/test-implement-structure.sh) · The feature text ties `ship-pr.sh` to `write_finalize_state`; the test matches the implementation_plan’s weaker `grep -qF` over the whole script (which is satisfied by the existing top-level `source` and is practically sufficient today). **Scenario:** A future edit could remove the top-level `source` while leaving the filename only in a comment or dead block; the test could still pass. **Suggested fix:** If you need literal alignment with the feature line, anchor a check to `write_finalize_state()`’s region or assert a `source …lib-finalize-state-keys` before the function definition.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## **Latent** · **risk-integration** · [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (new block ~52–105 vs `main`) · The feature text ties assertion (d) to `ship-pr.sh`’s `write_finalize_state`, but the branch only asserts a top-level `source`/`.` line loading `lib-finalize-state-keys.sh`. A future refactor could keep that `source` while moving or gutting `write_finalize_state` so finalize-state keys no longer flow from the shared helper, and CI would still pass. Tighten the harness with a targeted grep on `write_finalize_state` (definition body or call path) if that coupling is meant to be load-bearing.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Latent** · **risk-integration** · [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (new block ~52–105 vs `main`) · The feature text ties assertion (d) to `ship-pr.sh`’s `write_finalize_state`, but the branch only asserts a top-level `source`/`.` line loading `lib-finalize-state-keys.sh`. A future refactor could keep that `source` while moving or gutting `write_finalize_state` so finalize-state keys no longer flow from the shared helper, and CI would still pass. Tighten the harness with a targeted grep on `write_finalize_state` (definition body or call path) if that coupling is meant to be load-bearing.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## **Latent** — `correctness` — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (diff-added NEVER `grep -qE` line, immediately after the `Larch-log batches` checks in the same hunk) — The ERE uses an unescaped `.` before `\$IMPLEMENT_TMPDIR`, so it matches **any** single character there, not strictly a literal dot or the documented `` ` `` wrapper. **Concrete scenario:** A mistaken edit that inserts a different single character before `$IMPLEMENT_TMPDIR` while keeping the rest of the substring could still satisfy the harness even though the NEVER bullet text no longer matches the intended contract. **Suggested fix:** Anchor the segment literally (e.g. `\.` and/or the backtick-wrapped form that `SKILL.md` actually uses) so the check matches the real bullet shape.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Latent** — `correctness` — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (diff-added NEVER `grep -qE` line, immediately after the `Larch-log batches` checks in the same hunk) — The ERE uses an unescaped `.` before `\$IMPLEMENT_TMPDIR`, so it matches **any** single character there, not strictly a literal dot or the documented `` ` `` wrapper. **Concrete scenario:** A mistaken edit that inserts a different single character before `$IMPLEMENT_TMPDIR` while keeping the rest of the substring could still satisfy the harness even though the NEVER bullet text no longer matches the intended contract. **Suggested fix:** Anchor the segment literally (e.g. `\.` and/or the backtick-wrapped form that `SKILL.md` actually uses) so the check matches the real bullet shape.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## **Latent** — `correctness` — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (diff-added `awk` fence opener `^```bash`) — Only fenced blocks labeled exactly `bash` are scanned for restore/teardown order. **Concrete scenario:** Step 18 is refactored to an equivalent ` ```sh ` (or `shell`) fence while keeping the same commands; the harness reports “restore-finalize-state.sh not found in Step 18 region” even though order is correct. **Suggested fix:** Treat the same set of shell fences the skill uses (e.g. `bash|sh|shell`) or match the repo’s existing convention from other harnesses.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 4. **Latent** — `correctness` — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (diff-added `awk` fence opener `^```bash`) — Only fenced blocks labeled exactly `bash` are scanned for restore/teardown order. **Concrete scenario:** Step 18 is refactored to an equivalent ` ```sh ` (or `shell`) fence while keeping the same commands; the harness reports “restore-finalize-state.sh not found in Step 18 region” even though order is correct. **Suggested fix:** Treat the same set of shell fences the skill uses (e.g. `bash|sh|shell`) or match the repo’s existing convention from other harnesses.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## **Latent** — `correctness` — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (diff-added `grep -qF 'lib-finalize-state-keys.sh'` on `restore-finalize-state.sh` and `ship-pr.sh`) — Failure messages say the scripts “must **source**” the library, but `-qF` only proves the filename appears somewhere in the file (comment, string, dead branch), not a top-level `source`/`.` line. **Concrete scenario:** Someone removes the real `source` line and adds a harmless comment containing `lib-finalize-state-keys.sh`; CI stays green while the runtime contract breaks. **Suggested fix:** Match a real source line (as in a `^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh`-style check) or otherwise assert load semantics.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **Latent** — `correctness` — [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (diff-added `grep -qF 'lib-finalize-state-keys.sh'` on `restore-finalize-state.sh` and `ship-pr.sh`) — Failure messages say the scripts “must **source**” the library, but `-qF` only proves the filename appears somewhere in the file (comment, string, dead branch), not a top-level `source`/`.` line. **Concrete scenario:** Someone removes the real `source` line and adds a harmless comment containing `lib-finalize-state-keys.sh`; CI stays green while the runtime contract breaks. **Suggested fix:** Match a real source line (as in a `^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh`-style check) or otherwise assert load semantics.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## **Latent**, `correctness`, [scripts/test-implement-structure.sh](scripts/test-implement-structure.sh):54-56 — The NEVER check uses the ERE fragment `modify .\$IMPLEMENT_TMPDIR` (exactly one character between `modify` and `$`). Today’s NEVER #13 line uses a Markdown backtick before `$`, so it matches. **Concrete impact:** If someone later edits NEVER #13 to use plain `` `$IMPLEMENT_TMPDIR/...` `` without any character between `modify` and `$` (or otherwise tightens wording), CI fails even though the prohibition is still clearly stated. **Suggested fix:** relax to `modify.?\\\$IMPLEMENT_TMPDIR` (or match a short literal substring from the skill text) so small editorial reflows do not false-fail.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Latent**, `correctness`, [scripts/test-implement-structure.sh](scripts/test-implement-structure.sh):54-56 — The NEVER check uses the ERE fragment `modify .\$IMPLEMENT_TMPDIR` (exactly one character between `modify` and `$`). Today’s NEVER #13 line uses a Markdown backtick before `$`, so it matches. **Concrete impact:** If someone later edits NEVER #13 to use plain `` `$IMPLEMENT_TMPDIR/...` `` without any character between `modify` and `$` (or otherwise tightens wording), CI fails even though the prohibition is still clearly stated. **Suggested fix:** relax to `modify.?\\\$IMPLEMENT_TMPDIR` (or match a short literal substring from the skill text) so small editorial reflows do not false-fail.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## **Nit** · **architecture** · [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-20 · The same branch carries a flushed implement manifest with `"status": "in-progress"` and `"pr_number": null`, bundled alongside the structural-test change. That mixes an incomplete run snapshot with policy enforcement and may add review noise unless flushing mid-run manifests to `main` is routine for your workflow.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Nit** · **architecture** · [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-20 · The same branch carries a flushed implement manifest with `"status": "in-progress"` and `"pr_number": null`, bundled alongside the structural-test change. That mixes an incomplete run snapshot with policy enforcement and may add review noise unless flushing mid-run manifests to `main` is routine for your workflow.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## **Nit** · **correctness** · (Applies only if the branch is still exactly as in **stale** `diff.txt`, not current `HEAD`.) · [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (per cached diff hunks for the `lib-finalize-state-keys` checks) · `grep -qF 'lib-finalize-state-keys.sh'` is satisfied by a lingering `# shellcheck source=…lib-finalize-state-keys.sh` comment even if the real `source` line were removed. Current `HEAD` vs `main` already replaces this with a `source`/`.` line anchored regex, which closes that hole.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Nit** · **correctness** · (Applies only if the branch is still exactly as in **stale** `diff.txt`, not current `HEAD`.) · [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (per cached diff hunks for the `lib-finalize-state-keys` checks) · `grep -qF 'lib-finalize-state-keys.sh'` is satisfied by a lingering `# shellcheck source=…lib-finalize-state-keys.sh` comment even if the real `source` line were removed. Current `HEAD` vs `main` already replaces this with a `source`/`.` line anchored regex, which closes that hole.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## **Nit** · **correctness** · [scripts/test-implement-structure.sh](scripts/test-implement-structure.sh) (new `grep -qF 'lib-finalize-state-keys.sh'` checks) · Failure strings say scripts “must **source**” the library, but the checks only require the substring `lib-finalize-state-keys.sh` anywhere in the file (as the implementation_plan specifies). **Suggested fix:** Align wording with behavior (“must reference …”) or tighten the pattern to `source` lines if you want the message to stay literal.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Nit** · **correctness** · [scripts/test-implement-structure.sh](scripts/test-implement-structure.sh) (new `grep -qF 'lib-finalize-state-keys.sh'` checks) · Failure strings say scripts “must **source**” the library, but the checks only require the substring `lib-finalize-state-keys.sh` anywhere in the file (as the implementation_plan specifies). **Suggested fix:** Align wording with behavior (“must reference …”) or tighten the pattern to `source` lines if you want the message to stay literal.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## **Nit** · **risk-integration** · Review input hygiene · The precomputed `round-2/diff.txt` still shows `grep -qF 'lib-finalize-state-keys.sh'` and `awk` opening only `^```bash`; `git diff main...HEAD` now uses `grep -qE '^[[:space:]]*(source|\.)…'` and opens `bash|sh|shell` fences. Anyone judging only the stale sidecar can file outdated critique on sourcing strength or missed `sh` fences.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Nit** · **risk-integration** · Review input hygiene · The precomputed `round-2/diff.txt` still shows `grep -qF 'lib-finalize-state-keys.sh'` and `awk` opening only `^```bash`; `git diff main...HEAD` now uses `grep -qE '^[[:space:]]*(source|\.)…'` and opens `bash|sh|shell` fences. Anyone judging only the stale sidecar can file outdated critique on sourcing strength or missed `sh` fences.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## **Nit** — `correctness` / **Completeness w.r.t. plan** — [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md):36-44 — The doc update summarizes the four themes in one paragraph but does not spell out the individual assertions or failure strings the feature description called “document the new assertions.” **Suggested fix:** Add a short bullet list mapping assertion → what it enforces (optional if prose is enough for your team).

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 5. **Nit** — `correctness` / **Completeness w.r.t. plan** — [`scripts/test-implement-structure.md`](scripts/test-implement-structure.md):36-44 — The doc update summarizes the four themes in one paragraph but does not spell out the individual assertions or failure strings the feature description called “document the new assertions.” **Suggested fix:** Add a short bullet list mapping assertion → what it enforces (optional if prose is enough for your team).
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## **Nit**, `correctness`, [scripts/test-implement-structure.sh](scripts/test-implement-structure.sh):87-93 — The `*)` branch of the Step 18 order `case` maps every unexpected `awk` exit code to the same “unexpected … failure” string. **Concrete impact:** True `awk` I/O or internal errors surface with a message that reads like a contract violation. **Suggested fix:** include the numeric exit code (already interpolated) in a wording that distinguishes “awk aborted” from “ordering contract failed,” or map a small set of known failure codes.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **Nit**, `correctness`, [scripts/test-implement-structure.sh](scripts/test-implement-structure.sh):87-93 — The `*)` branch of the Step 18 order `case` maps every unexpected `awk` exit code to the same “unexpected … failure” string. **Concrete impact:** True `awk` I/O or internal errors surface with a message that reads like a contract violation. **Suggested fix:** include the numeric exit code (already interpolated) in a wording that distinguishes “awk aborted” from “ordering contract failed,” or map a small set of known failure codes.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## **Read-only constraint:** No files were written. The instructions asked for a TSV sidecar on disk; that is omitted here. Tab-separated records are given at the end in a fenced block you can save manually if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## **Read-only constraint:** No files were written. The instructions asked for a `.tsv` sidecar file; that would mutate the workspace, so structured rows appear only in the fenced block at the end for optional manual materialization.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## **Sidecar TSV** (not written to disk — read-only session). Records use literal tabs between fields:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## **TSV (sidecar content; not written to disk in this read-only session)**

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## **TSV records** (sidecar not written — read-only):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## **`**Important**` · `risk-integration` · [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-20** — The branch diff adds a new `larch-logs/implement/.../manifest.json` with `status: "in-progress"`, issue `2177`, and local `operator_*` paths, in the same change set as the finalize-state structure-test work described in `<feature_description>`. That couples an unrelated implement “flush” artefact to a CI-harness PR, adds noise for reviewers and consumers of the plugin tree, and publishes a mid-run manifest without the rest of the run directory content shown in the diff hunk. **Suggested fix:** Drop this commit from the branch or land the log flush in a separate PR; keep this PR scoped to `scripts/test-implement-structure.sh` and `scripts/test-implement-structure.md` unless the tracking workflow explicitly requires committing this run.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **`**Important**` · `risk-integration` · [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):1-20** — The branch diff adds a new `larch-logs/implement/.../manifest.json` with `status: "in-progress"`, issue `2177`, and local `operator_*` paths, in the same change set as the finalize-state structure-test work described in `<feature_description>`. That couples an unrelated implement “flush” artefact to a CI-harness PR, adds noise for reviewers and consumers of the plugin tree, and publishes a mid-run manifest without the rest of the run directory content shown in the diff hunk. **Suggested fix:** Drop this commit from the branch or land the log flush in a separate PR; keep this PR scoped to `scripts/test-implement-structure.sh` and `scripts/test-implement-structure.md` unless the tracking workflow explicitly requires committing this run.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## **`**Nit**` · `code-quality` · [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (NEVER bullet `grep -qE`, new block ~lines 102–104 in patched file)** — The ERE uses `.` before `\$IMPLEMENT_TMPDIR`, so any single character satisfies that slot, not necessarily the markdown/backtick framing the skill uses today. **Suggested fix:** If you want a stricter pin, match the literal substring with `grep -F` / fixed-string span or enumerate the allowed prefix character(s).

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **`**Nit**` · `code-quality` · [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) (NEVER bullet `grep -qE`, new block ~lines 102–104 in patched file)** — The ERE uses `.` before `\$IMPLEMENT_TMPDIR`, so any single character satisfies that slot, not necessarily the markdown/backtick framing the skill uses today. **Suggested fix:** If you want a stricter pin, match the literal substring with `grep -F` / fixed-string span or enumerate the allowed prefix character(s).
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## ---

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## 08170256 Enforce finalize-state write guard in implement structure test

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json	Implement run manifest added on the same branch as the planned harness-only change; not in feature_description or implementation_plan.	PR scope and review surface include operator cwd paths, issue 2177 linkage, and in-progress run metadata unrelated to finalize-state assertions; reviewers cannot trace this to the stated plan.	Omit or move the larch-logs flush commit so the branch matches the documented deliverables.
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20	Committed in-progress implement manifest with local operator paths bundled with unrelated structure-test changes	Couples finalize-state CI harness PR to run flush noise; ships mid-run state not requested in feature_description	Remove or split the larch-logs commit; scope PR to test scripts/docs unless flush is explicitly required
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20	Unrelated implement manifest with absolute operator paths bundled in PR	PR mixes session metadata with harness change; noisy and machine-specific	Split or drop larch-logs commit from harness PR
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	scripts/test-implement-structure.sh:100-105	lib-finalize-state-keys check uses substring grep -qF per reviewed diff	Filename appears in shellcheck source comments; real source line can be removed while CI passes	Require uncommented source/. line or stricter pattern; align failure message with predicate
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk_integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20	Unrelated in-progress implement manifest with local operator_cwd paths committed as its own commit beside structure-test changes.	Dangling mid-run directory without companion batches; reviewers conflate with intentional fixtures; PR scope mixes operational flush with CI harness work.	Remove or split the larch-logs commit; complete fixture set and terminal status if intentional.
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk_integration	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-26	Unrelated implement run manifest committed with local paths and in-progress status	Merges machine-specific run metadata into the product repo; unrelated noise and possible larch-logs policy mismatch	Remove from PR or align with committed run-log contract; keep PR scoped to harness changes
- **Suggested revision**: Address the concern above.

### FINDING_36: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	scripts/test-implement-structure.sh (diff-added NEVER grep line)	ERE uses '.' so any one character matches before $IMPLEMENT_TMPDIR	A cosmetically wrong NEVER line could still pass the substring-shaped check	Use literal/escaped tokens matching SKILL.md's actual NEVER bullet
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	scripts/test-implement-structure.sh (diff-added awk bash fence)	Only ```bash fences are scanned for Step 18 order	Refactor to ```sh would false-fail despite correct command order	Accept bash|sh|shell fences or match repo markdown convention
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	scripts/test-implement-structure.sh (diff-added grep -qF lib-finalize-state-keys.sh)	Message claims 'must source' but -qF only requires substring presence	A comment containing the filename could satisfy CI without a real source line	Assert a real source/dot line or equivalent load contract
- **Suggested revision**: Address the concern above.

### FINDING_39: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	scripts/test-implement-structure.sh vs feature_description (4)	Feature mentions ship-pr.sh write_finalize_state; test follows implementation_plan file-wide substring grep.	Theoretically the string could remain in a comment after removing real sourcing; write_finalize_state could drift without failing the new check.	Optional: anchor verification to write_finalize_state or require a source line pattern.
- **Suggested revision**: Address the concern above.

### FINDING_40: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	scripts/test-implement-structure.sh:54-56	NEVER regex requires exactly one character before $IMPLEMENT_TMPDIR.	Reformatting NEVER #13 to remove the backtick (or other single-char gap) makes the harness fail while semantics unchanged.	Use modify.? before \$ or match a stable longer literal.
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	scripts/test-implement-structure.md:36-44	Doc claims source references	Doc overstates vs substring-only test	Strengthen test or soften doc to match enforcement
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	scripts/test-implement-structure.sh:52-105	Assertion (d) does not pin ship-pr.sh write_finalize_state to lib-finalize-state-keys	write_finalize_state could diverge from the shared key helper while source line remains	Anchor a grep (or small parser) on write_finalize_state body/calls for lib usage
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	architecture	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:1-20	In-progress implement manifest committed alongside harness change	Extra review surface; possible consumer confusion about terminal vs partial runs	Flush only terminal manifests or document mid-run flush policy
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	scripts/test-implement-structure.sh:102-104	NEVER bullet check uses ERE . before $IMPLEMENT_TMPDIR	Contrived SKILL edits could pass without preserving intended framing	Tighten to literal / fixed-string match on the documented NEVER line
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	scripts/test-implement-structure.md:36-44	Docs name themes but not per-assertion detail	Readers cannot map failures to assertion IDs without reading the shell script	Add bullets for each assertion/failure message
- **Suggested revision**: Address the concern above.

### FINDING_46: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	scripts/test-implement-structure.sh	Failure messages claim scripts must source lib-finalize-state-keys.sh but grep only requires the filename substring.	Messages overstate the guarantee relative to the actual check; minor confusion during CI triage.	Rename messages to match substring checks or strengthen the grep to source lines.
- **Suggested revision**: Address the concern above.

### FINDING_47: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	scripts/test-implement-structure.sh (stale diff only)	grep -qF lib-finalize-state-keys weaker than sourced-by contract	Comment-only satisfy	Already addressed on HEAD with source|. regex
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	scripts/test-implement-structure.sh:87-93	Catch-all maps any awk exit to generic contract-failure wording.	Awk runtime failures look like Step 18 ordering bugs.	Clarify message for non-10/11/12 exits or surface awk stderr.
- **Suggested revision**: Address the concern above.

### FINDING_49: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	review-sidecar:round-2/diff.txt	Stale precomputed diff disagrees with git diff main...HEAD for test-implement-structure.sh	Stale findings from cached diff	Regenerate sidecar or review git diff directly
- **Suggested revision**: Address the concern above.

### FINDING_50: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk_integration	scripts/test-implement-structure.sh:68-105	Working tree already differs from cached diff (stronger checks)	Review based solely on diff.txt may miss final merged behavior	Re-run structural review on the final branch diff before merge
- **Suggested revision**: Address the concern above.

### FINDING_51: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	security	larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json:6-7	Absolute paths in manifest	Documented provenance fields per docs/run-logs.md	None unless policy changes
- **Suggested revision**: Address the concern above.

### FINDING_52: panel [code-review/accepted]

## 4dc2d2da chore(larch-logs): flush implement run CEEF9367-14BA-4C4C-B26B-25D76D8A442B

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_53: panel [code-review/accepted]

## Commits on branch since `merge-base` with `main`: `08170256` (implement structure test + docs) and `4dc2d2da` (larch-logs implement manifest flush). Plan-aligned work is in the first commit; the diff bundles both.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_54: panel [code-review/accepted]

## HARD CONSTRAINT: no file writes, so the TSV sidecar was not written to disk. Records below are the sidecar content you can save as `diff.txt.tsv` (or your pipeline’s path) if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_55: panel [code-review/accepted]

## Note: the cached `diff.txt` you pointed at is slightly behind the current branch (for example it showed `grep -qF` for the lib key checks, while `git diff main` now shows anchored `grep -qE` source lines and ` ```(bash|sh|shell)` fences). The review below uses the current branch vs `main` (`git diff main` + file reads).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_56: panel [code-review/accepted]

## Note: your read-only constraint forbids writing the `.tsv` sidecar file; TSV rows appear at the end in a separate block for you to redirect if needed. The cached diff still shows `grep -qF` for the library checks; your working tree may already differ (see out-of-scope note).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_57: panel [code-review/accepted]

## Read-only constraint: no sidecar file was written; TSV lines are included at the end for you to persist if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_58: panel [code-review/accepted]

## Read-only constraint: the review template asked for a `.tsv` sidecar on disk; that was not written (no file mutations). Below is the same structured content for copy/paste if your pipeline expects a sidecar file.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_59: panel [code-review/accepted]

## Review is based on the precomputed diff at `<TMPDIR>/round-2/diff.txt` and the referenced repo paths for behavior context. The working tree’s [`scripts/test-implement-structure.sh`](/Users/zhupanov/larch2/scripts/test-implement-structure.sh) currently differs from that diff (e.g. shell fence regex and `lib-finalize-state-keys` checks); findings below target **what the cached diff adds**, not unshown local edits.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_60: panel [code-review/accepted]

## Reviewed [round-2 `diff.txt`](file:///Users/zhupanov/.cache/larch/sessions/claude-implement-larch2-27Ek6E/round-2/diff.txt) as the source of truth. Commits on branch since merge-base with `main`:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_61: panel [code-review/accepted]

## Reviewed the precomputed [`diff.txt`](<TMPDIR>/round-2/diff.txt) and reconciled against `git diff main...HEAD` for the current branch tip (they differ on the sourcing checks and fenced-code detection in `scripts/test-implement-structure.sh`).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_62: panel [code-review/accepted]

## Reviewed the precomputed diff, commit list, and relevant sections of [`skills/implement/SKILL.md`](skills/implement/SKILL.md) (Step 18 and NEVER #13) plus [`scripts/restore-finalize-state.sh`](scripts/restore-finalize-state.sh) / [`scripts/ship-pr.sh`](scripts/ship-pr.sh) for the lib source checks.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_63: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: Gathering the branch diff, commit list, and targeted file reads to verify correctness against the feature description and plan.
- **Suggested revision**: Address the concern above.

### FINDING_64: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Gathering the branch diff and commit history for a read-only review. We won't write the TSV sidecar (hard read-only constraint); we'll include TSV lines in the response if needed.
- **Suggested revision**: Address the concern above.

### FINDING_65: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Gathering the diff and commit history (read-only `git log`/`merge-base`) to verify plan fidelity.
- **Suggested revision**: Address the concern above.

### FINDING_66: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: Gathering the pre-computed diff and commit history for a read-only security-focused review. Skipping writing the TSV sidecar (hard constraint: no file mutations).
- **Suggested revision**: Address the concern above.

### FINDING_67: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Gathering the pre-computed diff and commit history for a read-only review. We won't write the TSV sidecar (read-only constraint); we'll include structured TSV records in the response if needed.
- **Suggested revision**: Address the concern above.

### FINDING_68: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: Gathering the diff and commit history for a read-only review. We won't write files (including the TSV sidecar) per your hard constraints; we'll include TSV lines in the response if needed.
- **Suggested revision**: Address the concern above.

### FINDING_69: panel [code-review/accepted]

## Verifying SKILL.md Step 18 structure and whether the new checks match the repo (plan fidelity).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_70: panel [code-review/accepted]

## Verifying Step 18 structure and whether `lib-finalize-state-keys.sh` is actually sourced (not only mentioned) in the referenced scripts.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_71: panel [code-review/accepted]

## Verifying Step 18 structure in SKILL.md and whether the grep/awk patterns match the real content.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_72: panel [code-review/accepted]

## Verifying Step 18 structure in SKILL.md and whether the larch-logs manifest belongs in the feature scope.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_73: panel [code-review/accepted]

## Verifying assertion patterns against the repo: checking SKILL.md for the NEVER bullet and Step 18 structure, and whether the larch-logs change belongs in the branch.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_74: panel [code-review/accepted]

## Verifying implementation against the repo: NEVER bullet wording, Step 18 structure, and whether `grep -qF 'lib-finalize-state-keys.sh'` matches actual `source` usage.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_75: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`risk-integration`) — The workspace copy of [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) already uses `grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh'`, which mitigates finding 1; the precomputed `diff.txt` still shows `grep -qF`. Confirm what actually ships on the branch before merge so the review artifact and `main` agree.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Nit** (`risk-integration`) — The workspace copy of [`scripts/test-implement-structure.sh`](scripts/test-implement-structure.sh) already uses `grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh'`, which mitigates finding 1; the precomputed `diff.txt` still shows `grep -qF`. Confirm what actually ships on the branch before merge so the review artifact and `main` agree.
- **Suggested revision**: Address the concern above.

### FINDING_76: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** — `risk-integration` — Current checkout of [`scripts/test-implement-structure.sh`](/Users/zhupanov/larch2/scripts/test-implement-structure.sh):68-105 — The tree on disk already tightens the cached diff (shell fence alternates; `source`-line regex for `lib-finalize-state-keys.sh`). That is **out of scope** for judging the provided `diff.txt` but means reviewers should re-run against the final branch diff before merge.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Nit** — `risk-integration` — Current checkout of [`scripts/test-implement-structure.sh`](/Users/zhupanov/larch2/scripts/test-implement-structure.sh):68-105 — The tree on disk already tightens the cached diff (shell fence alternates; `source`-line regex for `lib-finalize-state-keys.sh`). That is **out of scope** for judging the provided `diff.txt` but means reviewers should re-run against the final branch diff before merge.
- **Suggested revision**: Address the concern above.

### FINDING_77: panel [code-review/accepted]

## [OUT_OF_SCOPE] **security** · [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):6-7 · Absolute `operator_cwd` / `operator_repo_root` values look like local path disclosure, but [docs/run-logs.md](docs/run-logs.md) (around lines 35–36) documents schema v2 manifests as carrying local absolute paths for provenance and explicitly states they are not path-redacted. That is an existing product contract, not a new accidental leak introduced by this diff’s logic alone.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** · [`larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json`](larch-logs/implement/CEEF9367-14BA-4C4C-B26B-25D76D8A442B/manifest.json):6-7 · Absolute `operator_cwd` / `operator_repo_root` values look like local path disclosure, but [docs/run-logs.md](docs/run-logs.md) (around lines 35–36) documents schema v2 manifests as carrying local absolute paths for provenance and explicitly states they are not path-redacted. That is an existing product contract, not a new accidental leak introduced by this diff’s logic alone.
- **Suggested revision**: Address the concern above.

### FINDING_78: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: None worth filing here; the harness additions themselves are directionally sound (fenced-code-only Step 18 scan, executable bit, sibling docs, anchored `source`/`.` lines for the shared library).
- **Suggested revision**: Address the concern above.

### FINDING_79: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: None beyond noting that committed `larch-logs/**/manifest.json` trees appear to be an established repo pattern (many manifests exist); the issue here is **plan scope**, not whether the file type is foreign to the repository.
- **Suggested revision**: Address the concern above.

### FINDING_80: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: None.
- **Suggested revision**: Address the concern above.

### FINDING_81: panel [code-review/accepted]

## `08170256` Enforce finalize-state write guard in implement structure test  

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `08170256` Enforce finalize-state write guard in implement structure test  
- **Suggested revision**: Address the concern above.

### FINDING_82: panel [code-review/accepted]

## `4dc2d2da` chore(larch-logs): flush implement run CEEF9367-14BA-4C4C-B26B-25D76D8A442B  

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `4dc2d2da` chore(larch-logs): flush implement run CEEF9367-14BA-4C4C-B26B-25D76D8A442B
- **Suggested revision**: Address the concern above.

### FINDING_83: panel [code-review/accepted]

## ```

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_84: panel [code-review/accepted]

## ```text

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_85: panel [code-review/accepted]

## ```tsv

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_86: panel [code-review/accepted]

## `git log $(git merge-base HEAD main)..HEAD --oneline` (already run):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_87: panel [code-review/accepted]

## schema_version

- **Reviewer**: scope
- **Concern**: severity	focus_area	location	what	scenario_or_breakage	suggested_fix
- **Suggested revision**: Address the concern above.

