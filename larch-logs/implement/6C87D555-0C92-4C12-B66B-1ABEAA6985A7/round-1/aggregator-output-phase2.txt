Normalizing and merging the supplied reviewer findings into one structured list (read-only; no file or repo changes).
### FINDING_1: compose_prompt excerpt mktemp failure bypasses fail_status / LINT_FIX_STATUS
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under `set -e`, `compose_prompt` returns 1 when excerpt `mktemp` fails (e.g. `/tmp` exhaustion at lines 145–146) and the top-level caller invokes it without `fail_status` (line 526). The script exits with bare status 1 and no `LINT_FIX_STATUS=failed`, so upstream implement/ship-pr logic cannot classify the failure.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_2: Generic slash-path grep pollutes ## In-scope files
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The fifth grep pattern (line 111) matches generic `dir/file` tokens anywhere in the excerpt. Any log mention of an existing but unrelated path (e.g. prose referencing `scripts/relevant-checks.sh` while the failure is in `scripts/lint-fix-loop.sh`) can land in `## In-scope files` and misdirect the external coder despite log-scoped `fix_sentence`. Narrow or remove the slash-only pattern; rely on shellcheck, `path:line`, and extension patterns, or gate the broad regex behind empty results from stricter extractors.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_3: affected_files_from_log errors swallowed in process substitution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Inside `compose_prompt`, `affected_files_from_log` runs in a process substitution (lines 150–153) while failures there may not abort under `set -e`. `mktemp` failure or other extractor errors can yield an empty `affected_list` and the empty-list `fix_sentence` without surfacing parse failure, so Codex may miss in-scope paths and anti-cascade guidance even when the log shows concrete shellcheck paths.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_4: Missing test for phase-gated absence of optional pre-commit hint
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No harness case asserts that optional pre-commit verification is suppressed for agent-lint or direct-make phases. A regression could re-enable pre-commit hints on non-pre-commit failures while existing cases (e.g. Case 12) still pass, leading coders to run scoped pre-commit and hit whole-repo hooks. Add a case with `=== Running agent-lint ===` (or direct-make banner) plus a parseable `In … line …` failure; assert in-scope list present and optional pre-commit block absent.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_5: Shellcheck `In [^ ]+` pattern misses paths with spaces
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `In [^ ]+ line` regex (line 99) cannot extract paths containing spaces. A failure like `In my dir/foo.sh line 1:` appears in `## Checks Log` but not in `## In-scope files`, weakening scoping. Add a quoted-path shellcheck pattern or `path:line` extraction after stripping quotes, or document intentional under-match for spaced paths.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_6: Leading-slash paths always rejected
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_lint_fix_path_safety_ok` rejects any path starting with `/` (lines 62–71). Shellcheck output such as `In /abs/repo/scripts/foo.sh line 1` yields empty in-scope despite a visible error. Strip `REPO_ROOT` prefix and keep a repo-relative path when the file exists under the repo.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_7: Symlink paths accepted into in-scope list
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Repo-relative symlink paths pass `_lint_fix_path_safety_ok` via `[[ -f ]]` without rejecting `-L`. A symlink listed from a checks log can appear under `## In-scope files`, and the external coder may read/write through the symlink target. Reject `[[ -L "$root/$path" ]]` or require `realpath` stays under `REPO_ROOT` before listing a path in-scope.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_8: 50-path cap drops extras without notice
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `LINT_FIX_AFFECTED_FILES_CAP` default (50, line 123) silently truncates distinct failing paths in large excerpts. The prompt omits some failure paths while the parent loop may iterate on remaining issues. Note truncation in the prompt or raise the cap with a documented bound.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_9: Phase inference uses last banner, not failure context
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `infer_failure_phase_from_log` (lines 127–137) sets phase from the last matching banner in the excerpt, not from failure context. An agent-lint failure followed by a pre-commit banner in the tail can incorrectly enable the optional pre-commit hint. Infer phase from the banner nearest the first failure or first extracted path.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_10: Duplicated 60000-byte cap and embed sed
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The 60000-byte cap and `wc -c` logic are duplicated; embed paths use identical `sed` in both branches (lines 78–79, 144, 212–218). Future cap changes can drift between excerpt, banner, and parsers. Use a single named constant, pass `log_bytes` into `checks_log_excerpt`, and one `sed` embed path with conditional banner.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_11: checks_log_excerpt stdout/cat branches unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `checks_log_excerpt` stdout/`cat` branches (lines 75–89) have no callers; dead API surface increases review burden. Keep dest-file-only API unless a test needs stdout mode.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_12: tail -c excerpt may split UTF-8 or mid-line
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `tail -c 60000` (line 81) may start the excerpt mid-UTF-8 sequence or mid-line. Truncated logs at non-ASCII paths can cause parsers to miss paths at the window edge and omit optional blocks incorrectly. Strip the first partial line after byte tail or truncate by line budget.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_13: [OUT_OF_SCOPE] compose_prompt mktemp failure without LINT_FIX_STATUS KV
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Same excerpt `mktemp` failure class as in-scope FINDING_1, flagged out of scope for this review pass: rare temp failure aborts with generic exit 1 only instead of `fail_status` with a dedicated `FAILURE_REASON` (e.g. `prompt-excerpt-failed`).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_14: [OUT_OF_SCOPE] concatenated multi-run logs could mis-infer phase
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Not introduced by this branch; `scripts/relevant-checks.sh` unchanged (lines 317–322). Concatenated multi-run logs could mis-infer phase; address only if the capture layer appends multiple runs.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_15: [OUT_OF_SCOPE] committed implement run-log tree outside plan scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `larch-logs/implement/6C87D555-…` — committed run-log tree from `/implement` is outside this feature’s plan scope; per review policy, not treated as plan drift.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_16: [OUT_OF_SCOPE] Case 15 fixtures weaker than plan “on-disk fixture” wording
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan Case 15 describes on-disk fixtures with backtick/leading-dash names; the harness only places those strings in the checks log (filters still exercised). Acceptable for prompt-composition coverage; slightly weaker than plan fixture wording.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_17: [OUT_OF_SCOPE] spaced-path edge case and acceptance runs not executed
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `In [^ ]+ line` cannot extract shellcheck paths with spaces; plan lists this as an acceptable under-match failure mode. Acceptance items requiring `bash scripts/test-lint-fix-loop.sh`, `test-prompt-template-invariants.sh`, `test-implement-structure.sh`, and `relevant-checks.sh` were not executed in read-only review; test structure matches the plan on inspection only.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (for voters, not machine output):**

| Merged inputs | Rationale |
|---|---|
| 1 + 18 | Same mktemp/`fail_status` gap at `compose_prompt` / line 526 |
| 2 + 6 + 16 | Same broad slash grep at line 111 |
| 5 + 12 | Same missing phase-gating test |
| 7 + 15 | Same spaced-path regex gap at line 99 |
| 9 + 14 | Same process-substitution status swallowing at lines 150–153 |
| 11 kept OOS | Same risk as FINDING_1 but source tagged `[OUT_OF_SCOPE]` — not merged into in-scope block per OOS heading rule |

Input FINDING_11 (OOS duplicate of FINDING_1) is retained as FINDING_13 rather than subsumed, because the OOS tag must remain visible for Piece 2 round-trip. All other inputs are accounted for in the table above.

No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line — structured findings are present.
