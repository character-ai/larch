### FINDING_1: panel [code-review/accepted]

## **Concrete scenario:** Codex and Cursor both fail or are unavailable; the script “succeeds” the Claude leg while the subprocess is instructed not to edit, so accepted findings are not applied despite a green `CODER_TOOL=claude-subagent` / `CODER_STATUS=applied` path.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## The branch adds a new implement-run directory under `larch-logs/implement/` including `operator_cwd` / `operator_repo_root` and embedded plan text. This is outside the #2208 feature surface, enlarges the shipped plugin tree, and leaks machine-local paths into every consumer clone.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## The fallback invokes `launch-claude-subprocess.sh`, which unconditionally prepends a read-only mandate (“Do NOT use Edit, Write, or Bash tools. Do NOT modify files.”) before the coder prompt ([`scripts/launch-claude-subprocess.sh` lines 115–117](scripts/launch-claude-subprocess.sh)). That contradicts the feature/plan requirement that the Claude subagent **apply** voted-in code changes.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## When `REVIEW_CORE_STATUS` is `fix-required` but all in-scope findings are removed by the OOS awk filter or by submodule scrubbing (`CODER_STATUS=skipped`, `coder_rc=0`), the new `else` branch sets **`status=complete` and `exit_code=0`**.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## `launch-claude-subprocess.sh` ends with **`exit 0` unconditionally** ([line 171](scripts/launch-claude-subprocess.sh)) even when the inner `claude` CLI fails, and it emits `STATUS` via `emit_kv` on **FD 3** when quiet-init is active ([`scripts/lib-quiet.sh` lines 105–111](scripts/lib-quiet.sh)), not on stdout. Redirecting `> "$round_dir/coder-claude.env"` therefore typically **does not** contain `STATUS=…`. The caller treats `[[ "$status_line" == "OK" || -z "$status_line" ]]` as success.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## 1. **Claude fallback** is wired through [`scripts/launch-claude-subprocess.sh`](scripts/launch-claude-subprocess.sh), which is explicitly a **read-only reviewer** launcher and prepends instructions forbidding edits — this conflicts with the stated goal that the Claude subagent **applies** fixes (feature + plan).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## 2. **Committed `larch-logs/implement/73826C67-...`** tree (manifest, `plan-goals-test.md`, `plan-review-tally.json`) is **not** listed in the plan or feature description and carries operator-local paths — scope/hygiene issue.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Concrete scenario:** Inner `claude` exits non-zero (missing CLI, model error, timeout mapped to ERROR); the wrapper still exits 0, `kv_get` sees no `STATUS`, and `run_coder_dispatch` records a false successful Claude fallback.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## **Important** (`correctness`) — [skills/implement/SKILL.md](skills/implement/SKILL.md):1412-1416 — Step 5 still tells the orchestrator to append to `rejected-findings.md` when the **main agent skips any accepted fixer item** during Step 5. The plan removes the fixer / `FINDING_N.fixer.env` path and states the main agent must **never** apply (or selectively skip) review fixes via Edit/Write; fixes are applied by the coder pipeline or the round fails. Leaving this paragraph in place contradicts the new contract and can mis-route operators to a dead workflow (there are no per-finding fixer artifacts to skip anymore). **Scenario:** A reader follows Step 5 literally and looks for fixer-side effects or “skip” handling that no longer exists. **Fix:** Rewrite that bullet to describe coder outcomes only (e.g. findings the coder reported as `SKIPPED:` in its log, or panel-level rejections), or drop the “main agent skips accepted fixer item” wording entirely.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** (`correctness`) — [skills/implement/SKILL.md](skills/implement/SKILL.md):1412-1416 — Step 5 still tells the orchestrator to append to `rejected-findings.md` when the **main agent skips any accepted fixer item** during Step 5. The plan removes the fixer / `FINDING_N.fixer.env` path and states the main agent must **never** apply (or selectively skip) review fixes via Edit/Write; fixes are applied by the coder pipeline or the round fails. Leaving this paragraph in place contradicts the new contract and can mis-route operators to a dead workflow (there are no per-finding fixer artifacts to skip anymore). **Scenario:** A reader follows Step 5 literally and looks for fixer-side effects or “skip” handling that no longer exists. **Fix:** Rewrite that bullet to describe coder outcomes only (e.g. findings the coder reported as `SKIPPED:` in its log, or panel-level rejections), or drop the “main agent skips accepted fixer item” wording entirely.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## **Important** (`security`) — [`larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/manifest.json`](larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/manifest.json):5-6 — The branch adds committed implement run artifacts under `larch-logs/implement/…`, including `operator_cwd` and `operator_repo_root` with the full local filesystem path (`/Users/zhupanov/…`). That bakes operator machine layout into git history and any clone of the repo, which is a privacy / footprint leak and expands what future readers (including CI logs, forks, and issue miners) can infer about the environment. **Scenario:** anyone browsing the merged tree sees the developer’s home-style path and run id without opting in. **Fix:** drop these files from the commit (use `.gitignore` / existing run-log policy), or replace with redacted fixture paths if a sample is required.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Important** (`security`) — [`larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/manifest.json`](larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/manifest.json):5-6 — The branch adds committed implement run artifacts under `larch-logs/implement/…`, including `operator_cwd` and `operator_repo_root` with the full local filesystem path (`/Users/zhupanov/…`). That bakes operator machine layout into git history and any clone of the repo, which is a privacy / footprint leak and expands what future readers (including CI logs, forks, and issue miners) can infer about the environment. **Scenario:** anyone browsing the merged tree sees the developer’s home-style path and run id without opting in. **Fix:** drop these files from the commit (use `.gitignore` / existing run-log policy), or replace with redacted fixture paths if a sample is required.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## **Important** `code-quality` `plan` — The branch adds committed run material under [larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/](larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/) (e.g. `manifest.json` with absolute `operator_cwd` / `operator_repo_root`, plus `plan-goals-test.md` that embeds the full implementation plan and repeated `call-fixer` text). That is unrelated functional surface for #2208, enlarges the plugin tree, and defeats the plan’s own “grep `call-fixer`/`\.fixer\.env` under `skills/` + `scripts/`” cleanliness check if someone runs it from repo root without excluding `larch-logs/`. **Suggested fix:** drop the implement-run log commit from the feature PR or relocate it to a non-shipped path per repo policy; redact machine-specific fields if logs must ship.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Important** `code-quality` `plan` — The branch adds committed run material under [larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/](larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/) (e.g. `manifest.json` with absolute `operator_cwd` / `operator_repo_root`, plus `plan-goals-test.md` that embeds the full implementation plan and repeated `call-fixer` text). That is unrelated functional surface for #2208, enlarges the plugin tree, and defeats the plan’s own “grep `call-fixer`/`\.fixer\.env` under `skills/` + `scripts/`” cleanliness check if someone runs it from repo root without excluding `larch-logs/`. **Suggested fix:** drop the implement-run log commit from the feature PR or relocate it to a non-shipped path per repo policy; redact machine-specific fields if logs must ship.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## **Important** `risk-integration` `plan` [skills/implement/SKILL.md](skills/implement/SKILL.md) around the Step 5 “rejected findings” bullet (line ~1414 in the updated file) — The prose still says the main agent should append skipped **“accepted fixer item”** entries to `rejected-findings.md`, which contradicts the new model (no `call-fixer` / `.fixer.env`; coders apply fixes). Orchestrators following this literally may invent obsolete bookkeeping. **Suggested fix:** rephrase to “accepted finding the coder skipped or could not apply” (or point at `CODER_STATUS` / round logs) and remove the word “fixer”.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Important** `risk-integration` `plan` [skills/implement/SKILL.md](skills/implement/SKILL.md) around the Step 5 “rejected findings” bullet (line ~1414 in the updated file) — The prose still says the main agent should append skipped **“accepted fixer item”** entries to `rejected-findings.md`, which contradicts the new model (no `call-fixer` / `.fixer.env`; coders apply fixes). Orchestrators following this literally may invent obsolete bookkeeping. **Suggested fix:** rephrase to “accepted finding the coder skipped or could not apply” (or point at `CODER_STATUS` / round logs) and remove the word “fixer”.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## **Important** `security` `skills/review-and-fix/scripts/review-and-fix.sh:141-166` — Post-dispatch “layer 3” only unions `git diff --name-only` and `git diff --name-only --cached`, then reverts matching paths. Untracked paths (including new files under a submodule directory) never appear in those diffs, so a workspace-write coder can still leave submodule-tree content behind while the script reports `CODER_STATUS=applied` and `SUBMODULE_REVERT_COUNT=0`. That weakens the stated triple-layer guarantee in [SECURITY.md](SECURITY.md) (post-dispatch revert described as the mechanical control). **Suggested fix:** extend the post-dispatch scan with `git status --porcelain` (or compare against a pre-dispatch snapshot) and treat untracked paths under submodule roots like tracked edits (revert/remove + count toward violation).

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** `security` `skills/review-and-fix/scripts/review-and-fix.sh:141-166` — Post-dispatch “layer 3” only unions `git diff --name-only` and `git diff --name-only --cached`, then reverts matching paths. Untracked paths (including new files under a submodule directory) never appear in those diffs, so a workspace-write coder can still leave submodule-tree content behind while the script reports `CODER_STATUS=applied` and `SUBMODULE_REVERT_COUNT=0`. That weakens the stated triple-layer guarantee in [SECURITY.md](SECURITY.md) (post-dispatch revert described as the mechanical control). **Suggested fix:** extend the post-dispatch scan with `git status --porcelain` (or compare against a pre-dispatch snapshot) and treat untracked paths under submodule roots like tracked edits (revert/remove + count toward violation).
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## **Important** correctness — `skills/review-and-fix/scripts/review-and-fix.sh:129`: the Claude fallback cannot apply fixes because it uses `scripts/launch-claude-subprocess.sh`, which prepends a read-only instruction at `scripts/launch-claude-subprocess.sh:116`. If Codex and Cursor fail, the wrapper can return `CODER_TOOL=claude-subagent` and `CODER_STATUS=applied` even though the subprocess is explicitly told not to modify files. Use a write-capable Claude coder launcher/mode with appropriate guards, or remove Claude from the apply-fixes fallback chain.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** correctness — `skills/review-and-fix/scripts/review-and-fix.sh:129`: the Claude fallback cannot apply fixes because it uses `scripts/launch-claude-subprocess.sh`, which prepends a read-only instruction at `scripts/launch-claude-subprocess.sh:116`. If Codex and Cursor fail, the wrapper can return `CODER_TOOL=claude-subagent` and `CODER_STATUS=applied` even though the subprocess is explicitly told not to modify files. Use a write-capable Claude coder launcher/mode with appropriate guards, or remove Claude from the apply-fixes fallback chain.
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## **Important** correctness — `skills/review-and-fix/scripts/review-and-fix.sh:188`: scrubber failures are silently converted into “skipped” success because callers invoke `apply_findings_with_coder` under `set +e` and the helper never checks the scrub command’s exit status or `SCRUB_OK`. A symlinked `--findings-file` passes `run_findings_mode`’s `-f` check, is rejected by `scrub-submodule-paths.sh`, then returns `REVIEW_AND_FIX_STATUS=complete` / `CODER_STATUS=skipped` with exit 0. Check the scrub exit status and fail closed with `CODER_STATUS=failed` instead of treating missing scrubbed output as no work.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 5. **Important** correctness — `skills/review-and-fix/scripts/review-and-fix.sh:188`: scrubber failures are silently converted into “skipped” success because callers invoke `apply_findings_with_coder` under `set +e` and the helper never checks the scrub command’s exit status or `SCRUB_OK`. A symlinked `--findings-file` passes `run_findings_mode`’s `-f` check, is rejected by `scrub-submodule-paths.sh`, then returns `REVIEW_AND_FIX_STATUS=complete` / `CODER_STATUS=skipped` with exit 0. Check the scrub exit status and fail closed with `CODER_STATUS=failed` instead of treating missing scrubbed output as no work.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Concrete scenario:** Merge publishes another operator’s filesystem layout and in-progress manifest alongside functional code changes.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## **Important** risk-integration — `skills/review-and-fix/scripts/review-and-fix.sh:122`: the Cursor fallback invokes `cursor-agent --print --prompt`, but this repo’s supported Cursor launch shape is `cursor agent ... --workspace "$PWD"` with auth/model handling. On a host where `CURSOR_HEALTHY=true` was established via the standard `cursor agent` CLI, this fallback hits `command not found`, skips Cursor, and falls into the broken Claude fallback. Route through the existing Cursor launcher conventions or invoke `cursor agent` with the same auth/model/workspace setup used elsewhere.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** risk-integration — `skills/review-and-fix/scripts/review-and-fix.sh:122`: the Cursor fallback invokes `cursor-agent --print --prompt`, but this repo’s supported Cursor launch shape is `cursor agent ... --workspace "$PWD"` with auth/model handling. On a host where `CURSOR_HEALTHY=true` was established via the standard `cursor agent` CLI, this fallback hits `command not found`, skips Cursor, and falls into the broken Claude fallback. Route through the existing Cursor launcher conventions or invoke `cursor agent` with the same auth/model/workspace setup used elsewhere.
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## **Important** · `risk-integration` · `larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/manifest.json` · `plan-goals-test.md` · `plan-review-tally.json` · **source: requirements (scope) + plan (omission)**

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **Important** · `risk-integration` · `larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/manifest.json` · `plan-goals-test.md` · `plan-review-tally.json` · **source: requirements (scope) + plan (omission)**
- **Suggested revision**: Address the concern above.

### FINDING_36: panel [code-review/accepted]

## **Latent** (`correctness`) — [`skills/review-and-fix/scripts/review-and-fix.sh`](skills/review-and-fix/scripts/review-and-fix.sh):129-134 — `run_coder_dispatch` treats an empty `STATUS` line from `coder-claude.env` as success (`OK` **or** `-z "$status_line"`). If `launch-claude-subprocess.sh` ever omits `STATUS` on a failed or partial run, the wrapper could classify a broken subagent invocation as successful and skip fallbacks, leaving the tree in an ambiguous state while emitting `CODER_TOOL=claude-subagent`. **Fix:** require an explicit `STATUS=OK` (fail closed on missing/unknown `STATUS`) or align with whatever sentinel `launch-claude-subprocess.sh` guarantees on all exit paths.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Latent** (`correctness`) — [`skills/review-and-fix/scripts/review-and-fix.sh`](skills/review-and-fix/scripts/review-and-fix.sh):129-134 — `run_coder_dispatch` treats an empty `STATUS` line from `coder-claude.env` as success (`OK` **or** `-z "$status_line"`). If `launch-claude-subprocess.sh` ever omits `STATUS` on a failed or partial run, the wrapper could classify a broken subagent invocation as successful and skip fallbacks, leaving the tree in an ambiguous state while emitting `CODER_TOOL=claude-subagent`. **Fix:** require an explicit `STATUS=OK` (fail closed on missing/unknown `STATUS`) or align with whatever sentinel `launch-claude-subprocess.sh` guarantees on all exit paths.
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## **Latent** · `correctness` · `skills/review-and-fix/scripts/review-and-fix.sh` (`run_implement_round` exit classification for `fix-required|cap-reached`) · **source: plan**

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 4. **Latent** · `correctness` · `skills/review-and-fix/scripts/review-and-fix.sh` (`run_implement_round` exit classification for `fix-required|cap-reached`) · **source: plan**
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## **Nit** (`code-quality`) — [`scripts/test-review-structure.md`](scripts/test-review-structure.md):5-7 — Assertion 1c/1d text still claims `agents/orchestrator-judge.md` is a required hand-maintained agent, while [`scripts/test-review-structure.sh`](scripts/test-review-structure.sh):110-111 asserts that file **must not** exist. Assertion 20 also references `skills/review/references/voting.md` while the harness asserts that path must not exist. **Fix:** align the markdown contract with the shell assertions (or vice versa) in the same change set that touches this doc.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 7. **Nit** (`code-quality`) — [`scripts/test-review-structure.md`](scripts/test-review-structure.md):5-7 — Assertion 1c/1d text still claims `agents/orchestrator-judge.md` is a required hand-maintained agent, while [`scripts/test-review-structure.sh`](scripts/test-review-structure.sh):110-111 asserts that file **must not** exist. Assertion 20 also references `skills/review/references/voting.md` while the harness asserts that path must not exist. **Fix:** align the markdown contract with the shell assertions (or vice versa) in the same change set that touches this doc.
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## **Nit** (`code-quality`) — [`skills/implement/SKILL.md`](skills/implement/SKILL.md) (Step 5 “Track Rejected Code Review Findings” block, ~line 887 in the diff hunk) — Prose still says “If the main agent skips any accepted **fixer** item …” after removing `call-fixer.sh`. **Fix:** reword to “accepted finding” / “coder outcome” for consistency with the new contract.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 6. **Nit** (`code-quality`) — [`skills/implement/SKILL.md`](skills/implement/SKILL.md) (Step 5 “Track Rejected Code Review Findings” block, ~line 887 in the diff hunk) — Prose still says “If the main agent skips any accepted **fixer** item …” after removing `call-fixer.sh`. **Fix:** reword to “accepted finding” / “coder outcome” for consistency with the new contract.
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## **Nit** `code-quality` `scripts/scrub-submodule-paths.sh:78` — Path grep allowlist omits several common extensions (e.g. `.rs`, `.toml`, `.go` is covered, `.rs` is not). Findings that only mention such paths outside the `Location`/`File` bullets rely on the grep fallback and may bypass submodule scrubbing. **Suggested fix:** widen the extension alternation or reuse a more general path token pattern.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 6. **Nit** `code-quality` `scripts/scrub-submodule-paths.sh:78` — Path grep allowlist omits several common extensions (e.g. `.rs`, `.toml`, `.go` is covered, `.rs` is not). Findings that only mention such paths outside the `Location`/`File` bullets rely on the grep fallback and may bypass submodule scrubbing. **Suggested fix:** widen the extension alternation or reuse a more general path token pattern.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Suggested fix:** Distinguish “no in-scope actionable work after filtering” from “no accepted findings” (e.g. exit 3 with `CODER_STATUS=skipped` and a distinct `REVIEW_AND_FIX_STATUS`, or keep `fix-required` with exit 2/3 per policy).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_51: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	code-quality	larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/	Committed implement run logs embed full plan text, call-fixer mentions, and absolute operator paths.	Bloats shipped tree; grep-based cleanliness checks from repo root hit false positives; manifests leak local filesystem layout.	Remove run-log commit from feature PR or strip/redact per logging policy.
- **Suggested revision**: Address the concern above.

### FINDING_52: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/SKILL.md:1412-1416	Stale Step 5 prose still references main agent skipping accepted fixer items after call-fixer removal and no-Edit/Write rule.	Operators or automation following SKILL.md may search for fixer.env-based skip handling that no longer exists or contradicts coder-only application.	Reword or remove the fixer skip instruction so Step 5 matches coder dispatch only.
- **Suggested revision**: Address the concern above.

### FINDING_53: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/review-and-fix/scripts/review-and-fix.sh:run_coder_dispatch	Claude fallback uses launch-claude-subprocess read-only preamble	Codex/Cursor fail; Claude subprocess is told not to edit; fixes not applied while orchestration may report success	Use a write-capable subprocess launcher or add coder mode without read-only injection
- **Suggested revision**: Address the concern above.

### FINDING_54: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/review-and-fix/scripts/review-and-fix.sh:run_coder_dispatch	launch-claude-subprocess always exits 0; STATUS KV on FD3 not in captured env file	Inner claude fails; wrapper exits 0; empty STATUS parsed as success; false successful fallback	Parse .done exit code exit non-zero on tool failure or emit STATUS to stdout
- **Suggested revision**: Address the concern above.

### FINDING_55: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/manifest.json:1-20 plus sibling plan files	Committed implement run artifacts with operator paths outside #2208 scope	Clone ships local paths and in-progress manifest; PR noise and privacy	Remove larch-logs directory from branch
- **Suggested revision**: Address the concern above.

### FINDING_56: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/SKILL.md:1414	Step 5 prose still references skipped accepted fixer items.	Conflicts with coder-dispatch contract; orchestrators may follow obsolete fixer-env workflow.	Reword to coder-skip vocabulary and point at CODER_STATUS / logs.
- **Suggested revision**: Address the concern above.

### FINDING_57: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	security	larch-logs/implement/73826C67-B7E4-4EED-B7DA-389D968FE19A/manifest.json:5-6	Committed implement manifest records operator_cwd/operator_repo_root with absolute local paths.	Paths and run metadata become permanent repo content visible to all readers and forks.	Remove or redact run artifacts; keep larch-logs out of version control unless policy explicitly allows.
- **Suggested revision**: Address the concern above.

### FINDING_59: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	security	skills/review-and-fix/scripts/review-and-fix.sh:141-166	Post-dispatch submodule guard only inspects tracked/staged diffs, not untracked paths.	Coder can create untracked files under a submodule path; no revert runs; round still succeeds as applied.	Include git status porcelain (or snapshot diff) and treat untracked submodule paths as violations / revert targets.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Suggested fix:** Parse `${OUTPUT_FILE}.done` (non-zero means failure), add a dedicated machine-readable status file on stdout, or change the launcher to exit non-zero on subprocess failure; capture quiet-stream KVs if STATUS must stay on FD3.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_60: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/review-and-fix/scripts/review-and-fix.sh:129-134	Claude coder success treats empty STATUS as OK alongside explicit OK.	Missing STATUS on failure could be misclassified as success.	Require explicit STATUS=OK or tighten contract with launch-claude-subprocess.sh.
- **Suggested revision**: Address the concern above.

### FINDING_62: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/review-and-fix/scripts/review-and-fix.sh:run_implement_round fix-required branch	fix-required with zero post-filter actionable findings maps to complete exit 0	Accepted findings all OOS or scrubbed; core still fix-required; parent skips follow-up incorrectly	Emit distinct status exit code when accepted exist but none actionable
- **Suggested revision**: Address the concern above.

### FINDING_67: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	scripts/scrub-submodule-paths.sh:78	Path extraction regex omits several common file extensions. Submodule-only hints in prose for e.g. .rs files may skip scrub layer 1.	Expand extension list or generalize path token extraction.
- **Suggested revision**: Address the concern above.

### FINDING_68: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	scripts/test-review-structure.md:5-7 vs scripts/test-review-structure.sh:100-113	Contract markdown contradicts harness on orchestrator-judge and voting.md paths.	Contributors following only SKILL.md-style contract get wrong expectations.	Align documentation with assertions.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Suggested fix:** Remove these paths from the branch (keep only intentional code/docs/harness changes).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_70: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	skills/implement/SKILL.md (Step 5 Track Rejected block)	Stale wording references fixer items after call-fixer removal.	Operator confusion about who applies fixes.	Reword to coder/finding terminology.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Suggested fix:** Restore accurate guidance (e.g. reference `dispatch-code-voters.sh` / current panel layout as before).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_82: panel [code-review/accepted]

## Identifying a critical argv mismatch: the repo’s Cursor health probe and launchers use `cursor agent`, while the new coder path uses `cursor-agent`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Suggested fix:** Use a write-capable launcher (new script or an explicit “coder mode” on an existing one) that does not inject the read-only preamble, or invoke `claude` with a prompt file that is not wrapped by the reviewer-only header.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

