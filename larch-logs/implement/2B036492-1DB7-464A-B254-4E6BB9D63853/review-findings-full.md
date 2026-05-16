### FINDING_1: panel [code-review/accepted]

## **Important** (`correctness` / `risk-integration`) — [`agents/codex-implementer.md`](agents/codex-implementer.md):62,146-147 and [`agents/cursor-implementer.md`](agents/cursor-implementer.md):68,152-153 — Prose still states the dispatcher “does NOT cross-check” `files_touched` against actual changes and that accuracy is “no longer mechanically enforced,” while Step 7a.1 now **mechanically compares** porcelain paths to the manifest and logs a Warning. **Scenario:** implementers follow outdated guidance, treat `files_touched` as purely narrative, then are surprised by new `execution-issues.md` warnings or misread them as benign. **Suggested fix:** narrow the wording to “no `git diff` / subject-line enforcement and no bail,” and explicitly document the Step 7a.1 path-set warning.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Important** (`correctness` / `risk-integration`) — [`agents/codex-implementer.md`](agents/codex-implementer.md):62,146-147 and [`agents/cursor-implementer.md`](agents/cursor-implementer.md):68,152-153 — Prose still states the dispatcher “does NOT cross-check” `files_touched` against actual changes and that accuracy is “no longer mechanically enforced,” while Step 7a.1 now **mechanically compares** porcelain paths to the manifest and logs a Warning. **Scenario:** implementers follow outdated guidance, treat `files_touched` as purely narrative, then are surprised by new `execution-issues.md` warnings or misread them as benign. **Suggested fix:** narrow the wording to “no `git diff` / subject-line enforcement and no bail,” and explicitly document the Step 7a.1 path-set warning.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** (`correctness`, both) [SECURITY.md](SECURITY.md) (trust-model paragraph), [agents/codex-implementer.md:62-63,131,146](agents/codex-implementer.md), [agents/cursor-implementer.md](agents/cursor-implementer.md) (same “does NOT cross-check” bullets where mirrored), [agents/_implementer-base.md:41-42](agents/_implementer-base.md) — After Step 7a.1, claiming there is **“no diff cross-check”** / that the dispatcher **“does NOT cross-check”** `files_touched` against actual changes is **false or at least materially misleading**: the dispatcher now compares declared manifest paths to **all** porcelain paths and appends a Warning. **Concrete scenario:** An implementer reads `codex-implementer.md` bullet 3 or the SECURITY trust paragraph, believes manifest vs tree is purely honor-system, and under-declares `files_touched` thinking nothing mechanical cares—yet they still get a Warning and contradictory docs. **Suggested fix:** Reword to distinguish removed **diff/subject** checks from the new **path-set** diagnostic, and update every stale bullet (including “What you do NOT do” / checklist if still present in codex).

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **Important** (`correctness`, both) [SECURITY.md](SECURITY.md) (trust-model paragraph), [agents/codex-implementer.md:62-63,131,146](agents/codex-implementer.md), [agents/cursor-implementer.md](agents/cursor-implementer.md) (same “does NOT cross-check” bullets where mirrored), [agents/_implementer-base.md:41-42](agents/_implementer-base.md) — After Step 7a.1, claiming there is **“no diff cross-check”** / that the dispatcher **“does NOT cross-check”** `files_touched` against actual changes is **false or at least materially misleading**: the dispatcher now compares declared manifest paths to **all** porcelain paths and appends a Warning. **Concrete scenario:** An implementer reads `codex-implementer.md` bullet 3 or the SECURITY trust paragraph, believes manifest vs tree is purely honor-system, and under-declares `files_touched` thinking nothing mechanical cares—yet they still get a Warning and contradictory docs. **Suggested fix:** Reword to distinguish removed **diff/subject** checks from the new **path-set** diagnostic, and update every stale bullet (including “What you do NOT do” / checklist if still present in codex).
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** (`correctness`, plan + requirements) [skills/implement/scripts/step2-implement.sh:653-675](skills/implement/scripts/step2-implement.sh) — The warning text attributes all undeclared porcelain paths to the **“external implementer”**, but the set is `git status --porcelain` minus manifest paths with **no baseline** of what existed before the implementer ran. **Concrete scenario:** The operator leaves `notes.md` dirty before Step 2; the implementer touches only `foo.sh` and lists it in `files_touched`. Step 7a.1 still logs `notes.md` as if the implementer bundled it. **Suggested fix:** Narrow attribution (e.g. “working-tree paths not listed in manifest”) or diff against a pre-implementer snapshot if you truly need implementer-only blame.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Important** (`correctness`, plan + requirements) [skills/implement/scripts/step2-implement.sh:653-675](skills/implement/scripts/step2-implement.sh) — The warning text attributes all undeclared porcelain paths to the **“external implementer”**, but the set is `git status --porcelain` minus manifest paths with **no baseline** of what existed before the implementer ran. **Concrete scenario:** The operator leaves `notes.md` dirty before Step 2; the implementer touches only `foo.sh` and lists it in `files_touched`. Step 7a.1 still logs `notes.md` as if the implementer bundled it. **Suggested fix:** Narrow attribution (e.g. “working-tree paths not listed in manifest”) or diff against a pre-implementer snapshot if you truly need implementer-only blame.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** (`correctness`, requirements vs plan) [skills/implement/scripts/step2-implement.sh:653-670](skills/implement/scripts/step2-implement.sh) — `<feature_description>` asked to cross-reference the plan’s **“Files to modify”** section as well as the manifest and working tree; the implementation only compares **porcelain vs manifest** (`jq` on `files_touched` / `tests_added_or_modified`). **Concrete scenario:** A path appears in the plan and in the working tree but is omitted from both `files_touched` and `tests_added_or_modified`; it will **not** be reported as OOS by this check. The code follows the written implementation plan, not the broader feature text—call out which spec should win and implement or document the gap.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Important** (`correctness`, requirements vs plan) [skills/implement/scripts/step2-implement.sh:653-670](skills/implement/scripts/step2-implement.sh) — `<feature_description>` asked to cross-reference the plan’s **“Files to modify”** section as well as the manifest and working tree; the implementation only compares **porcelain vs manifest** (`jq` on `files_touched` / `tests_added_or_modified`). **Concrete scenario:** A path appears in the plan and in the working tree but is omitted from both `files_touched` and `tests_added_or_modified`; it will **not** be reported as OOS by this check. The code follows the written implementation plan, not the broader feature text—call out which spec should win and implement or document the gap.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Important** (`risk-integration`, `requirements`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh):653-682 — The `<feature_description>` asked to cross-reference the working tree and manifest **against the plan’s “Files to modify”** section; the shipped logic only diffs `git status --porcelain` pathnames against `files_touched` / `tests_added_or_modified` from the manifest and never reads `--plan-file`. **Scenario:** an implementer touches a file not listed in the plan but adds that path to `manifest.files_touched` so it matches the tree; no OOS warning fires even though the change is out of plan scope. **Suggested fix:** parse the plan’s “Files to modify” list (same way other steps consume `--plan-file`) and emit an additional warning (or extend the OOS set) when porcelain paths or manifest paths fall outside that set.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`, `requirements`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh):653-682 — The `<feature_description>` asked to cross-reference the working tree and manifest **against the plan’s “Files to modify”** section; the shipped logic only diffs `git status --porcelain` pathnames against `files_touched` / `tests_added_or_modified` from the manifest and never reads `--plan-file`. **Scenario:** an implementer touches a file not listed in the plan but adds that path to `manifest.files_touched` so it matches the tree; no OOS warning fires even though the change is out of plan scope. **Suggested fix:** parse the plan’s “Files to modify” list (same way other steps consume `--plan-file`) and emit an additional warning (or extend the OOS set) when porcelain paths or manifest paths fall outside that set.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Important** (`risk-integration`, both) [agents/codex-implementer.md:23-34 vs 104-113 vs 119](agents/codex-implementer.md), [agents/_implementer-base.md:23-34](agents/_implementer-base.md) — **NEVER #8** (under “Hard guards” whose preamble says violations **MUST** yield `status=bailed`) tells the model to put out-of-plan issues in `oos_observations[]` instead of editing, while the **OOS triage** block’s **Rule 1** requires folding documentation drift **into this commit** (which normally means editing the drifted file, often outside the narrow “Files to modify” list). **Concrete scenario:** Doc drift in a file not listed under “Files to modify”: Rule 1 says fold inline; NEVER #8 says do not edit and use `oos_observations[]`—the model receives incompatible instructions. **Suggested fix:** Add explicit precedence (e.g. triage rules override scope for Rule 1–2 folds), move scope rule out of “MUST bail” hard guards, or carve exceptions in NEVER #8.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 4. **Important** (`risk-integration`, both) [agents/codex-implementer.md:23-34 vs 104-113 vs 119](agents/codex-implementer.md), [agents/_implementer-base.md:23-34](agents/_implementer-base.md) — **NEVER #8** (under “Hard guards” whose preamble says violations **MUST** yield `status=bailed`) tells the model to put out-of-plan issues in `oos_observations[]` instead of editing, while the **OOS triage** block’s **Rule 1** requires folding documentation drift **into this commit** (which normally means editing the drifted file, often outside the narrow “Files to modify” list). **Concrete scenario:** Doc drift in a file not listed under “Files to modify”: Rule 1 says fold inline; NEVER #8 says do not edit and use `oos_observations[]`—the model receives incompatible instructions. **Suggested fix:** Add explicit precedence (e.g. triage rules override scope for Rule 1–2 folds), move scope rule out of “MUST bail” hard guards, or carve exceptions in NEVER #8.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Important** `correctness` `skills/implement/scripts/step2-implement.sh:667` — The detector only compares working-tree paths against `manifest.files_touched` / `tests_added_or_modified`; it never checks the plan’s `Files to modify` section. Concrete failing scenario: a plan allows only `README.md`, the implementer edits `SECURITY.md` and includes `SECURITY.md` in `files_touched`; `comm -23` sees no undeclared path, no Warning is appended, and `git add -A` commits the out-of-plan file. Suggested fix: parse the plan scope from `$PLAN_FILE` and warn on working-tree paths and manifest-declared paths that are outside that scope; add a regression where the manifest declares an out-of-plan path.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/implement/scripts/step2-implement.sh:667` — The detector only compares working-tree paths against `manifest.files_touched` / `tests_added_or_modified`; it never checks the plan’s `Files to modify` section. Concrete failing scenario: a plan allows only `README.md`, the implementer edits `SECURITY.md` and includes `SECURITY.md` in `files_touched`; `comm -23` sees no undeclared path, no Warning is appended, and `git add -A` commits the out-of-plan file. Suggested fix: parse the plan scope from `$PLAN_FILE` and warn on working-tree paths and manifest-declared paths that are outside that scope; add a regression where the manifest declares an out-of-plan path.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Latent** (`correctness`, plan) [skills/implement/scripts/step2-implement.sh:664-665](skills/implement/scripts/step2-implement.sh) — `awk 'NF {print $NF}'` on porcelain lines can mis-extract paths for **quoted paths** or some multi-field status shapes. **Concrete scenario:** A tracked file whose path contains spaces shows as `"path with spaces"` in porcelain; `$NF` may be a partial token or wrong field, so OOS detection misses or mis-names the path. **Suggested fix:** Use `-z` porcelain plus `git status --porcelain=v2` / NUL-delimited parsing, or a parser that respects quoting.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 5. **Latent** (`correctness`, plan) [skills/implement/scripts/step2-implement.sh:664-665](skills/implement/scripts/step2-implement.sh) — `awk 'NF {print $NF}'` on porcelain lines can mis-extract paths for **quoted paths** or some multi-field status shapes. **Concrete scenario:** A tracked file whose path contains spaces shows as `"path with spaces"` in porcelain; `$NF` may be a partial token or wrong field, so OOS detection misses or mis-names the path. **Suggested fix:** Use `-z` porcelain plus `git status --porcelain=v2` / NUL-delimited parsing, or a parser that respects quoting.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Nit** (`code-quality`, plan) [agents/cursor-implementer.md](agents/cursor-implementer.md) — The implementation plan’s Step 4 called the new Cursor rule **NEVER #7**; the branch adds it as **NEVER #8** (because #7 is “Control artifacts”). Numbering matches the file’s structure; only the plan text is stale.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 6. **Nit** (`code-quality`, plan) [agents/cursor-implementer.md](agents/cursor-implementer.md) — The implementation plan’s Step 4 called the new Cursor rule **NEVER #7**; the branch adds it as **NEVER #8** (because #7 is “Control artifacts”). Numbering matches the file’s structure; only the plan text is stale.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## **Nit** (`risk-integration`, `plan`) — [`agents/cursor-implementer.md`](agents/cursor-implementer.md):54 — The written implementation plan called the new rule “NEVER #7” for Cursor parity; the repo keeps “Control artifacts” as #7 and adds scope as **#8**, matching Codex numbering instead. **Suggested fix:** align internal plan/checklist text only; behavior is fine.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Nit** (`risk-integration`, `plan`) — [`agents/cursor-implementer.md`](agents/cursor-implementer.md):54 — The written implementation plan called the new rule “NEVER #7” for Cursor parity; the repo keeps “Control artifacts” as #7 and adds scope as **#8**, matching Codex numbering instead. **Suggested fix:** align internal plan/checklist text only; behavior is fine.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## **Nit** `correctness` `skills/implement/scripts/step2-implement.sh:664` — `git status --porcelain | awk '{print $NF}'` misparses valid paths containing spaces, so a declared edit like `docs/api guide.md` is compared as `guide.md` and can emit a bogus OOS warning. Suggested fix: use a NUL-safe status/diff path source such as `git status --porcelain=v1 -z` with an explicit parser, or another Git command that emits exact pathnames.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `correctness` `skills/implement/scripts/step2-implement.sh:664` — `git status --porcelain | awk '{print $NF}'` misparses valid paths containing spaces, so a declared edit like `docs/api guide.md` is compared as `guide.md` and can emit a bogus OOS warning. Suggested fix: use a NUL-safe status/diff path source such as `git status --porcelain=v1 -z` with an explicit parser, or another Git command that emits exact pathnames.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## **Read-only session:** the instructions asked for a TSV sidecar on disk; that was not written. Copy these records if you need them:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## ---

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	SECURITY.md; agents/codex-implementer.md:62-63,131,146; agents/_implementer-base.md:41-42	Stale claims of no cross-check contradict new manifest vs porcelain warning	Implementer trusts outdated prompt and misjudges enforcement	Update trust-model and implementer bullets for path-set diagnostic
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	agents/codex-implementer.md:62,146-147;agents/cursor-implementer.md:68,152-153	Implementer docs still claim no dispatcher cross-check of files_touched vs actual edits.	Operators or models follow stale prose and mis-calibrate manifest hygiene vs new Step 7a.1 warnings.	Update copy to describe path-set warning and retain accurate no-diff-cross-check wording.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:653-670	No cross-check against plan Files to modify	Plan-listed file changed on disk but absent from manifest never triggers Step 7a.1	Parse plan scope or document requirement drop
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:653-675	OOS warning blames external implementer for any undeclared porcelain path	Operator pre-existing dirty file not in manifest is attributed to implementer in execution-issues.md	Narrow wording or compare to pre-run baseline
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	agents/codex-implementer.md:23-34,104-113,119	NEVER #8 vs OOS triage Rule 1 conflict under Hard guards	Model cannot reconcile fold-doc-drift vs do-not-edit-out-of-plan	Add precedence or relocate/reword rules
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-682	Step 7a.1 compares git porcelain paths to manifest only; plan Files to modify is never parsed despite feature_description.	Implementer can edit and declare a path not in the plan with no OOS-style signal; plan-scope drift stays invisible.	Parse plan scope from --plan-file and warn on paths outside plan-listed files (and or manifest entries outside plan).
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:664-665	awk $NF porcelain parsing fragile for quoted paths	OOS list wrong or incomplete for paths with spaces	Use v2 or NUL-delimited status parsing
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	agents/cursor-implementer.md	Plan said NEVER #7; file uses NEVER #8	None beyond plan doc drift	Align plan text with file numbering
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	agents/cursor-implementer.md:54	NEVER list numbering differs from the Cursor bullet in the authored implementation plan (#7 vs #8).	None beyond doc checklist drift.	Rename in planning artifacts or accept #8 as final.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	architecture	agents/gemini-implementer.md; agents/_implementer-base.md	Scope wider than plan file list	None if parity intentional	Document parity in plan if required
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk-integration	larch-logs/; commit 59c4f13	Log flush bundled with feature PR	Reviewer noise	Split chore PR if undesired
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/*;git:59c4f13	Chore commit flushes implement run logs in the same branch as the feature.	Extra non-functional files in the PR diff.	Keep or split per repo logging policy; not part of OOS detection testing.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## Checking EXIT trap handling and `LAUNCHER_TMP` usage in `step2-implement.sh`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## Checking EXIT trap handling and surrounding context in `step2-implement.sh`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## Checking EXIT trap handling around the new block and reading the Test 18 implementation in the diff.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## Checking `_implementer-base.md` for the Hard guards preamble vs. NEVER #8.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## Checking append-execution-issue formatting and whether the plan file is available to the dispatcher for a plan-based check:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## Checking how the manifest is validated before Step 7 and whether `jq` failure is possible:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## Checking surrounding `step2-implement.sh` for EXIT traps and `LAUNCHER_TMP` usage, and verifying the plan cross-reference gap.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## Checking the "Hard guards" preamble vs. NEVER #8 wording and confirming cursor numbering in the repo.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## Checking the `trap`/`EXIT` interaction in `step2-implement.sh` and scanning other diff hunks for plan alignment.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## Checking whether `larch-logs` commits are intentional and scanning the diff for other sensitive additions:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_36: panel [code-review/accepted]

## Commits on branch vs `main`:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## Commits on branch vs `main`: `68099ed Warn on undeclared implementer files`, `59c4f13 chore(larch-logs): flush implement run ...`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## Confirming `printf` safety: `%s` for `OOS_LIST` avoids format-injection. Checking porcelain edge cases for `awk 'NF {print $NF}'`:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_39: panel [code-review/accepted]

## Creating the plan document summarizing Plan Fidelity findings. Commits: `68099ed` (feature), `59c4f13` (larch-logs flush). Verifying whether `codex-implementer.md` is generated-only (edits should go to `_implementer-base.md`).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_40: panel [code-review/accepted]

## Creating the plan-mode artifact and delivering the full structured review. Commits vs `main`: `68099ed` (OOS warning), `59c4f13` (larch-logs flush).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## Creating the review plan document and delivering the structured review. Findings: the implementation matches the attached implementation_plan but omits the outer feature_description's plan-file cross-check; stale prompt text next to the new NEVER rule; and best-effort `|| true` masking.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## Having reviewed the diff and `step2-implement.sh` trap context: the second `trap` replaces the first but still removes `LAUNCHER_TMP` — functional for the current file; flagging maintainability. Calling CreatePlan to satisfy plan-mode while delivering the requested review.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## Read-only mode: no `.tsv` file was written to disk. Below is the TSV payload you can save as your sidecar (e.g. next to the review output) if your pipeline expects it.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## Read-only review: cannot write the `.tsv` sidecar; TSV lines are included at the end for you to copy if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## Reading the implemented OOS block and Test 18 in the repo for full context.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_46: panel [code-review/accepted]

## Reading the implemented shell logic, `append-execution-issue.sh`, and agent numbering in the workspace.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_47: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: Reviewing the branch diff and commit history (read-only). Gathering the diff and git log.
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Gathering the branch diff and commit history for a read-only review. We won't write the TSV sidecar (read-only constraint); we'll include TSV rows in the response.
- **Suggested revision**: Address the concern above.

### FINDING_49: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only Plan Fidelity review. We won't write the `.tsv` sidecar (that would mutate the filesystem); we'll include TSV rows in the response per your constraints.
- **Suggested revision**: Address the concern above.

### FINDING_50: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: Gathering the branch diff and commit history for a read-only security-focused review. Reading the pre-computed diff and running read-only `git log`.
- **Suggested revision**: Address the concern above.

### FINDING_51: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Gathering the branch diff, commit list, and full-file context for a read-only review (no file writes; TSV provided inline due to read-only constraint).
- **Suggested revision**: Address the concern above.

### FINDING_52: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only review (no file writes). Reading the precomputed diff and running a non-mutating `git log`.
- **Suggested revision**: Address the concern above.

### FINDING_53: panel [code-review/accepted]

## Searching the diff for plan-relevant files and reading those hunks.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_54: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading full files where context is insufficient.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_55: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading full-file context where needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_56: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_57: panel [code-review/accepted]

## Searching the large diff for relevant hunks and reading the modified files for full context.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_58: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`architecture`, out_of_scope) — [agents/gemini-implementer.md](agents/gemini-implementer.md) and [agents/_implementer-base.md](agents/_implementer-base.md) were updated for parity though the attached implementation plan only named Codex/Cursor; reasonable consistency, slightly wider than the written plan.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Nit** (`architecture`, out_of_scope) — [agents/gemini-implementer.md](agents/gemini-implementer.md) and [agents/_implementer-base.md](agents/_implementer-base.md) were updated for parity though the attached implementation plan only named Codex/Cursor; reasonable consistency, slightly wider than the written plan.
- **Suggested revision**: Address the concern above.

### FINDING_59: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`risk-integration`, out_of_scope) — The branch bundles a **larch-logs flush** commit (`59c4f13`) and committed run artifacts under `larch-logs/implement/...` alongside the functional change; noisy for reviewers unless your process requires flushing logs in the same PR.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Nit** (`risk-integration`, out_of_scope) — The branch bundles a **larch-logs flush** commit (`59c4f13`) and committed run artifacts under `larch-logs/implement/...` alongside the functional change; noisy for reviewers unless your process requires flushing logs in the same PR.
- **Suggested revision**: Address the concern above.

### FINDING_60: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** — Commit `59c4f13` refreshes [`larch-logs/implement/...`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) artifacts alongside the functional change; not introduced by the OOS-detection logic itself, but it increases PR noise and review surface beyond the feature.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Nit** — Commit `59c4f13` refreshes [`larch-logs/implement/...`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) artifacts alongside the functional change; not introduced by the OOS-detection logic itself, but it increases PR noise and review surface beyond the feature.
- **Suggested revision**: Address the concern above.

### FINDING_61: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: codex-generalist-output.txt
- **Concern**: No out-of-scope observations.
- **Suggested revision**: Address the concern above.

### FINDING_62: panel [code-review/accepted]

## `59c4f13` — chore(larch-logs): flush implement run …

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `59c4f13` — chore(larch-logs): flush implement run …
- **Suggested revision**: Address the concern above.

### FINDING_63: panel [code-review/accepted]

## `68099ed` — Warn on undeclared implementer files

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `68099ed` — Warn on undeclared implementer files
- **Suggested revision**: Address the concern above.

### FINDING_64: panel [code-review/accepted]

## ```

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_65: panel [code-review/accepted]

## ```text

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_66: panel [code-review/accepted]

## schema_version

- **Reviewer**: scope
- **Concern**: severity	focus_area	location	what	scenario_or_breakage	suggested_fix
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## Entering **7a.1** replaces the earlier `EXIT` trap with one that still removes `"$LAUNCHER_TMP"` and the OOS temp paths. Today that preserves launcher cleanup; if someone later extends only the **405** trap, **7a.1** could silently drop that behavior for runs that hit the OOS block. **Suggested fix:** Use `trap ... EXIT` once with a helper that accumulates cleanup, or push temp cleanup to a function without redefining the whole `EXIT` handler.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## Run log / chore flush artifacts are not part of the functional implementation plan; they add review noise. Out of scope for plan fidelity to the OOS feature itself.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## The feature text asks to cross-reference manifest paths and the working tree **against the plan’s “Files to modify”** section. Step **7a.1** only compares `git status` paths to manifest `files_touched` / `tests_added_or_modified` and the comments state plan-scope drift is **explicitly not** checked. An implementer can list every changed path in the manifest (so **no** Warning) while still editing files the plan never authorized; that scenario stays invisible to this detector. **Suggested fix:** Parse `$PLAN_FILE` for the plan’s file list (or pass a normalized list from the orchestrator) and emit a separate Warning for WT paths not in that set, or narrow the feature text to “manifest vs working tree” only.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## The plan lists four paths; the branch also updates `SECURITY.md`, `agents/_implementer-base.md`, `agents/gemini-implementer.md`, harness markdown, and adds `larch-logs/implement/...` (plus the chore log commit). Most of this is reasonable collateral (SECURITY trust-model note, shared base + Gemini parity, docs, log flush) but it is **outside** the plan’s enumerated file list. **Suggested fix:** Treat as acceptable scope creep, or extend the plan’s file list when recording work.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## The plan’s NEVER text is a blanket rule: do **not** edit out-of-plan files; use `oos_observations[]`. The shipped bullets add **OOS triage Rule 1/2** exceptions that **require** inline edits even when the file is **not** under “Files to modify,” which contradicts the plan’s “instead of editing it” wording. **Suggested fix:** Match the plan verbatim in these prompts, or update the plan to document the triage overrides as the intended contract.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Important** (`correctness`) — `feature_description` vs [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) **653–660**  

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** (`correctness`) — `feature_description` vs [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) **653–660**  
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Important** (`correctness`) — `implementation_plan` Steps **3–4** vs [`agents/codex-implementer.md`](agents/codex-implementer.md) **54**, [`agents/cursor-implementer.md`](agents/cursor-implementer.md) **60**, [`agents/_implementer-base.md`](agents/_implementer-base.md) **34**  

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Important** (`correctness`) — `implementation_plan` Steps **3–4** vs [`agents/codex-implementer.md`](agents/codex-implementer.md) **54**, [`agents/cursor-implementer.md`](agents/cursor-implementer.md) **60**, [`agents/_implementer-base.md`](agents/_implementer-base.md) **34**  
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Important** (`risk-integration`) — [skills/implement/scripts/step2-implement.sh:653-657](skills/implement/scripts/step2-implement.sh) vs [feature_description](session): The shipped Step 7a.1 explicitly compares **only** `git status` paths to manifest `files_touched` / `tests_added_or_modified` and states it does **not** cross-reference the plan’s **“Files to modify”** section. The feature text you supplied calls for that third leg (plan scope vs tree vs manifest). **Scenario:** An implementer edits a file that is listed in the plan but omitted from `files_touched` (or the reverse: declared in manifest but not in plan); the dispatcher emits **no** 7a.1 signal for pure plan drift because the plan file is never read here. **Suggested fix:** Either parse the plan’s file list into the check (with clear normalization rules), or narrow the shipped contract/docs so operators are not told the dispatcher enforces plan scope.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** (`risk-integration`) — [skills/implement/scripts/step2-implement.sh:653-657](skills/implement/scripts/step2-implement.sh) vs [feature_description](session): The shipped Step 7a.1 explicitly compares **only** `git status` paths to manifest `files_touched` / `tests_added_or_modified` and states it does **not** cross-reference the plan’s **“Files to modify”** section. The feature text you supplied calls for that third leg (plan scope vs tree vs manifest). **Scenario:** An implementer edits a file that is listed in the plan but omitted from `files_touched` (or the reverse: declared in manifest but not in plan); the dispatcher emits **no** 7a.1 signal for pure plan drift because the plan file is never read here. **Suggested fix:** Either parse the plan’s file list into the check (with clear normalization rules), or narrow the shipped contract/docs so operators are not told the dispatcher enforces plan scope.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Important** `correctness` [skills/implement/scripts/step2-implement.sh:653]( /Users/zhupanov/larch5/skills/implement/scripts/step2-implement.sh:653 ): The new warning only computes working-tree paths minus manifest-declared paths, but the requested behavior also requires checking those paths against the plan’s “Files to modify” section. Concrete failing scenario: an implementer edits `SECURITY.md`, includes `SECURITY.md` in `manifest.files_touched`, and the dispatcher emits no warning even when the plan only allowed `skills/implement/scripts/step2-implement.sh`, `skills/implement/scripts/test-step2-dispatch.sh`, `agents/codex-implementer.md`, and `agents/cursor-implementer.md`. Parse the plan scope, compare both actual working-tree paths and manifest paths against it, and warn for any path outside the declared plan scope; add a regression where an out-of-plan file is manifest-declared.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [skills/implement/scripts/step2-implement.sh:653]( /Users/zhupanov/larch5/skills/implement/scripts/step2-implement.sh:653 ): The new warning only computes working-tree paths minus manifest-declared paths, but the requested behavior also requires checking those paths against the plan’s “Files to modify” section. Concrete failing scenario: an implementer edits `SECURITY.md`, includes `SECURITY.md` in `manifest.files_touched`, and the dispatcher emits no warning even when the plan only allowed `skills/implement/scripts/step2-implement.sh`, `skills/implement/scripts/test-step2-dispatch.sh`, `agents/codex-implementer.md`, and `agents/cursor-implementer.md`. Parse the plan scope, compare both actual working-tree paths and manifest paths against it, and warn for any path outside the declared plan scope; add a regression where an out-of-plan file is manifest-declared.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## **Important** `correctness` [skills/implement/scripts/step2-implement.sh:664]( /Users/zhupanov/larch5/skills/implement/scripts/step2-implement.sh:664 ): `git status --porcelain | awk '{print $NF}'` corrupts paths containing spaces, so the detector can warn on bogus paths or miss the real declared path. Concrete failing scenario: an implementer edits `docs/my file.md` and declares `docs/my file.md`; porcelain output is split by whitespace, so the comparison sees only `file.md` or a quoted fragment and logs a false OOS warning. Use a NUL-delimited status format and parse paths without whitespace splitting, then add a regression for a declared path containing spaces.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` [skills/implement/scripts/step2-implement.sh:664]( /Users/zhupanov/larch5/skills/implement/scripts/step2-implement.sh:664 ): `git status --porcelain | awk '{print $NF}'` corrupts paths containing spaces, so the detector can warn on bogus paths or miss the real declared path. Concrete failing scenario: an implementer edits `docs/my file.md` and declares `docs/my file.md`; porcelain output is split by whitespace, so the comparison sees only `file.md` or a quoted fragment and logs a false OOS warning. Use a NUL-delimited status format and parse paths without whitespace splitting, then add a regression for a declared path containing spaces.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## **Latent** (`correctness`) — [skills/implement/scripts/step2-implement.sh:669-679](skills/implement/scripts/step2-implement.sh): `git status --porcelain=v1 -z` is converted with `tr '\0' '\n'` then a line-based `awk`. **Scenario:** Unusual rename/copy states or path edge cases that `git` encodes across NUL-separated fields could be parsed into path tokens that do not match manifest paths one-for-one (false OOS or missed OOS). Rare in practice but possible under creative paths or future porcelain tweaks. **Suggested fix:** Prefer consuming `-z` with `read -d ''` in a loop (or `git diff --name-only` against `HEAD` for the complete path) instead of NUL→newline massaging.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Latent** (`correctness`) — [skills/implement/scripts/step2-implement.sh:669-679](skills/implement/scripts/step2-implement.sh): `git status --porcelain=v1 -z` is converted with `tr '\0' '\n'` then a line-based `awk`. **Scenario:** Unusual rename/copy states or path edge cases that `git` encodes across NUL-separated fields could be parsed into path tokens that do not match manifest paths one-for-one (false OOS or missed OOS). Rare in practice but possible under creative paths or future porcelain tweaks. **Suggested fix:** Prefer consuming `-z` with `read -d ''` in a loop (or `git diff --name-only` against `HEAD` for the complete path) instead of NUL→newline massaging.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## **Latent** (`correctness`) — [skills/implement/scripts/step2-implement.sh:681-683](skills/implement/scripts/step2-implement.sh): Manifest path enumeration uses `jq … 2>/dev/null` and falls through to `comm` even if `jq` fails or yields an empty manifest path set. **Scenario:** Unexpected manifest shape / IO glitch produces an empty `MANIFEST_PATHS_FILE` while the tree is dirty → **every** porcelain path becomes “OOS,” flooding `execution-issues.md` and drowning real signal. **Suggested fix:** Bail the 7a.1 branch (or emit a distinct “manifest path enumeration failed” warning) when `jq` exits non‑zero or returns no paths while porcelain is non‑empty and `status=complete` already passed schema (treat as invariant violation).

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **Latent** (`correctness`) — [skills/implement/scripts/step2-implement.sh:681-683](skills/implement/scripts/step2-implement.sh): Manifest path enumeration uses `jq … 2>/dev/null` and falls through to `comm` even if `jq` fails or yields an empty manifest path set. **Scenario:** Unexpected manifest shape / IO glitch produces an empty `MANIFEST_PATHS_FILE` while the tree is dirty → **every** porcelain path becomes “OOS,” flooding `execution-issues.md` and drowning real signal. **Suggested fix:** Bail the 7a.1 branch (or emit a distinct “manifest path enumeration failed” warning) when `jq` exits non‑zero or returns no paths while porcelain is non‑empty and `status=complete` already passed schema (treat as invariant violation).
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## **Latent** (`risk-integration`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) **405** and **667**  

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 4. **Latent** (`risk-integration`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) **405** and **667**  
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## **Latent** (`risk-integration`) — [skills/implement/scripts/step2-implement.sh:653-689](skills/implement/scripts/step2-implement.sh): The warning text admits paths **“may include pre-existing dirty files.”** **Scenario:** Operator (or a prior interrupted run) leaves unrelated dirty paths in the tree; external run completes with a truthful manifest. Step 7a.1 still lists those paths as “not declared,” implying the implementer bundled OOS work when the contamination is pre-existing. **Suggested fix:** Optionally diff against the recorded Step‑2 baseline snapshot (if available) or subtract paths dirty before launcher start, and tune the warning copy to distinguish “pre-existing dirty” vs “new since baseline.”

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Latent** (`risk-integration`) — [skills/implement/scripts/step2-implement.sh:653-689](skills/implement/scripts/step2-implement.sh): The warning text admits paths **“may include pre-existing dirty files.”** **Scenario:** Operator (or a prior interrupted run) leaves unrelated dirty paths in the tree; external run completes with a truthful manifest. Step 7a.1 still lists those paths as “not declared,” implying the implementer bundled OOS work when the contamination is pre-existing. **Suggested fix:** Optionally diff against the recorded Step‑2 baseline snapshot (if available) or subtract paths dirty before launcher start, and tune the warning copy to distinguish “pre-existing dirty” vs “new since baseline.”
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## **Nit** (`architecture`) — [skills/implement/scripts/step2-implement.sh:405](skills/implement/scripts/step2-implement.sh) and [skills/implement/scripts/step2-implement.sh:667](skills/implement/scripts/step2-implement.sh): The Step 7a.1 block replaces the prior `EXIT` trap with a wider cleanup that still includes `"$LAUNCHER_TMP"` (so no obvious `LAUNCHER_TMP` leak). **Scenario:** OOS temp files stay until process exit rather than end of the block; benign tmpdir churn under heavy use. **Suggested fix:** `trap - EXIT` restore plus explicit `rm -f` of the three OOS temps at block end, or a scoped subshell—optional hygiene only.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 6. **Nit** (`architecture`) — [skills/implement/scripts/step2-implement.sh:405](skills/implement/scripts/step2-implement.sh) and [skills/implement/scripts/step2-implement.sh:667](skills/implement/scripts/step2-implement.sh): The Step 7a.1 block replaces the prior `EXIT` trap with a wider cleanup that still includes `"$LAUNCHER_TMP"` (so no obvious `LAUNCHER_TMP` leak). **Scenario:** OOS temp files stay until process exit rather than end of the block; benign tmpdir churn under heavy use. **Suggested fix:** `trap - EXIT` restore plus explicit `rm -f` of the three OOS temps at block end, or a scoped subshell—optional hygiene only.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## **Nit** (`architecture`) — `implementation_plan` section **“Files to modify”** vs branch diff  

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. **Nit** (`architecture`) — `implementation_plan` section **“Files to modify”** vs branch diff  
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## **Nit** (`code-quality`) — [agents/codex-implementer.md:45-54](agents/codex-implementer.md), [agents/cursor-implementer.md:51-60](agents/cursor-implementer.md), [agents/gemini-implementer.md:51-60](agents/gemini-implementer.md): The Hard guards preamble still says every violation **MUST** abort with `status=bailed`, while NEVER **#8** instructs a softer behavior (triage exceptions + `oos_observations[]` instead of editing). **Scenario:** Prompt-only confusion for the model, not a runtime bug. **Suggested fix:** Add one clarifying sentence: e.g. “NEVER #8 is scope discipline; violating it after the fact is a process failure surfaced by Step 7a.1 / review, not a separate automatic bail token.”

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 5. **Nit** (`code-quality`) — [agents/codex-implementer.md:45-54](agents/codex-implementer.md), [agents/cursor-implementer.md:51-60](agents/cursor-implementer.md), [agents/gemini-implementer.md:51-60](agents/gemini-implementer.md): The Hard guards preamble still says every violation **MUST** abort with `status=bailed`, while NEVER **#8** instructs a softer behavior (triage exceptions + `oos_observations[]` instead of editing). **Scenario:** Prompt-only confusion for the model, not a runtime bug. **Suggested fix:** Add one clarifying sentence: e.g. “NEVER #8 is scope discipline; violating it after the fact is a process failure surfaced by Step 7a.1 / review, not a separate automatic bail token.”
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## **Note:** Per your constraints, no `.tsv` file was written on disk; paste the block above if you need a sidecar file.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## **Read-only constraint:** I did not write the TSV sidecar to disk (that would violate your mutation ban). The same records appear in a fenced block at the end.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## **TSV (intended sidecar content; not written to disk per read-only rule)**

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## ---

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	feature_description vs skills/implement/scripts/step2-implement.sh:653-660	Step 7a.1 does not cross-reference the plan Files to modify section as required by the feature text.	An implementer can touch only plan-out-of-scope files yet declare every path in files_touched; no Warning fires and plan-scope contamination stays undetected by this check.	Parse the plan file list or adjust the feature requirement to match manifest-only comparison.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	implementation_plan Steps 3-4 vs agents/codex-implementer.md:54 agents/cursor-implementer.md:60 agents/_implementer-base.md:34	NEVER bullets add OOS triage Rule 1/2 inline-edit exceptions not present in the plan verbatim text.	The plan promised a blanket prohibition on editing out-of-plan files; prompts now authorize mandatory inline edits outside Files to modify under triage, conflicting with the supplied plan block.	Align prompts with the plan wording or revise the plan to include triage overrides explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-657	Step 7a.1 does not read the plan Files to modify list despite feature text calling for that cross-check.	Plan-only scope drift (file in plan but not in manifest, or extra manifest file vs plan) produces no 7a.1 signal; operators may believe plan scope is mechanically enforced.	Implement plan-file parsing into the check, or align public contract/docs with manifest-vs-tree-only behavior.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:669-679	porcelain -z converted via tr then line awk may mishandle exotic rename/copy encodings.	Uncommon git encodings or unusual paths could yield false OOS or missed OOS vs manifest strings.	Consume NUL records with read -d '' or use a name-only diff against HEAD for complete paths.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:681-683	jq errors to manifest path list are swallowed; empty manifest path set vs non-empty porcelain yields all paths reported OOS.	jq/IO failure or empty extraction makes every dirty path look undeclared, flooding execution-issues and hiding real OOS bundles.	Detect jq failure or empty manifest path set when porcelain non-empty; emit a distinct failure/warning instead of comm-based OOS flood.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	skills/implement/scripts/step2-implement.sh:405-667	7a.1 replaces the prior EXIT trap when that block runs.	Future extensions to the line-405 EXIT handler could be dropped for complete runs that execute 7a.1.	Use a single EXIT cleanup path or append cleanup without overwriting unrelated trap duties.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	skills/implement/scripts/step2-implement.sh:653-689	Warning conflates implementer-side undeclared edits with any pre-existing dirty paths.	Pre-existing dirty files make the Warning blame the external implementer for paths it never touched, weakening trust in the signal.	Subtract baseline/pre-launcher dirty set or reword and split categories when pre-existing paths are detected.
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	architecture	implementation_plan Files to modify vs branch diff	Additional files touched beyond the four listed in the plan.	None by itself; traceability noise for reviewers auditing plan-to-diff mapping.	Update the plan file list or accept as collateral and document.
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	architecture	skills/implement/scripts/step2-implement.sh:405,667	EXIT trap replaced to add OOS temp cleanup; OOS temps live until shell exit.	High-frequency runs leave short-lived clutter in tmpdir until dispatcher exits.	Optional explicit rm at block end or trap restore if churn matters.
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	agents/codex-implementer.md:45-54 (also cursor/gemini parallels)	Hard-guard header says every NEVER violation must bail while NEVER #8 describes triage and oos_observations without a bail pairing.	Model may hesitate or mis-rank severity of scope violations versus true bail guards.	Clarify in one sentence how NEVER #8 relates to the bail rule and to Step 7a.1/review backstops.
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	code-quality	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/*	Committed run-log flush adds churn unrelated to dispatcher logic.	Noise in review and git history for consumers auditing the functional change.	Keep log flushes on a separate chore cadence or exclude from functional PRs when possible.
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## Checking EXIT trap interaction and completing Test 18 assertions.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## Checking EXIT-trap usage and surrounding context in `step2-implement.sh` — the new block installs `trap ... EXIT`, which may overwrite an existing EXIT trap.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## Checking for additional `trap` assignments after line 667 and verifying the diff’s `awk` porcelain handling vs. the workspace.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_36: panel [code-review/accepted]

## Checking hard-guard wording and whether `emit_bailed` exits the shell before the overwritten trap matters:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## Checking how `PLAN` is used in tests and whether a baseline snapshot exists for OOS detection:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## Checking the diff for `larch-logs` and whether the cached diff matches the workspace `step2-implement.sh` OOS block.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_39: panel [code-review/accepted]

## Checking whether `append-execution-issue` expects `--category Warnings` and scanning the diff for `_implementer-base` / SECURITY intent.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_40: panel [code-review/accepted]

## Commits on the branch since `merge-base` with `main`:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## Commits on this branch vs `main` (from your command):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## Creating the review plan. Findings are based on the pre-computed diff at the given path; the workspace copy of `step2-implement.sh` may differ (e.g. porcelain `-z` handling).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## Having compared the cached diff with the working tree: `step2-implement.sh` in the repo improves path handling vs. the diff excerpt. Reviewing the diff file for `step2-implement.sh` only (lines 413–488) — it used `git status --porcelain` with `awk 'NF {print $NF}'`, which mishandles paths with spaces. Final branch may differ.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## Inspecting `step2-implement.sh` for trap interactions and reading the remainder of Test 18.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## Note: the cached `diff.txt` shows an earlier `step2-implement.sh` hunk (`awk 'NF {print $NF}'`); your working tree has a more elaborate Step 7a.1 (`porcelain=v1 -z`, NUL handling, and explicit comments that the plan is **not** consulted). Findings below use the **current workspace** copies of the touched files so line numbers match what you merge.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_46: panel [code-review/accepted]

## Noting a discrepancy: the cached `diff.txt` shows a simpler OOS block than the current workspace `step2-implement.sh`. Reviewing both: requirements vs. workspace (authoritative if that's what merges).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_47: panel [code-review/accepted]

## Read-only mode: the instructions asked for a TSV **sidecar file**; that would require writing a file, which your HARD CONSTRAINTS forbid. Below is the same TSV content you can save manually (e.g. as `review.tsv`).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## Reading implementation sections in the repo for full context (diff may be truncated).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_49: panel [code-review/accepted]

## Reading trap setup and `LAUNCHER_TMP` lifecycle in `step2-implement.sh`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_50: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: Gathering the pre-computed diff and commit list, then reviewing changed files for correctness vs. the plan and feature description.
- **Suggested revision**: Address the concern above.

### FINDING_51: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Gathering the diff, commit list, and targeted file reads for an edge-case-focused review. Read-only: we won't write the TSV sidecar to disk (conflicts with your mutation ban); we'll provide the TSV block in the reply.
- **Suggested revision**: Address the concern above.

### FINDING_52: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Gathering the precomputed diff and commit history for a read-only Plan Fidelity review.
- **Suggested revision**: Address the concern above.

### FINDING_53: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: Gathering the pre-computed diff and commit history for a read-only security-focused review. We can't write the `.tsv` sidecar to disk (read-only constraint); we'll include TSV records in the response.
- **Suggested revision**: Address the concern above.

### FINDING_54: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Gathering the branch diff and commit history for a read-only review. Reading the precomputed diff and running a non-mutating `git log`.
- **Suggested revision**: Address the concern above.

### FINDING_55: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: Gathering the branch diff and commit history for a read-only review (no file writes). Reading the pre-computed diff and running read-only git commands.
- **Suggested revision**: Address the concern above.

### FINDING_56: panel [code-review/accepted]

## Reviewing committed `HEAD` (matches the pre-computed diff): OOS logic uses `awk '{print $NF}'` on non-null porcelain; feature text requires plan cross-reference, which the implementation omits; prompts add Hard guard #8 while OOS triage still mandates inline folds for doc drift and small bugs.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_57: panel [code-review/accepted]

## Searching the diff for plan-relevant files and reading those hunks.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_58: panel [code-review/accepted]

## Searching the diff for relevant files and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_59: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_60: panel [code-review/accepted]

## Searching the large diff for relevant hunks.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_61: panel [code-review/accepted]

## Verifying whether `docs/linting.md` lists assertion counts and whether the diff's `step2` hunk matches the workspace (porcelain parsing).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_62: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`architecture`) — `larch-logs/implement/2B036492-...` and commit `59c4f13`  

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Nit** (`architecture`) — `larch-logs/implement/2B036492-...` and commit `59c4f13`  
- **Suggested revision**: Address the concern above.

### FINDING_63: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`code-quality`) — Commit `59c4f13` and the `larch-logs/implement/…` artifact updates are operational log flush noise relative to the OOS-bundle feature; they widen review surface without changing dispatcher logic. Out of scope for judging the Step 7a.1 design.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Nit** (`code-quality`) — Commit `59c4f13` and the `larch-logs/implement/…` artifact updates are operational log flush noise relative to the OOS-bundle feature; they widen review surface without changing dispatcher logic. Out of scope for judging the Step 7a.1 design.
- **Suggested revision**: Address the concern above.

### FINDING_64: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: codex-generalist-output.txt
- **Concern**: No out-of-scope observations.
- **Suggested revision**: Address the concern above.

### FINDING_65: panel [code-review/accepted]

## `59c4f13` — chore(larch-logs): flush implement run …

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `59c4f13` — chore(larch-logs): flush implement run …
- **Suggested revision**: Address the concern above.

### FINDING_66: panel [code-review/accepted]

## `59c4f13` — chore(larch-logs): flush implement run …

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `59c4f13` — chore(larch-logs): flush implement run …
- **Suggested revision**: Address the concern above.

### FINDING_67: panel [code-review/accepted]

## `68099ed` — Warn on undeclared implementer files

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `68099ed` — Warn on undeclared implementer files
- **Suggested revision**: Address the concern above.

### FINDING_68: panel [code-review/accepted]

## `68099ed` — Warn on undeclared implementer files

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `68099ed` — Warn on undeclared implementer files
- **Suggested revision**: Address the concern above.

### FINDING_69: panel [code-review/accepted]

## ```

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_70: panel [code-review/accepted]

## ```text

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_71: panel [code-review/accepted]

## schema_version

- **Reviewer**: scope
- **Concern**: severity	focus_area	location	what	scenario_or_breakage	suggested_fix
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## The new detector never cross-references `$PLAN_FILE` / the plan’s “Files to modify” section; it only computes `working-tree paths - manifest paths` at `skills/implement/scripts/step2-implement.sh:664-670`. Concrete failing scenario: if the plan allows only `README.md`, but the implementer edits `README.md` and `docs/extra.md` and declares both in `manifest.files_touched`, `comm -23` is empty and no Warning is written before `git add -A` commits both files. Fix by parsing the plan-scoped allowed file list and warning for working-tree or manifest-declared paths outside that list; add a regression where the undeclared-to-plan file is declared in the manifest.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## `git status --porcelain | awk 'NF {print $NF}'` misparses valid paths containing spaces or quoted/special characters, causing false OOS warnings for correctly declared files. Concrete failing scenario: an implementer edits and declares `docs/my file.md`; porcelain emits a path with whitespace, `awk` records only `file.md`, and the dispatcher warns even though the manifest matches the actual file. Fix by using `git status --porcelain=v1 -z` and NUL-delimited parsing, and add coverage for a declared path containing a space.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## ### Structured TSV (not written to disk per read-only constraint)

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## ### Structured TSV (sidecar payload — not written to disk per read-only constraint)

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## ### TSV sidecar (not written to disk — read-only constraint)

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Commits** (`$(git merge-base HEAD main)..HEAD`): `68099ed Warn on undeclared implementer files`, `59c4f13 chore(larch-logs): flush implement run …`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Commits** (`git merge-base HEAD main`..`HEAD`): `59c4f13 chore(larch-logs): flush implement run 2B036492-1DB7-464A-B254-4E6BB9D63853`, `68099ed Warn on undeclared implementer files`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Hard constraint**: I did not create or edit any files (including the `.tsv` sidecar). The TSV block at the end is the sidecar payload you can save manually if your pipeline expects a file.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Important** (`code-quality`) [agents/_implementer-base.md:64-73](agents/_implementer-base.md), [agents/codex-implementer.md:110-119](agents/codex-implementer.md), [agents/cursor-implementer.md:156-165](agents/cursor-implementer.md), [agents/gemini-implementer.md:202-211](agents/gemini-implementer.md) — The **Hard guards** preamble still says violations **MUST** abort with `status=bailed`, but the new scope rule tells the model to keep going and use `oos_observations[]`. **Scenario:** Prompt-level contradiction: models may over-bail, under-apply the new rule, or randomize between “bail” vs “observe.” **Fix:** Carve out the scope rule from the unconditional bail set or reword the preamble (“except where a guard explicitly directs non-bail handling”).

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Important** (`code-quality`) [agents/_implementer-base.md:64-73](agents/_implementer-base.md), [agents/codex-implementer.md:110-119](agents/codex-implementer.md), [agents/cursor-implementer.md:156-165](agents/cursor-implementer.md), [agents/gemini-implementer.md:202-211](agents/gemini-implementer.md) — The **Hard guards** preamble still says violations **MUST** abort with `status=bailed`, but the new scope rule tells the model to keep going and use `oos_observations[]`. **Scenario:** Prompt-level contradiction: models may over-bail, under-apply the new rule, or randomize between “bail” vs “observe.” **Fix:** Carve out the scope rule from the unconditional bail set or reword the preamble (“except where a guard explicitly directs non-bail handling”).
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## **Important** (`code-quality`, `requirements`) [skills/implement/scripts/step2-implement.sh:653-691](skills/implement/scripts/step2-implement.sh) (committed `HEAD` OOS block) — The feature/plan called for cross-referencing the working tree against both the manifest **and** the plan’s **“Files to modify”** section. The shipped logic only diffs `git status` paths vs `files_touched` / `tests_added_or_modified`. **Scenario:** An implementer touches only plan-listed files but under-declares the manifest (or vice versa: declares extra files never in the plan); plan-scope drift is never surfaced by this check. **Fix:** Parse `--plan-file` for that section and include those paths in the allowed set (or explicitly document and ticket the reduced scope).

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** (`code-quality`, `requirements`) [skills/implement/scripts/step2-implement.sh:653-691](skills/implement/scripts/step2-implement.sh) (committed `HEAD` OOS block) — The feature/plan called for cross-referencing the working tree against both the manifest **and** the plan’s **“Files to modify”** section. The shipped logic only diffs `git status` paths vs `files_touched` / `tests_added_or_modified`. **Scenario:** An implementer touches only plan-listed files but under-declares the manifest (or vice versa: declares extra files never in the plan); plan-scope drift is never surfaced by this check. **Fix:** Parse `--plan-file` for that section and include those paths in the allowed set (or explicitly document and ticket the reduced scope).
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## **Important** (`correctness`) [skills/implement/scripts/step2-implement.sh:669-671](skills/implement/scripts/step2-implement.sh) — `git status --porcelain | awk 'NF {print $NF}'` assumes the path is the last whitespace token. **Scenario:** Repo-relative paths containing spaces, or unusual porcelain rows, yield wrong tokens or merged tokens, so `comm -23` miscomputes OOS (false negatives or garbage “paths” in the Warning). **Fix:** Use `git status --porcelain=v1 -z` and parse NUL-separated records (as in your uncommitted workspace sketch).

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Important** (`correctness`) [skills/implement/scripts/step2-implement.sh:669-671](skills/implement/scripts/step2-implement.sh) — `git status --porcelain | awk 'NF {print $NF}'` assumes the path is the last whitespace token. **Scenario:** Repo-relative paths containing spaces, or unusual porcelain rows, yield wrong tokens or merged tokens, so `comm -23` miscomputes OOS (false negatives or garbage “paths” in the Warning). **Fix:** Use `git status --porcelain=v1 -z` and parse NUL-separated records (as in your uncommitted workspace sketch).
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## **Important** (`correctness`) — **feature_description** (plan-scope cross-reference) vs [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) (diff hunk ~438–466). The product/feature text requires cross-referencing working-tree changes and `files_touched` **against the plan’s “Files to modify”** section; Step 1 of the **implementation_plan** and the shipped hunk only compare `git status --porcelain` paths to manifest paths (`comm -23`), with no `$PLAN`/plan-file parse. **Concrete breakage:** a file both present in the tree and listed in `files_touched` but **not** in the plan’s allowed list never surfaces as plan-scope drift; only manifest-vs-tree gaps are warned. **Suggested fix:** parse the plan’s “Files to modify” list (same source `/implement` already passes as `--plan-file`) and extend the warning logic (e.g. flag paths in the union/plan diff not covered by the plan section, or tighten the warning text to match what is actually checked).

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** (`correctness`) — **feature_description** (plan-scope cross-reference) vs [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) (diff hunk ~438–466). The product/feature text requires cross-referencing working-tree changes and `files_touched` **against the plan’s “Files to modify”** section; Step 1 of the **implementation_plan** and the shipped hunk only compare `git status --porcelain` paths to manifest paths (`comm -23`), with no `$PLAN`/plan-file parse. **Concrete breakage:** a file both present in the tree and listed in `files_touched` but **not** in the plan’s allowed list never surfaces as plan-scope drift; only manifest-vs-tree gaps are warned. **Suggested fix:** parse the plan’s “Files to modify” list (same source `/implement` already passes as `--plan-file`) and extend the warning logic (e.g. flag paths in the union/plan diff not covered by the plan section, or tighten the warning text to match what is actually checked).
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## **Important** (`correctness`) — **implementation_plan** Step 4 (“After NEVER #6, add NEVER **#7** … parity”) vs [`agents/cursor-implementer.md`](agents/cursor-implementer.md) (diff ~163–165; current file [`agents/cursor-implementer.md:58-60`](agents/cursor-implementer.md)). The new scope rule is numbered **8** and placed **after** the existing “Control artifacts …” **#7**, instead of being inserted as **#7** after repo-root rule **#6** with “Control artifacts” renumbered to **#8**. **Concrete breakage:** any operator or automation that keys off the plan’s “NEVER #7” wording for Cursor points at the wrong bullet (control artifacts vs scope). **Suggested fix:** insert the scope bullet as item 7 immediately after item 6 and renumber “Control artifacts” to 8.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Important** (`correctness`) — **implementation_plan** Step 4 (“After NEVER #6, add NEVER **#7** … parity”) vs [`agents/cursor-implementer.md`](agents/cursor-implementer.md) (diff ~163–165; current file [`agents/cursor-implementer.md:58-60`](agents/cursor-implementer.md)). The new scope rule is numbered **8** and placed **after** the existing “Control artifacts …” **#7**, instead of being inserted as **#7** after repo-root rule **#6** with “Control artifacts” renumbered to **#8**. **Concrete breakage:** any operator or automation that keys off the plan’s “NEVER #7” wording for Cursor points at the wrong bullet (control artifacts vs scope). **Suggested fix:** insert the scope bullet as item 7 immediately after item 6 and renumber “Control artifacts” to 8.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## **Important** (`correctness`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) (diff ~449–451). Working-tree paths are derived with `git status --porcelain | awk 'NF {print $NF}'`. **Concrete breakage:** porcelain paths that contain spaces (or other non-standard first-column layouts) yield a **wrong final token**, so OOS detection can miss real changes or attribute noise to the wrong path. **Suggested fix:** NUL-delimited `git status --porcelain=v1 -z` parsing (or an equivalent robust path extractor), matching the plan’s edge-case intent for renames/new paths.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. **Important** (`correctness`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) (diff ~449–451). Working-tree paths are derived with `git status --porcelain | awk 'NF {print $NF}'`. **Concrete breakage:** porcelain paths that contain spaces (or other non-standard first-column layouts) yield a **wrong final token**, so OOS detection can miss real changes or attribute noise to the wrong path. **Suggested fix:** NUL-delimited `git status --porcelain=v1 -z` parsing (or an equivalent robust path extractor), matching the plan’s edge-case intent for renames/new paths.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## **Important** (`risk-integration`) [skills/implement/scripts/step2-implement.sh:674-681](skills/implement/scripts/step2-implement.sh) — The Warning copy attributes paths to the **“external implementer”**, but `git status` includes **any** dirty path in `$REPO_ROOT`, including operator preloads called out elsewhere in the same prompts. **Scenario:** Operator leaves an unrelated dirty file; dispatcher logs a false “implementer OOS” Warning and wastes review attention. **Fix:** Qualify the message (“may include pre-existing dirty paths”) and/or diff against a baseline snapshot taken before the launcher.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 5. **Important** (`risk-integration`) [skills/implement/scripts/step2-implement.sh:674-681](skills/implement/scripts/step2-implement.sh) — The Warning copy attributes paths to the **“external implementer”**, but `git status` includes **any** dirty path in `$REPO_ROOT`, including operator preloads called out elsewhere in the same prompts. **Scenario:** Operator leaves an unrelated dirty file; dispatcher logs a false “implementer OOS” Warning and wastes review attention. **Fix:** Qualify the message (“may include pre-existing dirty paths”) and/or diff against a baseline snapshot taken before the launcher.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## **Important** (`risk-integration`, `plan`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~653–658 (and OOS logic following): The requested behavior was to cross-reference the plan’s **“Files to modify”** section with the working tree and manifest. The shipped logic only compares `git status` paths to `files_touched` / `tests_added_or_modified`; the script explicitly documents that it does **not** parse the plan for scope. **Scenario:** An implementer edits only files listed in the plan but omits one from `files_touched` (or lists extras only in the plan) — no Warning; edits that violate the plan but are declared in the manifest produce no OOS signal relative to the plan. **Fix:** Parse `PLAN_FILE` for the “Files to modify” list (or structured export), union/intersect with manifest paths as specified, then diff against porcelain.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`, `plan`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~653–658 (and OOS logic following): The requested behavior was to cross-reference the plan’s **“Files to modify”** section with the working tree and manifest. The shipped logic only compares `git status` paths to `files_touched` / `tests_added_or_modified`; the script explicitly documents that it does **not** parse the plan for scope. **Scenario:** An implementer edits only files listed in the plan but omits one from `files_touched` (or lists extras only in the plan) — no Warning; edits that violate the plan but are declared in the manifest produce no OOS signal relative to the plan. **Fix:** Parse `PLAN_FILE` for the “Files to modify” list (or structured export), union/intersect with manifest paths as specified, then diff against porcelain.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## **Important** (`risk-integration`, `plan`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~680–691: When `jq` yields no path lines (`jq_out` empty) and the working tree is non-empty, the code appends *“could not extract declared paths… OOS check skipped”* instead of treating every dirty path as OOS. The plan’s edge case called for: empty `files_touched` ⇒ **all** working-tree changes reported as OOS. **Scenario:** Valid manifest with empty `files_touched`/`tests_added_or_modified` and real edits on disk — operators get a vague skip warning, not an enumerated OOS list, so contamination is harder to triage. **Fix:** Distinguish jq failure from legitimately empty declarations; on empty declaration + non-empty porcelain, run the full `comm -23` path (all WT paths OOS).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Important** (`risk-integration`, `plan`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~680–691: When `jq` yields no path lines (`jq_out` empty) and the working tree is non-empty, the code appends *“could not extract declared paths… OOS check skipped”* instead of treating every dirty path as OOS. The plan’s edge case called for: empty `files_touched` ⇒ **all** working-tree changes reported as OOS. **Scenario:** Valid manifest with empty `files_touched`/`tests_added_or_modified` and real edits on disk — operators get a vague skip warning, not an enumerated OOS list, so contamination is harder to triage. **Fix:** Distinguish jq failure from legitimately empty declarations; on empty declaration + non-empty porcelain, run the full `comm -23` path (all WT paths OOS).
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## **Important** `correctness` (source: `plan`) — [skills/implement/scripts/step2-implement.sh](skills/implement/scripts/step2-implement.sh) (diff lines 449–451): `git status --porcelain | awk 'NF {print $NF}'` treats the **last whitespace-separated token** as the path. **Scenario**: An untracked or modified path containing spaces (e.g. `?? foo bar.txt`) yields `$NF` = `bar.txt`; `comm` compares the wrong string, so OOS detection misses the real path or mis-counts duplicates. **Suggested fix**: Use NUL-terminated porcelain (`git status --porcelain=v1 -z` + `read -d ''`) or another parser that respects `core.quotePath` / quoted paths.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 4. **Important** `correctness` (source: `plan`) — [skills/implement/scripts/step2-implement.sh](skills/implement/scripts/step2-implement.sh) (diff lines 449–451): `git status --porcelain | awk 'NF {print $NF}'` treats the **last whitespace-separated token** as the path. **Scenario**: An untracked or modified path containing spaces (e.g. `?? foo bar.txt`) yields `$NF` = `bar.txt`; `comm` compares the wrong string, so OOS detection misses the real path or mis-counts duplicates. **Suggested fix**: Use NUL-terminated porcelain (`git status --porcelain=v1 -z` + `read -d ''`) or another parser that respects `core.quotePath` / quoted paths.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## **Important** `correctness` `completeness w.r.t. requirements` (source: `requirements`) — [skills/implement/scripts/step2-implement.sh](skills/implement/scripts/step2-implement.sh) (new block in diff after the Step 7a `paths_invalid` bail, approx. diff lines 438–466 in `diff.txt`): The feature text requires cross-referencing the working tree not only against the manifest but also against the plan’s **“Files to modify”** section; the diff only implements `git status --porcelain` paths minus manifest `files_touched` / `tests_added_or_modified`. **Scenario**: Implementer edits a file listed in the plan but forgets to add it to `files_touched`; that path is still “in plan scope” but is **not** reported as OOS, so the warning does not surface the mismatch the feature asked for. **Suggested fix**: Parse the plan file (same `--plan-file` the dispatcher already receives), collect declared paths, and include `(wt \setminus manifest) ∪ (wt \setminus plan_files)` (or equivalent) in the warning logic, or narrow the documented product requirement to “manifest vs tree only”.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Important** `correctness` `completeness w.r.t. requirements` (source: `requirements`) — [skills/implement/scripts/step2-implement.sh](skills/implement/scripts/step2-implement.sh) (new block in diff after the Step 7a `paths_invalid` bail, approx. diff lines 438–466 in `diff.txt`): The feature text requires cross-referencing the working tree not only against the manifest but also against the plan’s **“Files to modify”** section; the diff only implements `git status --porcelain` paths minus manifest `files_touched` / `tests_added_or_modified`. **Scenario**: Implementer edits a file listed in the plan but forgets to add it to `files_touched`; that path is still “in plan scope” but is **not** reported as OOS, so the warning does not surface the mismatch the feature asked for. **Suggested fix**: Parse the plan file (same `--plan-file` the dispatcher already receives), collect declared paths, and include `(wt \setminus manifest) ∪ (wt \setminus plan_files)` (or equivalent) in the warning logic, or narrow the documented product requirement to “manifest vs tree only”.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## **Important** `correctness` `plan-correctness` (source: `both`) — [agents/_implementer-base.md](agents/_implementer-base.md) (diff lines 62–73): The “## Hard guards” preamble still says *“Violating any of them MUST cause you to abort with `status=bailed`”* while the new item **8** describes scope discipline that the dispatcher handles with a **non-bailing** Warning in `step2-implement.sh`. **Scenario**: A model treats every numbered “NEVER” under Hard guards as a hard bail trigger and bails on any accidental out-of-scope touch, or conversely assumes post-hoc warnings mean other NEVER rules are also soft. **Suggested fix**: Move the scope rule out of “Hard guards”, or qualify the preamble (e.g. “items 1–7” / “except item 8”), or explicitly state that item 8 is enforced by the dispatcher as a Warning, not as a `status=bailed` trigger.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Important** `correctness` `plan-correctness` (source: `both`) — [agents/_implementer-base.md](agents/_implementer-base.md) (diff lines 62–73): The “## Hard guards” preamble still says *“Violating any of them MUST cause you to abort with `status=bailed`”* while the new item **8** describes scope discipline that the dispatcher handles with a **non-bailing** Warning in `step2-implement.sh`. **Scenario**: A model treats every numbered “NEVER” under Hard guards as a hard bail trigger and bails on any accidental out-of-scope touch, or conversely assumes post-hoc warnings mean other NEVER rules are also soft. **Suggested fix**: Move the scope rule out of “Hard guards”, or qualify the preamble (e.g. “items 1–7” / “except item 8”), or explicitly state that item 8 is enforced by the dispatcher as a Warning, not as a `status=bailed` trigger.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## **Important** `correctness` `plan-correctness` (source: `plan`) — Same agent diff as above propagates through [agents/codex-implementer.md](agents/codex-implementer.md), [agents/cursor-implementer.md](agents/cursor-implementer.md), and [agents/gemini-implementer.md](agents/gemini-implementer.md): The internal “MUST `status=bailed`” framing now conflicts with the new rule’s enforcement story. **Scenario**: Same ambiguous bail behavior for all three external implementers. **Suggested fix**: Regenerate prompts from an updated `_implementer-base.md` after fixing the section structure so Codex/Cursor/Gemini stay aligned.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **Important** `correctness` `plan-correctness` (source: `plan`) — Same agent diff as above propagates through [agents/codex-implementer.md](agents/codex-implementer.md), [agents/cursor-implementer.md](agents/cursor-implementer.md), and [agents/gemini-implementer.md](agents/gemini-implementer.md): The internal “MUST `status=bailed`” framing now conflicts with the new rule’s enforcement story. **Scenario**: Same ambiguous bail behavior for all three external implementers. **Suggested fix**: Regenerate prompts from an updated `_implementer-base.md` after fixing the section structure so Codex/Cursor/Gemini stay aligned.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## **Important** `correctness` — `skills/implement/scripts/step2-implement.sh:664`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `skills/implement/scripts/step2-implement.sh:664`  
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## **Important** `correctness` — `skills/implement/scripts/step2-implement.sh:664`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` — `skills/implement/scripts/step2-implement.sh:664`  
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## **Important**, **architecture**, [`skills/implement/scripts/step2-implement.sh:656-658`](skills/implement/scripts/step2-implement.sh) vs. the stated feature: The shipped check **does not** cross-reference the plan’s **“Files to modify”** section—only manifest-declared paths vs. the working tree, and the script documents that limitation. **Scenario:** An implementer faithfully lists every touched file in `files_touched` but edits files outside the plan scope; no Step 7a.1 signal fires, so the feature goal in the prompt is not met mechanically. **Fix:** Parse the plan artifact the dispatcher already has (`--plan-file`) for that section (robustly) and add a second diff (or reuse parsed paths) in addition to the manifest cross-check, or narrow the product wording so docs and prompts do not claim plan-scope detection.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Important**, **architecture**, [`skills/implement/scripts/step2-implement.sh:656-658`](skills/implement/scripts/step2-implement.sh) vs. the stated feature: The shipped check **does not** cross-reference the plan’s **“Files to modify”** section—only manifest-declared paths vs. the working tree, and the script documents that limitation. **Scenario:** An implementer faithfully lists every touched file in `files_touched` but edits files outside the plan scope; no Step 7a.1 signal fires, so the feature goal in the prompt is not met mechanically. **Fix:** Parse the plan artifact the dispatcher already has (`--plan-file`) for that section (robustly) and add a second diff (or reuse parsed paths) in addition to the manifest cross-check, or narrow the product wording so docs and prompts do not claim plan-scope detection.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## **Important**, **correctness**, [`skills/implement/scripts/step2-implement.sh:673-677`](skills/implement/scripts/step2-implement.sh): Working-tree paths are derived with `printf '%s\n' "${record##* }"` on each `git status --porcelain=v1 -z` record. That takes only the **last whitespace-delimited token**, not the full path tail after the two-letter status and separating space. **Scenario:** Porcelain lines where the path is quoted or contains spaces (or rename/other multi-token layouts) produce truncated or quoted fragments, so `comm` mis-classifies paths (false “undeclared” warnings or missed real OOS paths). **Fix:** Derive the path with the porcelain contract (fixed `XY ` prefix strip and optional unquoting), or avoid hand-parsing and use something like `git -C "$REPO_ROOT" diff --name-only -z "$BASELINE_SHA"` (or another stable name list) aligned with what “changed since baseline” should mean for this check.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Important**, **correctness**, [`skills/implement/scripts/step2-implement.sh:673-677`](skills/implement/scripts/step2-implement.sh): Working-tree paths are derived with `printf '%s\n' "${record##* }"` on each `git status --porcelain=v1 -z` record. That takes only the **last whitespace-delimited token**, not the full path tail after the two-letter status and separating space. **Scenario:** Porcelain lines where the path is quoted or contains spaces (or rename/other multi-token layouts) produce truncated or quoted fragments, so `comm` mis-classifies paths (false “undeclared” warnings or missed real OOS paths). **Fix:** Derive the path with the porcelain contract (fixed `XY ` prefix strip and optional unquoting), or avoid hand-parsing and use something like `git -C "$REPO_ROOT" diff --name-only -z "$BASELINE_SHA"` (or another stable name list) aligned with what “changed since baseline” should mean for this check.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## **Important**, **security**, [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json:242-243`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json): The chore commit adds a tracked manifest containing `operator_cwd` and `operator_repo_root` with a real home-style absolute path. **Scenario:** Anyone cloning the public repo sees the operator’s local directory layout (hostname/username is often inferable from `~/...`), which is unnecessary information disclosure for a security-sensitive automation repo. **Fix:** Do not commit session logs that embed absolute operator paths, or redact/normalize those fields before commit; keep run logs local or in gitignored storage.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Important**, **security**, [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json:242-243`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json): The chore commit adds a tracked manifest containing `operator_cwd` and `operator_repo_root` with a real home-style absolute path. **Scenario:** Anyone cloning the public repo sees the operator’s local directory layout (hostname/username is often inferable from `~/...`), which is unnecessary information disclosure for a security-sensitive automation repo. **Fix:** Do not commit session logs that embed absolute operator paths, or redact/normalize those fields before commit; keep run logs local or in gitignored storage.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## **Latent** (`correctness`) [skills/implement/scripts/step2-implement.sh:658-691](skills/implement/scripts/step2-implement.sh) — Under `set -o pipefail`, a failing `jq … | sort` pipeline inside `{ … } || true` aborts the compound command silently (no `append-execution-issue` path). **Scenario:** Manifest JSON readable by earlier `jq` calls but failing on this specific query edge case leaves contamination unwarned. **Fix:** Log a Warning when the OOS sub-block cannot run, or isolate `jq` with `|| true` and explicit empty handling.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 4. **Latent** (`correctness`) [skills/implement/scripts/step2-implement.sh:658-691](skills/implement/scripts/step2-implement.sh) — Under `set -o pipefail`, a failing `jq … | sort` pipeline inside `{ … } || true` aborts the compound command silently (no `append-execution-issue` path). **Scenario:** Manifest JSON readable by earlier `jq` calls but failing on this specific query edge case leaves contamination unwarned. **Fix:** Log a Warning when the OOS sub-block cannot run, or isolate `jq` with `|| true` and explicit empty handling.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## **Latent** (`correctness`) — [`agents/codex-implementer.md`](agents/codex-implementer.md) / [`agents/cursor-implementer.md`](agents/cursor-implementer.md) “Hard guards” preamble (diff: “Violating any of them **MUST** cause you to abort with `status=bailed`”) vs new NEVER **#8** scope rule (diff text only describes logging/review backstop, not an abort). **Concrete breakage:** readers can infer scope violations require a bail manifest even though the dispatcher is explicitly warn-and-continue. **Suggested fix:** qualify the preamble (“rules 1–7”) or move scope discipline out of the strict bail list.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 5. **Latent** (`correctness`) — [`agents/codex-implementer.md`](agents/codex-implementer.md) / [`agents/cursor-implementer.md`](agents/cursor-implementer.md) “Hard guards” preamble (diff: “Violating any of them **MUST** cause you to abort with `status=bailed`”) vs new NEVER **#8** scope rule (diff text only describes logging/review backstop, not an abort). **Concrete breakage:** readers can infer scope violations require a bail manifest even though the dispatcher is explicitly warn-and-continue. **Suggested fix:** qualify the preamble (“rules 1–7”) or move scope discipline out of the strict bail list.
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## **Latent** (`risk-integration`) [larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) (from diff / second commit) — New committed run metadata includes absolute `operator_cwd` / `operator_repo_root`. **Scenario:** If this tree is published or shared, paths leak workspace layout. **Fix:** Align with repo policy for `larch-logs` (redact fields, scrub before commit, or keep logs out of version control).

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 8. **Latent** (`risk-integration`) [larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) (from diff / second commit) — New committed run metadata includes absolute `operator_cwd` / `operator_repo_root`. **Scenario:** If this tree is published or shared, paths leak workspace layout. **Fix:** Align with repo policy for `larch-logs` (redact fields, scrub before commit, or keep logs out of version control).
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## **Latent** (`risk-integration`) — **implementation_plan** “Files to modify” (four paths) vs full branch diff. The branch also touches [`SECURITY.md`](SECURITY.md), [`skills/implement/scripts/step2-implement.md`](skills/implement/scripts/step2-implement.md), [`skills/implement/scripts/test-step2-dispatch.md`](skills/implement/scripts/test-step2-dispatch.md), [`agents/_implementer-base.md`](agents/_implementer-base.md), [`agents/gemini-implementer.md`](agents/gemini-implementer.md), and committed [`larch-logs/implement/...`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) artifacts. **Concrete impact:** larger review surface and run-log churn than the stated implementation file list (even if some updates are desirable). **Suggested fix:** split docs/log commits from the functional change or extend the written plan’s file list to match reality.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 4. **Latent** (`risk-integration`) — **implementation_plan** “Files to modify” (four paths) vs full branch diff. The branch also touches [`SECURITY.md`](SECURITY.md), [`skills/implement/scripts/step2-implement.md`](skills/implement/scripts/step2-implement.md), [`skills/implement/scripts/test-step2-dispatch.md`](skills/implement/scripts/test-step2-dispatch.md), [`agents/_implementer-base.md`](agents/_implementer-base.md), [`agents/gemini-implementer.md`](agents/gemini-implementer.md), and committed [`larch-logs/implement/...`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) artifacts. **Concrete impact:** larger review surface and run-log churn than the stated implementation file list (even if some updates are desirable). **Suggested fix:** split docs/log commits from the functional change or extend the written plan’s file list to match reality.
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## **Latent** (`risk-integration`) — [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) (and sibling new files under the same run id): The second commit flushes a run log containing machine-specific `operator_cwd` / `operator_repo_root`. **Scenario:** Noise in PR review, possible policy friction if run logs are not always meant to ship with every feature branch. **Fix:** Confirm run-log policy; omit or redact local paths if logs should not carry operator home paths.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 5. **Latent** (`risk-integration`) — [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) (and sibling new files under the same run id): The second commit flushes a run log containing machine-specific `operator_cwd` / `operator_repo_root`. **Scenario:** Noise in PR review, possible policy friction if run logs are not always meant to ship with every feature branch. **Fix:** Confirm run-log policy; omit or redact local paths if logs should not carry operator home paths.
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## **Latent** `correctness` (source: `plan`) — Same OOS block: any path in `git status --porcelain` that was **dirty before** the implementer ran (allowed by the prompts’ “do not discard deliberate dirt”) appears in `wt \setminus manifest` and triggers the Warning even when the implementer did not touch it this run. **Scenario**: Operator leaves unrelated edits in the tree; every complete dispatch logs a large OOS Warning though the implementer stayed in manifest-declared files. **Suggested fix**: Compare against a baseline path set captured before the launcher runs, or narrow the message to “may include pre-existing dirt” (as in some later workspace iterations) and/or diff against `BASELINE` state if available.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 5. **Latent** `correctness` (source: `plan`) — Same OOS block: any path in `git status --porcelain` that was **dirty before** the implementer ran (allowed by the prompts’ “do not discard deliberate dirt”) appears in `wt \setminus manifest` and triggers the Warning even when the implementer did not touch it this run. **Scenario**: Operator leaves unrelated edits in the tree; every complete dispatch logs a large OOS Warning though the implementer stayed in manifest-declared files. **Suggested fix**: Compare against a baseline path set captured before the launcher runs, or narrow the message to “may include pre-existing dirt” (as in some later workspace iterations) and/or diff against `BASELINE` state if available.
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## **Latent** `risk-integration` (source: `plan`) — [skills/implement/scripts/step2-implement.sh](skills/implement/scripts/step2-implement.sh) (diff line 447): `trap 'rm -f "$WT_PATHS_FILE" "$MANIFEST_PATHS_FILE" "$OOS_PATHS_FILE" "$LAUNCHER_TMP"' EXIT` **replaces** the script’s earlier `EXIT` trap that only removed `"$LAUNCHER_TMP"`. **Scenario**: In this diff the replacement still deletes `"$LAUNCHER_TMP"`, so behavior is OK today; if a future edit adds a separate `EXIT` hook without merging traps, the inner `trap` would clobber it. **Suggested fix**: Save/restore `trap -p EXIT` or append cleanup with a `trap` wrapper pattern.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 6. **Latent** `risk-integration` (source: `plan`) — [skills/implement/scripts/step2-implement.sh](skills/implement/scripts/step2-implement.sh) (diff line 447): `trap 'rm -f "$WT_PATHS_FILE" "$MANIFEST_PATHS_FILE" "$OOS_PATHS_FILE" "$LAUNCHER_TMP"' EXIT` **replaces** the script’s earlier `EXIT` trap that only removed `"$LAUNCHER_TMP"`. **Scenario**: In this diff the replacement still deletes `"$LAUNCHER_TMP"`, so behavior is OK today; if a future edit adds a separate `EXIT` hook without merging traps, the inner `trap` would clobber it. **Suggested fix**: Save/restore `trap -p EXIT` or append cleanup with a `trap` wrapper pattern.
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## **Latent**, **correctness**, [`skills/implement/scripts/step2-implement.sh:682-692`](skills/implement/scripts/step2-implement.sh): The branch `[[ -z "$jq_out" ]] && [[ -s "$WT_PATHS_FILE" ]]` treats **all** empty `jq` outputs the same (parse failure, empty arrays, or “no paths emitted”), logging “OOS check skipped.” **Scenario:** A malformed or edge-case manifest that still reached `status=complete` could suppress the intended OOS enumeration; distinguishing `jq` failure (non-zero exit) from a valid empty declaration would make behavior predictable.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **Latent**, **correctness**, [`skills/implement/scripts/step2-implement.sh:682-692`](skills/implement/scripts/step2-implement.sh): The branch `[[ -z "$jq_out" ]] && [[ -s "$WT_PATHS_FILE" ]]` treats **all** empty `jq` outputs the same (parse failure, empty arrays, or “no paths emitted”), logging “OOS check skipped.” **Scenario:** A malformed or edge-case manifest that still reached `status=complete` could suppress the intended OOS enumeration; distinguishing `jq` failure (non-zero exit) from a valid empty declaration would make behavior predictable.
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## **Latent**, **risk-integration**, [`agents/codex-implementer.md:119`](agents/codex-implementer.md) (and the same bullet in [`agents/_implementer-base.md:73`](agents/_implementer-base.md), [`agents/cursor-implementer.md:165`](agents/cursor-implementer.md), [`agents/gemini-implementer.md:211`](agents/gemini-implementer.md)): New NEVER #8 tells implementers to push out-of-plan issues into `oos_observations[]`, while [`SECURITY.md:18`](SECURITY.md) still states that security findings must not be folded into `oos_observations[]`. **Scenario:** A model routes a sensitive finding into OOS prose believing it complies with NEVER #8, reintroducing the exact boundary `SECURITY.md` warns about. **Fix:** Qualify NEVER #8 (“non-security observations only; never use `oos_observations[]` for security findings — private disclosure / SECURITY flow”) so it cannot be read as overriding the security policy.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Latent**, **risk-integration**, [`agents/codex-implementer.md:119`](agents/codex-implementer.md) (and the same bullet in [`agents/_implementer-base.md:73`](agents/_implementer-base.md), [`agents/cursor-implementer.md:165`](agents/cursor-implementer.md), [`agents/gemini-implementer.md:211`](agents/gemini-implementer.md)): New NEVER #8 tells implementers to push out-of-plan issues into `oos_observations[]`, while [`SECURITY.md:18`](SECURITY.md) still states that security findings must not be folded into `oos_observations[]`. **Scenario:** A model routes a sensitive finding into OOS prose believing it complies with NEVER #8, reintroducing the exact boundary `SECURITY.md` warns about. **Fix:** Qualify NEVER #8 (“non-security observations only; never use `oos_observations[]` for security findings — private disclosure / SECURITY flow”) so it cannot be read as overriding the security policy.
- **Suggested revision**: Address the concern above.

### FINDING_36: panel [code-review/accepted]

## **Nit** (`code-quality`) [skills/implement/scripts/test-step2-dispatch.sh:612-676](skills/implement/scripts/test-step2-dispatch.sh) — Test 18 proves the Warning exists alongside `STATUS=complete` but does not assert it was emitted **before** `git add -A && git commit` (the plan’s ordering claim). **Fix:** Compare mtimes of `execution-issues.md` vs `.git/objects` / new commit, or assert log ordering with a harness-visible sentinel.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 7. **Nit** (`code-quality`) [skills/implement/scripts/test-step2-dispatch.sh:612-676](skills/implement/scripts/test-step2-dispatch.sh) — Test 18 proves the Warning exists alongside `STATUS=complete` but does not assert it was emitted **before** `git add -A && git commit` (the plan’s ordering claim). **Fix:** Compare mtimes of `execution-issues.md` vs `.git/objects` / new commit, or assert log ordering with a harness-visible sentinel.
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## **Nit** (`code-quality`) — Beyond the plan’s file list, the diff also updates `agents/_implementer-base.md`, `agents/gemini-implementer.md`, `SECURITY.md`, `skills/implement/scripts/step2-implement.md`, and `skills/implement/scripts/test-step2-dispatch.md`. Mostly coherent parity/docs; slightly wider change surface for reviewers.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 9. **Nit** (`code-quality`) — Beyond the plan’s file list, the diff also updates `agents/_implementer-base.md`, `agents/gemini-implementer.md`, `SECURITY.md`, `skills/implement/scripts/step2-implement.md`, and `skills/implement/scripts/test-step2-dispatch.md`. Mostly coherent parity/docs; slightly wider change surface for reviewers.
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## **Nit** (`code-quality`, `plan`) [agents/cursor-implementer.md:156-165](agents/cursor-implementer.md) — Plan asked for a new **“NEVER #7”** for Cursor parity; the diff adds an eighth **numbered** hard guard without renumbering the list. **Fix:** Renumber so the visible “NEVER” index matches the plan, or adjust the plan text.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 6. **Nit** (`code-quality`, `plan`) [agents/cursor-implementer.md:156-165](agents/cursor-implementer.md) — Plan asked for a new **“NEVER #7”** for Cursor parity; the diff adds an eighth **numbered** hard guard without renumbering the list. **Fix:** Renumber so the visible “NEVER” index matches the plan, or adjust the plan text.
- **Suggested revision**: Address the concern above.

### FINDING_39: panel [code-review/accepted]

## **Nit** (`code-quality`, `plan`) — [`agents/cursor-implementer.md`](agents/cursor-implementer.md) hard-guard list: The implementation plan called the new rule “NEVER #7”; the file adds an eighth numbered hard guard (same as Codex/Gemini). **Fix:** Renumber or align docs with the plan if numbering matters for cross-references.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 4. **Nit** (`code-quality`, `plan`) — [`agents/cursor-implementer.md`](agents/cursor-implementer.md) hard-guard list: The implementation plan called the new rule “NEVER #7”; the file adds an eighth numbered hard guard (same as Codex/Gemini). **Fix:** Renumber or align docs with the plan if numbering matters for cross-references.
- **Suggested revision**: Address the concern above.

### FINDING_40: panel [code-review/accepted]

## **Nit** (`correctness`) — **implementation_plan** Step 3 template vs [`agents/codex-implementer.md`](agents/codex-implementer.md) (diff ~119). NEVER **#8** adds “**especially its ‘Files to modify’ section**” beyond the plan’s quoted sentence. Low risk but not verbatim plan fidelity. **Suggested fix:** match the plan quote or update the plan document.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 6. **Nit** (`correctness`) — **implementation_plan** Step 3 template vs [`agents/codex-implementer.md`](agents/codex-implementer.md) (diff ~119). NEVER **#8** adds “**especially its ‘Files to modify’ section**” beyond the plan’s quoted sentence. Low risk but not verbatim plan fidelity. **Suggested fix:** match the plan quote or update the plan document.
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## **Nit** (`risk-integration`, `plan`) — [`skills/implement/scripts/test-step2-dispatch.sh`](skills/implement/scripts/test-step2-dispatch.sh) ~612–676: Test 18 only covers “declared README + undeclared `undeclared.txt`”. It does not cover plan cross-scope, the jq-empty / skip branch, or paths with spaces (the `-z` porcelain path). **Fix:** Add focused cases once plan-scope and empty-manifest semantics are fixed.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Nit** (`risk-integration`, `plan`) — [`skills/implement/scripts/test-step2-dispatch.sh`](skills/implement/scripts/test-step2-dispatch.sh) ~612–676: Test 18 only covers “declared README + undeclared `undeclared.txt`”. It does not cover plan cross-scope, the jq-empty / skip branch, or paths with spaces (the `-z` porcelain path). **Fix:** Add focused cases once plan-scope and empty-manifest semantics are fixed.
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## **Nit** `completeness w.r.t. plan` (source: `plan`) — [agents/cursor-implementer.md](agents/cursor-implementer.md): The implementation plan called the new Cursor rule “NEVER #7”, but the shared template already uses **7** for the control-artifact rule; adding scope as **8** matches the file’s numbering and is consistent with Codex. **Suggested fix**: Update the written plan / issue text to say “NEVER #8” for Cursor parity, or renumber the control-artifact bullet.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 7. **Nit** `completeness w.r.t. plan` (source: `plan`) — [agents/cursor-implementer.md](agents/cursor-implementer.md): The implementation plan called the new Cursor rule “NEVER #7”, but the shared template already uses **7** for the control-artifact rule; adding scope as **8** matches the file’s numbering and is consistent with Codex. **Suggested fix**: Update the written plan / issue text to say “NEVER #8” for Cursor parity, or renumber the control-artifact bullet.
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## **Nit** `completeness w.r.t. plan` (source: `plan`) — [agents/gemini-implementer.md](agents/gemini-implementer.md) and [agents/_implementer-base.md](agents/_implementer-base.md) are updated even though the plan’s file list named only Codex and Cursor; this is reasonable because Codex/Cursor are AUTO-GENERATED from the base. **Suggested fix**: None if generators are re-run in CI; otherwise ensure `bash scripts/generate-*-implementer.sh` outputs match hand edits.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 8. **Nit** `completeness w.r.t. plan` (source: `plan`) — [agents/gemini-implementer.md](agents/gemini-implementer.md) and [agents/_implementer-base.md](agents/_implementer-base.md) are updated even though the plan’s file list named only Codex and Cursor; this is reasonable because Codex/Cursor are AUTO-GENERATED from the base. **Suggested fix**: None if generators are re-run in CI; otherwise ensure `bash scripts/generate-*-implementer.sh` outputs match hand edits.
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## **Nit**, **architecture**, [`agents/cursor-implementer.md:165`](agents/cursor-implementer.md): The feature text asked for Cursor **NEVER #7** parity after #6; the branch adds the same rule as **#8**, matching Codex/base numbering instead of the requested Cursor-local numbering. **Fix:** Renumber only in `cursor-implementer.md` if strict parity with the written spec matters.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 6. **Nit**, **architecture**, [`agents/cursor-implementer.md:165`](agents/cursor-implementer.md): The feature text asked for Cursor **NEVER #7** parity after #6; the branch adds the same rule as **#8**, matching Codex/base numbering instead of the requested Cursor-local numbering. **Fix:** Renumber only in `cursor-implementer.md` if strict parity with the written spec matters.
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## **Note:** Your checked-out [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) already differs from the **truncated diff hunk** (e.g. `-z` porcelain, jq-empty guard, comments). If the PR tip matches the workspace file rather than the older diff snippet, finding **3** may already be partially addressed—re-validate against the final commit tip before voting.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_46: panel [code-review/accepted]

## **Plan items verified present in the diff (no gap vs implementation_plan):** Step 7a→7b placement after `paths_invalid` bail; `append-execution-issue.sh` with `--category Warnings`; guards `[[ -x "$APPEND_TOOL" && -d "$TMPDIR_ARG" ]]`; outer `|| true`; manifest jq pipeline; Test 18 + doc updates in `test-step2-dispatch.*`; Codex NEVER **#8** added after old **#7** as specified.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_47: panel [code-review/accepted]

## **Read-only constraint:** I did not write a `.tsv` file to disk. Below is the TSV payload you can save as the sidecar (e.g. next to your review artifact) if your pipeline expects it.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## **Structured TSV** (could not be written to disk under read-only review; paste into sidecar if needed):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_49: panel [code-review/accepted]

## ---

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_50: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	architecture	skills/implement/scripts/step2-implement.sh:656-658	No mechanical comparison against plan Files to modify section	Edits outside plan scope still pass if manifest lists touched paths	Implement plan path cross check or align documentation prompts with actual behavior
- **Suggested revision**: Address the concern above.

### FINDING_51: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	code-quality	agents/_implementer-base.md:64-73 agents/codex-implementer.md:110-119 agents/cursor-implementer.md:156-165 agents/gemini-implementer.md:202-211	Hard guards say MUST bail on any violation; new scope rule expects non-bail completion with oos_observations	Contradictory model instructions	Reword preamble or move scope rule out of unconditional bail set
- **Suggested revision**: Address the concern above.

### FINDING_52: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	code-quality	skills/implement/scripts/step2-implement.sh:653-691	OOS check omits plan Files to modify cross-reference per feature/plan	Plan-scope drift where manifest and tree agree but plan does not list touched files is never flagged	Parse plan section from --plan-file into allowlist or document scope reduction
- **Suggested revision**: Address the concern above.

### FINDING_53: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	agents/_implementer-base.md:62-73 (diff.txt hunk)	Hard guards say every violation MUST status=bailed; new NEVER #8 is enforced as a dispatcher Warning not a bail.	Model may bail incorrectly or treat other NEVER rules as soft; inconsistent operator guidance.	Qualify preamble carve-out item 8 or move scope rule out of Hard guards.
- **Suggested revision**: Address the concern above.

### FINDING_54: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	agents/codex-implementer.md agents/cursor-implementer.md agents/gemini-implementer.md: parallel NEVER block (diff.txt)	Same Hard-guards vs NEVER #8 contradiction propagated to all external implementer prompts.	Same ambiguous bail semantics for Codex/Cursor/Gemini.	Fix _implementer-base then regenerate implementer prompts.
- **Suggested revision**: Address the concern above.

### FINDING_55: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	feature_description vs skills/implement/scripts/step2-implement.sh (diff ~438-466)	No cross-check against plan Files to modify section only manifest vs porcelain	Plan-scope drift where manifest lists touched files but plan forbids them is invisible to Step 7a.1	Parse plan file and intersect or extend warnings per feature_description
- **Suggested revision**: Address the concern above.

### FINDING_56: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:438-466 (diff.txt hunk)	OOS check compares only git status paths to manifest paths; plan Files to modify not consulted.	Implementer changes a plan-listed file but omits it from files_touched; no Warning even though work is out of sync with declared manifest and plan scope.	Parse plan Files to modify and union with manifest-declared paths (or drop that requirement from the feature spec).
- **Suggested revision**: Address the concern above.

### FINDING_57: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:449-451 (diff.txt hunk)	awk print $NF mis-parses porcelain paths with spaces or unusual quoting.	Untracked file foo bar.txt yields wrong token bar.txt; OOS list wrong or empty for that path.	Use porcelain -z NUL parsing or quoted-path aware extraction.
- **Suggested revision**: Address the concern above.

### FINDING_58: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:669-671	Awk last-field parsing of default porcelain mishandles spaced paths / some statuses	OOS list wrong or incomplete; warning misses real OOS paths	Use porcelain -z NUL parsing
- **Suggested revision**: Address the concern above.

### FINDING_59: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:673-677	Porcelain path extraction uses last whitespace token not full path field	Misclassified OOS warnings or missed detections when paths contain spaces quotes or unusual porcelain tokens	Parse XY path per git porcelain rules or use git diff name list instead of manual tokenization
- **Suggested revision**: Address the concern above.

### FINDING_60: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-710	OOS warning compares only git porcelain to manifest paths; plan Files to modify is not parsed despite feature request.	Edits allowed by plan but omitted from manifest (or manifest-only scope) never surface as plan-relative OOS; false confidence for operators.	Parse PLAN_FILE for Files to modify and implement the planned three-way check.
- **Suggested revision**: Address the concern above.

### FINDING_61: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:674-681	Warning blames external implementer for all undeclared porcelain paths	Operator pre-existing dirty files produce misleading implementer warnings	Qualify message or diff against pre-implementer baseline
- **Suggested revision**: Address the concern above.

### FINDING_62: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:680-691	Empty jq path output with dirty tree logs skip warning instead of treating all WT paths as OOS per plan.	Empty files_touched/tests with real edits yields vague skip message not enumerated OOS.	Split jq failure from empty declaration; on empty declaration use full comm OOS list.
- **Suggested revision**: Address the concern above.

### FINDING_63: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	security	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json:242-243	Tracked run log embeds operator absolute cwd paths	Repository clone leaks local filesystem layout to readers	Stop committing such logs or redact path fields to placeholders
- **Suggested revision**: Address the concern above.

### FINDING_64: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:438-466 (diff.txt hunk)	OOS set includes any pre-existing dirty paths not in manifest.	Large spurious Warning on every complete run in a dirty worktree even if implementer only touched declared files.	Baseline-subtract before compare or clarify warning text and operator workflow.
- **Suggested revision**: Address the concern above.

### FINDING_65: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:673-676	Jq pipeline failure inside pipefail group is swallowed by || true with no skip notice	OOS diagnostic silently omitted on jq edge failure	Append explicit Warning when OOS block cannot complete
- **Suggested revision**: Address the concern above.

### FINDING_66: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:682-692	Empty jq output branch conflates failures with empty declarations	OOS diagnostic may be skipped on jq error or odd manifest	Branch on jq exit status separately from empty path sets
- **Suggested revision**: Address the concern above.

### FINDING_67: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	agents/codex-implementer.md:119	NEVER 8 routes out of plan issues to oos_observations without excluding security	Models may stash security content in OOS contrary to SECURITY.md	Qualify rule as non security only and point to private disclosure flow
- **Suggested revision**: Address the concern above.

### FINDING_68: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json	Committed run manifest embeds absolute operator paths	Workspace path leakage in shared repo	Redact or exclude per policy
- **Suggested revision**: Address the concern above.

### FINDING_69: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json:1-20	Committed run log includes absolute operator paths.	PR noise or policy mismatch for committed logs.	Confirm larch-logs commit policy redact paths or drop from PR.
- **Suggested revision**: Address the concern above.

### FINDING_70: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	skills/implement/scripts/step2-implement.sh:447 (diff.txt hunk)	trap EXIT inside block replaces prior EXIT trap.	Future second EXIT hook could be clobbered by this pattern.	Save/restore trap or merge cleanup actions explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_71: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	architecture	agents/cursor-implementer.md:165	Cursor hard guard numbered 8 not 7 as requested in feature text	Spec readers expect NEVER 7 on cursor only	Renumber in cursor prompt if spec alignment matters
- **Suggested revision**: Address the concern above.

### FINDING_72: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	agents/cursor-implementer.md:154-165	NEVER numbering differs from plan (called #7 implemented as #8).	Cross-doc references to NEVER numbers may drift.	Align numbering with plan or codex parity docs.
- **Suggested revision**: Address the concern above.

### FINDING_73: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	agents/cursor-implementer.md:156-165	Plan asked NEVER #7; list adds eighth guard without renumbering	Doc/plan vocabulary mismatch	Renumber or update plan wording
- **Suggested revision**: Address the concern above.

### FINDING_74: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	multiple files listed in finding 9	Wider-than-plan doc/agent parity edits	Slightly larger review surface	Accept or split PR
- **Suggested revision**: Address the concern above.

### FINDING_75: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	skills/implement/scripts/test-step2-dispatch.sh:612-676	Test does not pin Warning before commit ordering	Regression could pass if Warning moves after commit	Add ordering assertion
- **Suggested revision**: Address the concern above.

### FINDING_76: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	agents/cursor-implementer.md (diff.txt)	Plan text said NEVER #7; file uses #8 after control-artifact #7.	Documentation mismatch only.	Update plan wording to NEVER #8 for Cursor.
- **Suggested revision**: Address the concern above.

### FINDING_77: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	agents/gemini-implementer.md agents/_implementer-base.md (diff.txt)	Plan listed only codex/cursor; gemini/base also edited.	Slightly broader diff than plan file list (likely intentional for generation).	Document generator workflow or restrict diff to listed files if policy requires.
- **Suggested revision**: Address the concern above.

### FINDING_78: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	skills/implement/scripts/test-step2-dispatch.sh:612-676	Test 18 does not cover plan scope jq-empty skip or spaced paths.	Untested branches regress without CI signal.	Add tests for those semantics once implemented.
- **Suggested revision**: Address the concern above.

### FINDING_79: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	architecture	skills/implement/scripts/step2-implement.sh (pre-existing trust model)	Manifest remains advisory vs working tree for commits	unchanged baseline behavior	N/A
- **Suggested revision**: Address the concern above.

### FINDING_80: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	code-quality	SECURITY.md:26-27 (diff.txt)	Long single-line paragraph edit.	Readability only.	Wrap paragraph when touching SECURITY.md next time.
- **Suggested revision**: Address the concern above.

### FINDING_81: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/ (diff.txt)	Committed implement run log tree plus chore commit.	PR noise unrelated to OOS logic verification.	Omit larch-logs from feature PR or follow repo logging policy.
- **Suggested revision**: Address the concern above.

### FINDING_82: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk-integration	skills/implement/scripts/step2-implement.md:407-408	Harness scope prose partially updated.	Low impact doc drift.	Tidy when editing that file.
- **Suggested revision**: Address the concern above.

### FINDING_83: panel [code-review/accepted]

## 2

- **Reviewer**: in_scope
- **Concern**: important	correctness	implementation_plan Step 4 vs agents/cursor-implementer.md (diff ~163-165)	Cursor scope rule numbered 8 after control artifacts instead of inserted as 7 after 6	References to NEVER #7 for Cursor mis-target the control-artifacts rule	Renumber insert scope as 7 and control artifacts as 8
- **Suggested revision**: Address the concern above.

### FINDING_84: panel [code-review/accepted]

## 3

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh (diff ~449-451)	Awk last-field porcelain parsing breaks on paths with spaces	OOS list wrong or incomplete noisy warnings	Use porcelain -z or robust path extraction
- **Suggested revision**: Address the concern above.

### FINDING_85: panel [code-review/accepted]

## 4

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	implementation_plan Files to modify vs branch diff	Extra files SECURITY.md step2-implement.md test-step2-dispatch.md agents/_implementer-base.md agents/gemini-implementer.md larch-logs	PR scope exceeds stated four-file plan	Split commits or expand plan file list
- **Suggested revision**: Address the concern above.

### FINDING_86: panel [code-review/accepted]

## 5

- **Reviewer**: in_scope
- **Concern**: latent	correctness	agents/codex-implementer.md agents/cursor-implementer.md Hard guards preamble vs new NEVER 8	Hard guards say any violation must bail scope rule describes warn path	Readers expect bail on OOS edits	Qualify preamble or relocate scope rule
- **Suggested revision**: Address the concern above.

### FINDING_87: panel [code-review/accepted]

## 6

- **Reviewer**: in_scope
- **Concern**: nit	correctness	implementation_plan Step 3 vs agents/codex-implementer.md (diff ~119)	Extra wording beyond plan quote	Minor plan text drift	Align text to plan
- **Suggested revision**: Address the concern above.

### FINDING_88: panel [code-review/accepted]

## Checking EXIT trap usage and `LAUNCHER_TMP` in the dispatcher, and reading the Test 18 hunk.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_89: panel [code-review/accepted]

## Checking EXIT trap usage in `step2-implement.sh` — the new block adds `trap ... EXIT`, which may overwrite the script's global EXIT handler.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_90: panel [code-review/accepted]

## Checking EXIT-trap usage in `step2-implement.sh` and reading `_implementer-base.md` / `gemini-implementer.md` diffs for parity.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_91: panel [code-review/accepted]

## Checking `step2-implement.sh` for EXIT traps and `LAUNCHER_TMP`, and reading the rest of Test 18 plus `append-execution-issue.sh`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_92: panel [code-review/accepted]

## Checking existing `trap` usage in `step2-implement.sh` and reading the remainder of Test 18.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_93: panel [code-review/accepted]

## Checking surrounding `trap` usage and `LAUNCHER_TMP` in `step2-implement.sh` to validate the EXIT-trap concern.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_94: panel [code-review/accepted]

## Checking whether the cached diff matches the workspace for the OOS block and scanning `append-execution-issue.sh` for injection risks:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_95: panel [code-review/accepted]

## Commits on branch vs `main`: `68099ed Warn on undeclared implementer files`, `59c4f13 chore(larch-logs): flush implement run …`. Review targets the precomputed diff (matches `HEAD` for the OOS block); your working tree’s `step2-implement.sh` has extra uncommitted edits beyond `HEAD` (for example `-z` parsing and jq fallback), which are **not** part of this branch-vs-main review unless committed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_96: panel [code-review/accepted]

## Commits on this branch since merge-base with `main` (read-only):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_97: panel [code-review/accepted]

## Hard constraint: **no file writes** — the TSV “sidecar” cannot be written to disk here; it is included as a fenced block you can save manually if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_98: panel [code-review/accepted]

## Note: the precomputed file under `~/.cache/larch/.../diff.txt` is **stale** for `step2-implement.sh` (it still showed the earlier `awk`/non-`-z` version). The authoritative branch diff vs `main` matches the working tree: NUL-terminated porcelain plus the `jq_out` guard. The review below follows **`git diff main`** (current branch).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_99: panel [code-review/accepted]

## Noting the cached `diff.txt` OOS block uses `awk 'NF {print $NF}'` on plain porcelain, while the workspace copy uses `git status --porcelain=v1 -z` and a jq-empty guard—likely post-diff edits on the working tree. Reviewing both: citing the diff where it diverges and using workspace line numbers for items present in the repo.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_100: panel [code-review/accepted]

## Read-only constraint: no sidecar file was written. TSV records appear in a code block at the end (tabs as literal `\t` in the explanation — I'll use real tab characters in the code block).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_101: panel [code-review/accepted]

## Review is based on the precomputed diff at `.../round-3/diff.txt`, commit list `59c4f13`, `68099ed`, and a spot-check of current workspace line anchors where the diff was truncated or superseded. Per your read-only constraint, no sidecar file was written; TSV lines are included in a code block for you to save manually if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_102: panel [code-review/accepted]

## Reviewed the precomputed diff at `<TMPDIR>/round-3/diff.txt` (including the `step2-implement.sh`, harness, agent, `SECURITY.md`, and `larch-logs` hunks) and commit list from `git log $(git merge-base HEAD main)..HEAD --oneline`. The on-disk workspace under `larch5` may have diverged slightly from that cached diff (for example `step2-implement.sh` in the repo shows a `-z` / `read -d ''` path list and extra comments); findings below are tied to **what the cached diff actually changes**, with line references taken from the diff hunks you were given.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_103: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: Gathering the pre-computed diff and commit list for a read-only correctness review.
- **Suggested revision**: Address the concern above.

### FINDING_104: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only review (no file writes). Reading the precomputed diff and running a non-mutating `git log`.
- **Suggested revision**: Address the concern above.

### FINDING_105: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Gathering the branch diff and commit list for a plan-fidelity review (read-only).
- **Suggested revision**: Address the concern above.

### FINDING_106: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: Gathering the diff and commit history (read-only). We won't write the TSV sidecar file due to your no-file-mutation constraint; we'll include TSV records in the response.
- **Suggested revision**: Address the concern above.

### FINDING_107: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Gathering the pre-computed diff and commit history for a read-only review. We won't write the TSV sidecar (read-only constraint); we'll include TSV rows in the response.
- **Suggested revision**: Address the concern above.

### FINDING_108: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: Gathering the branch diff and commit history for a read-only review focused on tests, CI, and regression risk.
- **Suggested revision**: Address the concern above.

### FINDING_109: panel [code-review/accepted]

## Reviewing the cached diff: the OOS block used `trap` including `LAUNCHER_TMP` (launcher temp cleanup preserved). The working tree now uses `git status --porcelain=v1 -z` and a jq-empty guard—the cache diff you were given is slightly behind the on-disk `step2-implement.sh`; findings below reflect the branch as it exists in the workspace (superset of the cache).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_110: panel [code-review/accepted]

## Searching the diff for plan-relevant files and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_111: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_112: panel [code-review/accepted]

## Searching the diff for relevant hunks; the full diff exceeds read limits.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_113: panel [code-review/accepted]

## Searching the precomputed diff for relevant files and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_114: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`architecture`) — Pre-existing trust model still treats `manifest.files_touched` as advisory vs the working tree; this change adds a warning layer but does not change the commit/staging model. Not introduced by the branch; listed only as context.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Nit** (`architecture`) — Pre-existing trust model still treats `manifest.files_touched` as advisory vs the working tree; this change adds a warning layer but does not change the commit/staging model. Not introduced by the branch; listed only as context.
- **Suggested revision**: Address the concern above.

### FINDING_115: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`architecture`) — [`SECURITY.md`](SECURITY.md) trust-model paragraph (diff ~26) documents the new warning; helpful for operators but outside the implementation_plan’s enumerated “Files to modify.” Treat as policy-driven doc sync unless you want the plan to formally own it.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Nit** (`architecture`) — [`SECURITY.md`](SECURITY.md) trust-model paragraph (diff ~26) documents the new warning; helpful for operators but outside the implementation_plan’s enumerated “Files to modify.” Treat as policy-driven doc sync unless you want the plan to formally own it.
- **Suggested revision**: Address the concern above.

### FINDING_116: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`risk-integration`) — [`skills/implement/scripts/step2-implement.md`](skills/implement/scripts/step2-implement.md) still describes the harness as not covering dispatcher-side commit in depth; wording was partially updated. Pre-existing broad “out of scope” language; only worth tidying if you touch that file again.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Nit** (`risk-integration`) — [`skills/implement/scripts/step2-implement.md`](skills/implement/scripts/step2-implement.md) still describes the harness as not covering dispatcher-side commit in depth; wording was partially updated. Pre-existing broad “out of scope” language; only worth tidying if you touch that file again.
- **Suggested revision**: Address the concern above.

### FINDING_117: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** `code-quality` (out of scope: pre-existing doc convention) — [SECURITY.md](SECURITY.md) (diff lines 26–27): The “External tool delegation” paragraph is a very long single line; the diff only inserts a sentence about the new Warning. Not introduced for readability here.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Nit** `code-quality` (out of scope: pre-existing doc convention) — [SECURITY.md](SECURITY.md) (diff lines 26–27): The “External tool delegation” paragraph is a very long single line; the diff only inserts a sentence about the new Warning. Not introduced for readability here.
- **Suggested revision**: Address the concern above.

### FINDING_118: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** `risk-integration` (out of scope: log hygiene, not logic of OOS detection) — [larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) and the `chore(larch-logs): flush implement run …` commit in the branch: committing per-run `larch-logs` trees is often noisy for reviewers unless the repo’s policy requires it for this change set.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Nit** `risk-integration` (out of scope: log hygiene, not logic of OOS detection) — [larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) and the `chore(larch-logs): flush implement run …` commit in the branch: committing per-run `larch-logs` trees is often noisy for reviewers unless the repo’s policy requires it for this change set.
- **Suggested revision**: Address the concern above.

### FINDING_119: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: codex-generalist-output.txt
- **Concern**: No out-of-scope observations.
- **Suggested revision**: Address the concern above.

### FINDING_120: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: None worth filing from this pass (remaining trust-model text in `SECURITY.md` is largely pre-existing, with a small additive sentence tied to the new warning).
- **Suggested revision**: Address the concern above.

### FINDING_121: panel [code-review/accepted]

## `59c4f13` — chore(larch-logs): flush implement run `2B036492-1DB7-464A-B254-4E6BB9D63853`

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `59c4f13` — chore(larch-logs): flush implement run `2B036492-1DB7-464A-B254-4E6BB9D63853`
- **Suggested revision**: Address the concern above.

### FINDING_122: panel [code-review/accepted]

## `68099ed` — Warn on undeclared implementer files  

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `68099ed` — Warn on undeclared implementer files
- **Suggested revision**: Address the concern above.

### FINDING_123: panel [code-review/accepted]

## ```

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_124: panel [code-review/accepted]

## ```text

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_125: panel [code-review/accepted]

## ```tsv

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_126: panel [code-review/accepted]

## schema_version

- **Reviewer**: scope
- **Concern**: severity	focus_area	location	what	scenario_or_breakage	suggested_fix
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## ### Structured TSV (not written to disk; read-only review)

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** (`architecture`) — [`skills/implement/scripts/step2-implement.sh:656-657`](skills/implement/scripts/step2-implement.sh) — The product/feature text asks to cross-reference the plan’s **“Files to modify”** section against the working tree; the implementation explicitly does **not** do that (`not implemented` comment). An implementer can list every touched path in `files_touched` (silencing the new Warning) while still editing files outside the plan’s declared scope, so the stated “OOS-bundled / scope” goal is only partially met. **Suggested fix:** Parse the plan file (`--plan-file` already exists in the dispatcher) for the `Files to modify` bullet list, normalize paths, and union that set into the “declared” side of the comparison (or emit a second Warning category when WT paths fall outside the plan set even if they appear in the manifest).

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** (`architecture`) — [`skills/implement/scripts/step2-implement.sh:656-657`](skills/implement/scripts/step2-implement.sh) — The product/feature text asks to cross-reference the plan’s **“Files to modify”** section against the working tree; the implementation explicitly does **not** do that (`not implemented` comment). An implementer can list every touched path in `files_touched` (silencing the new Warning) while still editing files outside the plan’s declared scope, so the stated “OOS-bundled / scope” goal is only partially met. **Suggested fix:** Parse the plan file (`--plan-file` already exists in the dispatcher) for the `Files to modify` bullet list, normalize paths, and union that set into the “declared” side of the comparison (or emit a second Warning category when WT paths fall outside the plan set even if they appear in the manifest).
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** (`code-quality`) — [`agents/codex-implementer.md`](agents/codex-implementer.md) (e.g. “How to declare completion” still says the dispatcher does not cross-check the manifest against the diff; manifest checklist ~line 131 still says there is no diff cross-check). New NEVER #8 claims the dispatcher “detects undeclared working-tree changes.” **Scenario:** implementers get contradictory instructions (advisory-only manifest vs mechanical warning). **Fix:** tighten wording to “best-effort list cross-check (not a full diff)” and align the declare-completion bullet with Step 7a.1.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 4. **Important** (`code-quality`) — [`agents/codex-implementer.md`](agents/codex-implementer.md) (e.g. “How to declare completion” still says the dispatcher does not cross-check the manifest against the diff; manifest checklist ~line 131 still says there is no diff cross-check). New NEVER #8 claims the dispatcher “detects undeclared working-tree changes.” **Scenario:** implementers get contradictory instructions (advisory-only manifest vs mechanical warning). **Fix:** tighten wording to “best-effort list cross-check (not a full diff)” and align the declare-completion bullet with Step 7a.1.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** (`code-quality`, `plan` / `requirements`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) (new Step 7a.1 block in diff around the insert after path validation, ~`step2-implement.sh:633-467` in the diff hunk). The feature text and implementation plan require cross-referencing the working tree (and manifest) against the plan’s **“Files to modify”** section; the shipped logic only compares `git status --porcelain` paths to `files_touched` / `tests_added_or_modified`. **Scenario:** implementer edits a path listed in the plan but omits it from the manifest while declaring only in-plan files — no warning even though the plan’s file list is violated. **Fix:** parse the plan file (or the artifact the orchestrator already materializes) for that section and include those paths in the allowed set (or emit a separate warning for plan-vs-tree drift).

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** (`code-quality`, `plan` / `requirements`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) (new Step 7a.1 block in diff around the insert after path validation, ~`step2-implement.sh:633-467` in the diff hunk). The feature text and implementation plan require cross-referencing the working tree (and manifest) against the plan’s **“Files to modify”** section; the shipped logic only compares `git status --porcelain` paths to `files_touched` / `tests_added_or_modified`. **Scenario:** implementer edits a path listed in the plan but omits it from the manifest while declaring only in-plan files — no warning even though the plan’s file list is violated. **Fix:** parse the plan file (or the artifact the orchestrator already materializes) for that section and include those paths in the allowed set (or emit a separate warning for plan-vs-tree drift).
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Important** (`code-quality`, `plan`) — [`agents/codex-implementer.md`](agents/codex-implementer.md), [`agents/cursor-implementer.md`](agents/cursor-implementer.md) (Hard guards: new bullet is numbered `8.` in both). The plan asked for Codex **NEVER #8** and Cursor **NEVER #7** (parity by ordinal). **Impact:** operators/docs that refer to “NEVER #7” on Cursor now point at the wrong rule. **Fix:** renumber Cursor’s list so the new scope rule is #7 and following bullets shift, or explicitly document shared numbering with `_implementer-base.md`.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Important** (`code-quality`, `plan`) — [`agents/codex-implementer.md`](agents/codex-implementer.md), [`agents/cursor-implementer.md`](agents/cursor-implementer.md) (Hard guards: new bullet is numbered `8.` in both). The plan asked for Codex **NEVER #8** and Cursor **NEVER #7** (parity by ordinal). **Impact:** operators/docs that refer to “NEVER #7” on Cursor now point at the wrong rule. **Fix:** renumber Cursor’s list so the new scope rule is #7 and following bullets shift, or explicitly document shared numbering with `_implementer-base.md`.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Important** (`risk-integration` / `correctness`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~669–672 (`HEAD`): OOS enumeration uses `git status --porcelain` piped to `awk 'NF {print $NF}'`. For paths with spaces (or other tokenization edge cases), `$NF` is not the full path, so paths can be truncated, merged, or omitted from `comm`, producing **false negatives** (missed OOS) or nonsense entries. Suggested fix: use NUL-delimited `git status --porcelain=v1 -z` and parse the path field per Git’s v1 z-format (or another space-safe extraction).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Important** (`risk-integration` / `correctness`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~669–672 (`HEAD`): OOS enumeration uses `git status --porcelain` piped to `awk 'NF {print $NF}'`. For paths with spaces (or other tokenization edge cases), `$NF` is not the full path, so paths can be truncated, merged, or omitted from `comm`, producing **false negatives** (missed OOS) or nonsense entries. Suggested fix: use NUL-delimited `git status --porcelain=v1 -z` and parse the path field per Git’s v1 z-format (or another space-safe extraction).
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Important** (`risk-integration`) — [`agents/codex-implementer.md:62`](agents/codex-implementer.md), [`agents/cursor-implementer.md:68`](agents/cursor-implementer.md), [`agents/gemini-implementer.md:68`](agents/gemini-implementer.md) — “How to declare completion” still says the dispatcher **does NOT cross-check** `files_touched` against the working tree / diff, which is now false given Step 7a.1 (and [`SECURITY.md`](SECURITY.md) already describes the new Warning). **Concrete scenario:** an external implementer follows the stale bullet, under-declares `files_touched`, and assumes there is no mechanical comparison—operators rely on the new Warning, but the prompt trains the wrong invariant. **Suggested fix:** Rewrite bullet 3 to describe Step 7a.1’s porcelain-vs-manifest Warning (non-blocking), keep the “no unified diff / subject cross-check” nuance, and align wording with `step2-implement.md` / `SECURITY.md`.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Important** (`risk-integration`) — [`agents/codex-implementer.md:62`](agents/codex-implementer.md), [`agents/cursor-implementer.md:68`](agents/cursor-implementer.md), [`agents/gemini-implementer.md:68`](agents/gemini-implementer.md) — “How to declare completion” still says the dispatcher **does NOT cross-check** `files_touched` against the working tree / diff, which is now false given Step 7a.1 (and [`SECURITY.md`](SECURITY.md) already describes the new Warning). **Concrete scenario:** an external implementer follows the stale bullet, under-declares `files_touched`, and assumes there is no mechanical comparison—operators rely on the new Warning, but the prompt trains the wrong invariant. **Suggested fix:** Rewrite bullet 3 to describe Step 7a.1’s porcelain-vs-manifest Warning (non-blocking), keep the “no unified diff / subject cross-check” nuance, and align wording with `step2-implement.md` / `SECURITY.md`.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Important** (`risk-integration`, `requirements` + `plan` scope from `<feature_description>`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~653–686 (Step 7a.1 at `HEAD`): the warning only subtracts manifest-declared paths (`files_touched` / `tests_added_or_modified`) from `git status` paths; it does **not** cross-check the plan artifact’s “Files to modify” list. Concrete scenario: an implementer touches an out-of-plan file but **lists it** in `files_touched` to satisfy the manifest; the tree matches the manifest, so **no Warning**, yet plan scope is still violated. Suggested fix: parse declared paths from `--plan-file` (or the exported plan slice) and emit a second warning for plan∖manifest or tree∖plan, or narrow the shipped contract/docs so “OOS” means “undeclared vs manifest” only.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`, `requirements` + `plan` scope from `<feature_description>`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~653–686 (Step 7a.1 at `HEAD`): the warning only subtracts manifest-declared paths (`files_touched` / `tests_added_or_modified`) from `git status` paths; it does **not** cross-check the plan artifact’s “Files to modify” list. Concrete scenario: an implementer touches an out-of-plan file but **lists it** in `files_touched` to satisfy the manifest; the tree matches the manifest, so **no Warning**, yet plan scope is still violated. Suggested fix: parse declared paths from `--plan-file` (or the exported plan slice) and emit a second warning for plan∖manifest or tree∖plan, or narrow the shipped contract/docs so “OOS” means “undeclared vs manifest” only.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Important** `correctness` `skills/implement/scripts/step2-implement.sh:664-666` — `git status --porcelain | awk 'NF {print $NF}'` corrupts paths containing spaces, so the diagnostic can compare and report the wrong file. Concrete scenario: an implementer edits `docs/scope note.md`; porcelain emits `?? docs/scope note.md`, `awk` records only `note.md`, and the Warning either names an unusable path or falsely warns even when the manifest correctly declares `docs/scope note.md`. Fix by using NUL-delimited porcelain, for example `git status --porcelain=v1 -z`, and parse full path records before sorting/comparing.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` `skills/implement/scripts/step2-implement.sh:664-666` — `git status --porcelain | awk 'NF {print $NF}'` corrupts paths containing spaces, so the diagnostic can compare and report the wrong file. Concrete scenario: an implementer edits `docs/scope note.md`; porcelain emits `?? docs/scope note.md`, `awk` records only `note.md`, and the Warning either names an unusable path or falsely warns even when the manifest correctly declares `docs/scope note.md`. Fix by using NUL-delimited porcelain, for example `git status --porcelain=v1 -z`, and parse full path records before sorting/comparing.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## **Important** `correctness` `skills/implement/scripts/step2-implement.sh:667` — The new OOS check only compares working-tree paths against manifest-declared paths, so it misses the requested plan-scope check. Concrete scenario: if the plan’s “Files to modify” allows only `README.md`, but the implementer edits `SECURITY.md` and includes `SECURITY.md` in `manifest.files_touched`, `comm -23` sees no undeclared path and no Warning is logged before `git add -A` commits the out-of-plan edit. Fix by parsing the plan’s “Files to modify” allowlist and warning when either actual working-tree paths or manifest-declared paths fall outside it; add a regression beside `skills/implement/scripts/test-step2-dispatch.sh:918-982` where the extra file is declared in the manifest but absent from the plan.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/implement/scripts/step2-implement.sh:667` — The new OOS check only compares working-tree paths against manifest-declared paths, so it misses the requested plan-scope check. Concrete scenario: if the plan’s “Files to modify” allows only `README.md`, but the implementer edits `SECURITY.md` and includes `SECURITY.md` in `manifest.files_touched`, `comm -23` sees no undeclared path and no Warning is logged before `git add -A` commits the out-of-plan edit. Fix by parsing the plan’s “Files to modify” allowlist and warning when either actual working-tree paths or manifest-declared paths fall outside it; add a regression beside `skills/implement/scripts/test-step2-dispatch.sh:918-982` where the extra file is declared in the manifest but absent from the plan.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## **Important**, **correctness**, [`skills/implement/scripts/step2-implement.sh:670-677`](skills/implement/scripts/step2-implement.sh): The NUL-delimited `git status --porcelain=v1 -z` loop treats every NUL-terminated slice as `XY␠<path>` and prints `${record:3}`. For renames Git emits **two** slices: `R  <newpath>\0<oldpath>\0` (verified: `b'R  f2\x00f1\x00'` after `git mv f1 f2`). The second slice is **bare** `<oldpath>` with no two-letter status prefix, so `${record:3}` yields an **empty** line (or garbage for shorter strings), polluting `$WT_PATHS_FILE`. That corrupts `sort`/`comm` against the manifest and can produce bogus OOS warnings or mask real ones. The adjacent comment claims the “last NUL-terminated field (destination path)” is used, but the code does not implement that. **Fix:** Only strip three characters when `record` matches `^[A-Z?][A-Z?] `; otherwise treat the slice as a raw path (rename second field), or use a single-shot parser aligned with Git’s documented `-z` record shapes.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Important**, **correctness**, [`skills/implement/scripts/step2-implement.sh:670-677`](skills/implement/scripts/step2-implement.sh): The NUL-delimited `git status --porcelain=v1 -z` loop treats every NUL-terminated slice as `XY␠<path>` and prints `${record:3}`. For renames Git emits **two** slices: `R  <newpath>\0<oldpath>\0` (verified: `b'R  f2\x00f1\x00'` after `git mv f1 f2`). The second slice is **bare** `<oldpath>` with no two-letter status prefix, so `${record:3}` yields an **empty** line (or garbage for shorter strings), polluting `$WT_PATHS_FILE`. That corrupts `sort`/`comm` against the manifest and can produce bogus OOS warnings or mask real ones. The adjacent comment claims the “last NUL-terminated field (destination path)” is used, but the code does not implement that. **Fix:** Only strip three characters when `record` matches `^[A-Z?][A-Z?] `; otherwise treat the slice as a raw path (rename second field), or use a single-shot parser aligned with Git’s documented `-z` record shapes.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## **Latent** (`correctness`) — [`skills/implement/scripts/step2-implement.sh:670-677`](skills/implement/scripts/step2-implement.sh) — NUL-delimited porcelain is parsed by stripping a fixed **3-character** `XY ` prefix from **every** NUL-terminated record. For Git rename/copy entries, `git status --porcelain=v1 -z` can emit **multiple** path segments per logical change; continuation segments often **lack** the `XY ` prefix, so `${record:3}` mangles the path or drops the canonical destination name from the working-tree set. **Concrete scenario:** a rename-heavy implementer run produces an incorrect `WT_PATHS_FILE`, so `comm` misses a truly undeclared path (false negative) or injects garbage lines into the Warning. **Suggested fix:** Use a parser that follows Git’s documented `-z` record shape (or `git diff --name-only` against `HEAD` for the same tree snapshot), and add a harness case with a synthetic rename if feasible.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **Latent** (`correctness`) — [`skills/implement/scripts/step2-implement.sh:670-677`](skills/implement/scripts/step2-implement.sh) — NUL-delimited porcelain is parsed by stripping a fixed **3-character** `XY ` prefix from **every** NUL-terminated record. For Git rename/copy entries, `git status --porcelain=v1 -z` can emit **multiple** path segments per logical change; continuation segments often **lack** the `XY ` prefix, so `${record:3}` mangles the path or drops the canonical destination name from the working-tree set. **Concrete scenario:** a rename-heavy implementer run produces an incorrect `WT_PATHS_FILE`, so `comm` misses a truly undeclared path (false negative) or injects garbage lines into the Warning. **Suggested fix:** Use a parser that follows Git’s documented `-z` record shape (or `git diff --name-only` against `HEAD` for the same tree snapshot), and add a harness case with a synthetic rename if feasible.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## **Latent** (`correctness`) — [`skills/implement/scripts/step2-implement.sh:686-687`](skills/implement/scripts/step2-implement.sh) — `comm` compares **literal** strings from `jq` manifest paths vs porcelain paths with no canonicalization (e.g. `./src/foo` vs `src/foo`). **Concrete scenario:** implementer lists `./pkg/bar` in `files_touched` while Git reports `pkg/bar`, producing a noisy Warning listing `pkg/bar` as “undeclared” despite honest declaration. **Suggested fix:** Normalize both sides (strip leading `./`, collapse redundant slashes where safe) before `sort -u` / `comm`.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 5. **Latent** (`correctness`) — [`skills/implement/scripts/step2-implement.sh:686-687`](skills/implement/scripts/step2-implement.sh) — `comm` compares **literal** strings from `jq` manifest paths vs porcelain paths with no canonicalization (e.g. `./src/foo` vs `src/foo`). **Concrete scenario:** implementer lists `./pkg/bar` in `files_touched` while Git reports `pkg/bar`, producing a noisy Warning listing `pkg/bar` as “undeclared” despite honest declaration. **Suggested fix:** Normalize both sides (strip leading `./`, collapse redundant slashes where safe) before `sort -u` / `comm`.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## **Latent** (`correctness`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) (same 7a.1 block in the **precomputed diff**). Porcelain paths are collected with `awk 'NF {print $NF}'`. **Scenario:** status lines with spaces in paths, copy/rename lines with multiple fields, or other non-single-token tail fields can yield wrong or truncated paths, so `comm` may miss real OOS files or false-positive. **Fix:** use NUL-terminated porcelain (`git status --porcelain=v1 -z`) and split records the same way as other tooling in this repo.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Latent** (`correctness`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) (same 7a.1 block in the **precomputed diff**). Porcelain paths are collected with `awk 'NF {print $NF}'`. **Scenario:** status lines with spaces in paths, copy/rename lines with multiple fields, or other non-single-token tail fields can yield wrong or truncated paths, so `comm` may miss real OOS files or false-positive. **Fix:** use NUL-terminated porcelain (`git status --porcelain=v1 -z`) and split records the same way as other tooling in this repo.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## **Latent** (`risk-integration`) — [`skills/implement/scripts/step2-implement.sh:665-668`](skills/implement/scripts/step2-implement.sh) — The EXIT trap is captured with `trap -p EXIT | sed …` and concatenated into a new trap string. If the pre-existing EXIT handler contains quotes/newlines/subshells typical of defensive traps, the `sed` peel can truncate or corrupt the prior handler. **Concrete scenario:** a future EXIT trap change causes the merged trap to fail to parse at `trap` install time (shell-dependent) or drops the previous cleanup, leaking `$TMPDIR_ARG/oos-*.XXXXXX` files across dispatcher runs. **Suggested fix:** Avoid string-splicing `trap -p`; use a dedicated cleanup function registered once that tracks temp paths in an array, or scope temp cleanup to a subshell where acceptable.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Latent** (`risk-integration`) — [`skills/implement/scripts/step2-implement.sh:665-668`](skills/implement/scripts/step2-implement.sh) — The EXIT trap is captured with `trap -p EXIT | sed …` and concatenated into a new trap string. If the pre-existing EXIT handler contains quotes/newlines/subshells typical of defensive traps, the `sed` peel can truncate or corrupt the prior handler. **Concrete scenario:** a future EXIT trap change causes the merged trap to fail to parse at `trap` install time (shell-dependent) or drops the previous cleanup, leaking `$TMPDIR_ARG/oos-*.XXXXXX` files across dispatcher runs. **Suggested fix:** Avoid string-splicing `trap -p`; use a dedicated cleanup function registered once that tracks temp paths in an array, or scope temp cleanup to a subshell where acceptable.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## **Latent** (`risk-integration`) — same block ~665–667 (`HEAD`): the OOS helper sets a fresh `trap ... EXIT` inside the compound command. Today line ~405’s EXIT trap is only `rm -f "$LAUNCHER_TMP"`, and the new trap still removes `"$LAUNCHER_TMP"`, so behavior is likely equivalent for the current script. If a future edit extends the global EXIT trap with additional cleanup, this block would **silently replace** it and drop obligations. Suggested fix: compose with the previous `trap -p EXIT` body (chained trap) instead of replacing.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Latent** (`risk-integration`) — same block ~665–667 (`HEAD`): the OOS helper sets a fresh `trap ... EXIT` inside the compound command. Today line ~405’s EXIT trap is only `rm -f "$LAUNCHER_TMP"`, and the new trap still removes `"$LAUNCHER_TMP"`, so behavior is likely equivalent for the current script. If a future edit extends the global EXIT trap with additional cleanup, this block would **silently replace** it and drop obligations. Suggested fix: compose with the previous `trap -p EXIT` body (chained trap) instead of replacing.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## **Latent**, **architecture**, [`skills/implement/scripts/step2-implement.sh:656-657`](skills/implement/scripts/step2-implement.sh) vs feature text: The product/feature description asked to cross-reference the plan’s **“Files to modify”** section; the dispatcher explicitly documents that this is **not implemented** and only compares the working tree to manifest paths. **Impact:** Operators may assume plan-scope drift is detected when only manifest drift is. **Fix:** Either implement plan cross-check (parse plan section) or tighten external-facing docs (SECURITY/step2-implement.md) so they never imply plan parity.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Latent**, **architecture**, [`skills/implement/scripts/step2-implement.sh:656-657`](skills/implement/scripts/step2-implement.sh) vs feature text: The product/feature description asked to cross-reference the plan’s **“Files to modify”** section; the dispatcher explicitly documents that this is **not implemented** and only compares the working tree to manifest paths. **Impact:** Operators may assume plan-scope drift is detected when only manifest drift is. **Fix:** Either implement plan cross-check (parse plan section) or tighten external-facing docs (SECURITY/step2-implement.md) so they never imply plan parity.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## **Latent**, **risk-integration**, [`agents/_implementer-base.md:64-73`](agents/_implementer-base.md) (and the same NEVER bullet mirrored in [`agents/codex-implementer.md`](agents/codex-implementer.md), [`agents/cursor-implementer.md`](agents/cursor-implementer.md), [`agents/gemini-implementer.md`](agents/gemini-implementer.md)): NEVER #8 steers implementers to record out-of-plan issues in `oos_observations[]`, while [`SECURITY.md`](SECURITY.md) (unchanged in intent) still stresses that **security** findings must not be routed through public OOS artifacts. **Scenario:** An implementer misreads #8 as permission to park a security issue in `oos_observations[]`, reintroducing disclosure risk at the manifest boundary. **Fix:** Qualify NEVER #8 as **non-security** observations only, pointing security to the private disclosure flow.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Latent**, **risk-integration**, [`agents/_implementer-base.md:64-73`](agents/_implementer-base.md) (and the same NEVER bullet mirrored in [`agents/codex-implementer.md`](agents/codex-implementer.md), [`agents/cursor-implementer.md`](agents/cursor-implementer.md), [`agents/gemini-implementer.md`](agents/gemini-implementer.md)): NEVER #8 steers implementers to record out-of-plan issues in `oos_observations[]`, while [`SECURITY.md`](SECURITY.md) (unchanged in intent) still stresses that **security** findings must not be routed through public OOS artifacts. **Scenario:** An implementer misreads #8 as permission to park a security issue in `oos_observations[]`, reintroducing disclosure risk at the manifest boundary. **Fix:** Qualify NEVER #8 as **non-security** observations only, pointing security to the private disclosure flow.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## **Nit** (`code-quality`) — [`skills/implement/scripts/test-step2-dispatch.sh`](skills/implement/scripts/test-step2-dispatch.sh) (Test 18 in diff). The stub touches `README.md` and `undeclared.txt` while the manifest only lists `README.md`; the assertion does not prove ordering relative to `git add`/`commit`, only that `execution-issues.md` contains the warning and `STATUS=complete`. Acceptable for a diagnostic pin, but the test name/comments slightly over-claim “before commit.” **Fix:** optionally assert file mtimes or grep dispatcher sidecar for ordering if you need that guarantee.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 5. **Nit** (`code-quality`) — [`skills/implement/scripts/test-step2-dispatch.sh`](skills/implement/scripts/test-step2-dispatch.sh) (Test 18 in diff). The stub touches `README.md` and `undeclared.txt` while the manifest only lists `README.md`; the assertion does not prove ordering relative to `git add`/`commit`, only that `execution-issues.md` contains the warning and `STATUS=complete`. Acceptable for a diagnostic pin, but the test name/comments slightly over-claim “before commit.” **Fix:** optionally assert file mtimes or grep dispatcher sidecar for ordering if you need that guarantee.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## **Nit** (`risk-integration`) — Branch includes a separate chore commit flushing [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) plus the functional commit; increases review surface and couples run metadata to the feature PR.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 6. **Nit** (`risk-integration`) — Branch includes a separate chore commit flushing [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) plus the functional commit; increases review surface and couples run metadata to the feature PR.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## **Nit** (`risk-integration`) — [`skills/implement/scripts/test-step2-dispatch.sh:918-982`](skills/implement/scripts/test-step2-dispatch.sh) — Test 18 asserts the positive path (undeclared file triggers substring match) but does not assert that declared edits (e.g. `README.md`) are **absent** from the OOS list or that the stub still returns `STATUS=complete` without collateral failures. **Suggested fix:** Tighten assertions (e.g. `grep -Fvq` for `README.md` in the Warning block or snapshot the `execution-issues.md` section) so regressions in `comm` logic fail loudly.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 6. **Nit** (`risk-integration`) — [`skills/implement/scripts/test-step2-dispatch.sh:918-982`](skills/implement/scripts/test-step2-dispatch.sh) — Test 18 asserts the positive path (undeclared file triggers substring match) but does not assert that declared edits (e.g. `README.md`) are **absent** from the OOS list or that the stub still returns `STATUS=complete` without collateral failures. **Suggested fix:** Tighten assertions (e.g. `grep -Fvq` for `README.md` in the Warning block or snapshot the `execution-issues.md` section) so regressions in `comm` logic fail loudly.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## **Nit** (`risk-integration`) — [`skills/implement/scripts/test-step2-dispatch.sh`](skills/implement/scripts/test-step2-dispatch.sh) ~969–981: Test 18 asserts post-run contents of `execution-issues.md` and `STATUS=complete` but does not pin ordering relative to `git commit` (e.g., a deliberate commit failure hook could not prove “before commit”). Suggested fix: only if you need a hard ordering pin—e.g., temporary `GIT_COMMIT` stub or assert intermediate artifact timestamps—not usually worth the complexity.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 5. **Nit** (`risk-integration`) — [`skills/implement/scripts/test-step2-dispatch.sh`](skills/implement/scripts/test-step2-dispatch.sh) ~969–981: Test 18 asserts post-run contents of `execution-issues.md` and `STATUS=complete` but does not pin ordering relative to `git commit` (e.g., a deliberate commit failure hook could not prove “before commit”). Suggested fix: only if you need a hard ordering pin—e.g., temporary `GIT_COMMIT` stub or assert intermediate artifact timestamps—not usually worth the complexity.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## **Nit** (`risk-integration`, `plan`) — [`docs/linting.md`](docs/linting.md) ~211: the `make test-step2-dispatch` row still describes harness coverage without mentioning the new undeclared-path / `execution-issues.md` Warning behavior (Test 18). Suggested fix: extend that row (and any assertion-count prose elsewhere) when the harness contract grows.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 4. **Nit** (`risk-integration`, `plan`) — [`docs/linting.md`](docs/linting.md) ~211: the `make test-step2-dispatch` row still describes harness coverage without mentioning the new undeclared-path / `execution-issues.md` Warning behavior (Test 18). Suggested fix: extend that row (and any assertion-count prose elsewhere) when the harness contract grows.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## **Nit**, **correctness** (precomputed **round-4 diff only** for [`step2-implement.sh`](skills/implement/scripts/step2-implement.sh)): The cached hunk used `awk 'NF {print $NF}'` on non-`-z` porcelain, which mishandles quoted paths and some multi-field lines. **If** that version were what shipped, path enumeration would be unreliable. Current tree uses `-z` (with the rename parsing bug above). **Fix:** Ensure no release branch still carries the awk-only hunk.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 6. **Nit**, **correctness** (precomputed **round-4 diff only** for [`step2-implement.sh`](skills/implement/scripts/step2-implement.sh)): The cached hunk used `awk 'NF {print $NF}'` on non-`-z` porcelain, which mishandles quoted paths and some multi-field lines. **If** that version were what shipped, path enumeration would be unreliable. Current tree uses `-z` (with the rename parsing bug above). **Fix:** Ensure no release branch still carries the awk-only hunk.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## **Nit**, **correctness**, [`agents/_implementer-base.md:62-73`](agents/_implementer-base.md): The heading says any hard-guard violation **MUST** cause `status=bailed`, but NEVER #8 is phrased as scope discipline (“do not modify… record in `oos_observations[]`”) without an explicit bail rule if the model already edited out of scope. **Fix:** Clarify whether scope violations are retrospective guidance only or require bail after the fact.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Nit**, **correctness**, [`agents/_implementer-base.md:62-73`](agents/_implementer-base.md): The heading says any hard-guard violation **MUST** cause `status=bailed`, but NEVER #8 is phrased as scope discipline (“do not modify… record in `oos_observations[]`”) without an explicit bail rule if the model already edited out of scope. **Fix:** Clarify whether scope violations are retrospective guidance only or require bail after the fact.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## **Nit**, **risk-integration**, [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) (per diff): New committed run metadata includes absolute `operator_cwd` / `operator_repo_root` under a user home path. **Impact:** Low security, but persistent PII/path leakage in a shared repo if logs are published. Prefer redaction or repo-relative fields if policy requires it.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **Nit**, **risk-integration**, [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) (per diff): New committed run metadata includes absolute `operator_cwd` / `operator_repo_root` under a user home path. **Impact:** Low security, but persistent PII/path leakage in a shared repo if logs are published. Prefer redaction or repo-relative fields if policy requires it.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## **Note:** The checked-out workspace copy of [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) already differs from the **precomputed diff** (e.g. NUL-terminated `git status`, EXIT-trap chaining, and an explicit comment that plan cross-reference is not implemented). If that is uncommitted work, merge review should re-run against the final tree; the findings above still apply to what the cached diff shows unless those follow-ups land.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## **Note:** Your local `step2-implement.sh` (uncommitted) already shows a chained EXIT trap and NUL-delimited status parsing—those edits address findings 2–3 for the working tree but are **not** on `HEAD` yet; merge risk remains until committed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## **Read-only constraint:** No `.tsv` sidecar was written to disk. TSV records appear in a fenced block at the end for the orchestrator to capture.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## **Read-only notice:** Per HARD CONSTRAINTS, no sidecar file was written. Structured TSV lines below are for manual capture if your pipeline expects a `.tsv` file.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## **TSV (read-only: not written to `*.tsv`; paste/save if your pipeline needs it)**

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## ---

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	architecture	skills/implement/scripts/step2-implement.sh:656-657	Plan Files to modify cross-check explicitly not implemented; only manifest paths used.	Implementer can over-declare files_touched to silence warnings while still editing out-of-plan files the feature text called out.	Parse --plan-file Files to modify and include in declared set or emit separate plan-scope Warning.
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	code-quality	agents/codex-implementer.md:79-82 and ~121-131	Declare-completion / checklist still says no dispatcher cross-check; conflicts with new NEVER #8.	Implementer may ignore list hygiene thinking manifest is purely advisory for mechanics.	Align copy: advisory manifest plus best-effort undeclared-path warning (not full diff).
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	code-quality	agents/cursor-implementer.md:154-165; agents/codex-implementer.md:108-119	New scope rule numbered 8 in both; plan asked Cursor NEVER #7.	Docs and humans reference wrong NEVER index on Cursor.	Renumber Cursor bullets or document shared base numbering.
- **Suggested revision**: Address the concern above.

### FINDING_36: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	code-quality	skills/implement/scripts/step2-implement.sh:633-700 (Step 7a.1)	Plan-required cross-check against plan Files to modify is missing; only manifest vs porcelain.	Edits match plan file list but are omitted from manifest → no OOS warning despite plan scope violation.	Parse plan Files to modify (or equivalent artifact) and union with manifest-declared paths before comm -23.
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:670-677	NUL porcelain loop applies ${record:3} to every NUL slice; rename emits bare second path without XY prefix	Rename after external implementer yields extra empty or wrong path rows in WT_PATHS_FILE corrupting comm vs manifest and OOS warnings	Detect XY-prefixed lines vs raw path slices per git status -z rename contract or use a path enumerator that returns final paths only
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	agents/codex-implementer.md:62 agents/cursor-implementer.md:68 agents/gemini-implementer.md:68	Stale prompt bullet claims dispatcher does not cross-check files_touched vs working tree.	Implementer trained on false invariant under-declares manifest paths despite new Step 7a.1 Warning.	Update bullet 3 to describe Step 7a.1 porcelain-vs-manifest Warning and align with SECURITY/step2-implement.md.
- **Suggested revision**: Address the concern above.

### FINDING_39: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-686	Step 7a.1 only compares working tree to manifest paths; no plan Files-to-modify cross-check per feature_description.	Implementer can edit out-of-plan files yet list them in files_touched; no Warning fires while plan scope is violated.	Parse plan-declared paths from --plan-file and warn on plan vs manifest / tree mismatches, or align requirements to manifest-only OOS.
- **Suggested revision**: Address the concern above.

### FINDING_40: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:669-672	Porcelain paths parsed with awk last-field.	Paths containing spaces split across awk fields; OOS set wrong → missed warnings or garbage paths.	Use git status --porcelain=v1 -z and NUL-safe path extraction.
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	architecture	skills/implement/scripts/step2-implement.sh:656-657	Explicit comment: plan Files to modify cross-check not implemented	Feature description promised plan cross-reference; warning does not detect edits outside plan but inside manifest	Implement plan section parse or narrow public claims to manifest-only comparison
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:633-700 (diff version awk tail)	Awk last-field porcelain parsing mishandles paths with spaces / multi-field rename lines.	OOS set wrong → silent miss or bogus warnings.	Use git status -z and robust field split (as in improved tree) or path0 helpers.
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:670-677	Porcelain v1 -z parsed with fixed 3-char strip on every NUL record.	Rename/copy z-records may include unprefixed continuation paths; WT_PATHS_FILE wrong -> false negatives or garbage Warning lines.	Parse per Git -z record rules or use diff-name list; add rename harness case.
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:686-687	comm compares raw manifest strings vs git paths without normalization.	Equivalent paths ./foo vs foo cause spurious undeclared warnings.	Normalize both path sets before sort/comm.
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	agents/_implementer-base.md:64-73 plus codex/cursor/gemini parity bullets	NEVER #8 routes out-of-plan issues to oos_observations without excluding security class	Security finding could be mis-filed in oos_observations contrary to SECURITY.md public-boundary rules	Prefix NEVER #8 with non-security only and cite SECURITY disclosure path for security issues
- **Suggested revision**: Address the concern above.

### FINDING_46: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	skills/implement/scripts/step2-implement.sh:665-667	OOS block sets EXIT trap without chaining prior trap body.	Future global EXIT cleanup beyond rm LAUNCHER_TMP could be dropped if this block runs.	Chain trap -p EXIT into the new EXIT handler.
- **Suggested revision**: Address the concern above.

### FINDING_47: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	skills/implement/scripts/step2-implement.sh:665-668	EXIT trap merged via trap -p piped through sed.	Complex prior EXIT trap may break parsing or drop cleanup; oos tempfiles leak.	Use function-based cleanup or array-tracked temps instead of sed-splicing trap -p output.
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	skills/implement/scripts/test-step2-dispatch.sh:612-676	Test asserts warning present + STATUS=complete but not strict ordering before git commit.	Comment over-claims ordering invariant.	Tighten comment or add ordering assertion if required.
- **Suggested revision**: Address the concern above.

### FINDING_49: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	agents/_implementer-base.md:62-73	Hard guards preamble requires bail on any violation while NEVER #8 omits explicit bail for scope edits	Implementers may disagree on required status when scope was violated	Clarify bail vs retrospective guidance for scope violations
- **Suggested revision**: Address the concern above.

### FINDING_50: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	correctness	skills/implement/scripts/step2-implement.sh (round-4 diff hunk only)	Awk last-field extraction from non -z porcelain	Quoted or unusual status lines mis-enumerate paths if that hunk ships	Use NUL-delimited parsing with correct rename handling
- **Suggested revision**: Address the concern above.

### FINDING_51: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	docs/linting.md:211	make test-step2-dispatch doc row omits new OOS warning / Test 18 coverage.	Operators skim linting table and miss the new diagnostic contract.	Extend the row to mention undeclared-path warnings and Test 18.
- **Suggested revision**: Address the concern above.

### FINDING_52: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/*	Chore log flush commit bundled with functional change.	Extra unrelated files in PR diff.	Split or omit run-log flush from feature PR per repo convention.
- **Suggested revision**: Address the concern above.

### FINDING_53: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json (new)	Committed manifest embeds absolute operator cwd/repo root	Username/host path leakage in shared git history if logs are distributed	Redact or relativize paths in committed run logs if policy requires
- **Suggested revision**: Address the concern above.

### FINDING_54: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	skills/implement/scripts/test-step2-dispatch.sh:918-982	Test 18 only checks positive grep fragments.	Regression in comm logic could still pass if output format shifts slightly or false positives include declared paths.	Add negative assertions on declared paths / snapshot section.
- **Suggested revision**: Address the concern above.

### FINDING_55: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	skills/implement/scripts/test-step2-dispatch.sh:969-981	Test 18 does not strictly order-pin warning before git commit.	Reorder regression could slip if someone moves Step 7a.1 after commit without test update.	Add ordering assertion only if project requires hard pin.
- **Suggested revision**: Address the concern above.

### FINDING_56: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	code-quality	SECURITY.md:26-27	Trust paragraph already maximal-density before this edit.	Pre-existing readability.	None for this PR; optional future wrap only.
- **Suggested revision**: Address the concern above.

### FINDING_57: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	code-quality	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/ plus commit 59c4f13	Run-log flush churn in same branch as functional change.	PR harder to review; no runtime effect on OOS detection.	Policy choice; split log commits from code if undesired.
- **Suggested revision**: Address the concern above.

### FINDING_58: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/	Committed implement run logs bundled with feature commit.	PR diff noise; not introduced functional test gap.	Keep run logs out of feature PRs or separate commit.
- **Suggested revision**: Address the concern above.

### FINDING_59: panel [code-review/accepted]

## Checking EXIT trap handling in `step2-implement.sh` — the new block sets `trap ... EXIT`, which may override the script's global EXIT handler.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_60: panel [code-review/accepted]

## Checking EXIT-trap usage in `step2-implement.sh` and reading the remainder of Test 18.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_61: panel [code-review/accepted]

## Checking `LAUNCHER_TMP`, trap handling, and `append-execution-issue.sh` for injection or trap-override issues.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_62: panel [code-review/accepted]

## Checking manifest schema for `tests_added_or_modified`, doc consistency, and trap/append-execution-issue edge cases.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_63: panel [code-review/accepted]

## Checking porcelain `-z` parsing for edge cases and the hard-guards intro in the agent files.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_64: panel [code-review/accepted]

## Checking the `trap` interaction and whether plan-file cross-checking exists; reading surrounding `step2-implement.sh` and the cursor/gemini agent diffs.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_65: panel [code-review/accepted]

## Checking whether the rename NUL-splitting issue exists in the branch (workspace) and preparing the review. Skipping CreatePlan — the task is a deliverable review, not an implementation plan to confirm.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_66: panel [code-review/accepted]

## Commits on branch since merge-base with `main` (from read-only `git log`):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_67: panel [code-review/accepted]

## Commits since merge-base with `main` (from your command):  

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_68: panel [code-review/accepted]

## Commits vs `main` (read-only): `68099ed Warn on undeclared implementer files`, `59c4f13 chore(larch-logs): flush implement ...`. Merge-base: `b47793ced4cb7985926b8ebf05c9a4f8cd9993fb`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_69: panel [code-review/accepted]

## Confirming `PLAN_FILE` is validated but unused by the new OOS check. Creating the review plan document.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_70: panel [code-review/accepted]

## Confirming the branch diff (not the stale `round-4/diff.txt`) includes NUL porcelain parsing and the merged EXIT trap. Verifying rename `-z` record structure against Git's documented format:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_71: panel [code-review/accepted]

## Read-only constraint: no file writes, so the TSV sidecar is included as a fenced block you can save manually; it was not written to disk.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_72: panel [code-review/accepted]

## Reading diff hunks for `step2-implement.sh`, `test-step2-dispatch.sh`, and agent files to verify plan fidelity (including cross-check vs plan "Files to modify").

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_73: panel [code-review/accepted]

## Reading the implemented OOS-detection logic, Test 18, and agent prompt changes in the workspace for accurate line numbers and edge-case analysis.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_74: panel [code-review/accepted]

## Review is based on the precomputed diff at `.../round-4/diff.txt` plus spot reads of the current tree where the diff was ambiguous. Your hard constraint forbids writing a `.tsv` file; TSV records appear in a fenced block at the end for copy/paste.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_75: panel [code-review/accepted]

## Review used the precomputed diff plus `git log $(git merge-base HEAD main)..HEAD --oneline` (commits: `68099ed Warn on undeclared implementer files`, `59c4f13 chore(larch-logs): flush implement run …`). For `step2-implement.sh`, `git show HEAD:…` matches the diff hunks (the working copy on disk can differ from `HEAD`; this review treats **committed** branch content as what merges).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_76: panel [code-review/accepted]

## Reviewed the precomputed diff at `.../round-4/diff.txt` (capped hunks) and cross-checked the live dispatcher block in [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) because the tree has evolved past the cached hunk (trap merge, `-z` parsing, jq fallback, explicit “plan Files to modify not implemented” comment).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_77: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: Gathering the pre-computed diff and commit list for a read-only correctness review.
- **Suggested revision**: Address the concern above.

### FINDING_78: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Gathering the branch diff, commit list, and full-file context for an edge-case-focused read-only review. Running read-only git commands and reading the precomputed diff plus key files.
- **Suggested revision**: Address the concern above.

### FINDING_79: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Gathering the branch diff and commit list for a Plan Fidelity review (read-only: no file writes).
- **Suggested revision**: Address the concern above.

### FINDING_80: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only security-focused review. Reading the precomputed diff and running read-only git commands (`git log`, `git merge-base`).
- **Suggested revision**: Address the concern above.

### FINDING_81: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only review (no file writes; we'll include TSV records in the response because writing the sidecar would violate your hard constraint).
- **Suggested revision**: Address the concern above.

### FINDING_82: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: Gathering the pre-computed diff and commit history (read-only) for a tests/CI/regression review.
- **Suggested revision**: Address the concern above.

### FINDING_83: panel [code-review/accepted]

## Reviewing `git diff main` (authoritative); `round-4/diff.txt` is stale (older `awk`/`trap` version). Creating the review plan.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_84: panel [code-review/accepted]

## Reviewing the supplied diff and workspace for discrepancies. Findings: the feature requires cross-referencing the plan's "Files to modify" section — the workspace explicitly documents that as not implemented. Stale implementer copy still claims no mechanical cross-check. Checking whether `step2-implement.sh` receives `--plan-file` for a possible plan-based check:

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_85: panel [code-review/accepted]

## Searching the diff for plan-relevant files and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_86: panel [code-review/accepted]

## Searching the diff for relevant files and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_87: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading key sections of the source files for line-accurate review.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_88: panel [code-review/accepted]

## Searching the diff for relevant hunks; the full diff exceeds the read limit.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_89: panel [code-review/accepted]

## TSV (could not write sidecar file per read-only constraint; paste to `review.tsv` if needed):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_90: panel [code-review/accepted]

## Verifying `git status --porcelain=v1 -z` record shape for renames (correctness).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_91: panel [code-review/accepted]

## Verifying branch content: the cached diff may not match the working tree. Fetching the authoritative `git diff` for the critical file.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_92: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`code-quality`) — [`SECURITY.md`](SECURITY.md): the trust-model paragraph was already an extremely long single block before this edit; the branch only adjusts one sentence about the new warning. Out of scope as a structural problem not introduced by this branch’s intent.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Nit** (`code-quality`) — [`SECURITY.md`](SECURITY.md): the trust-model paragraph was already an extremely long single block before this edit; the branch only adjusts one sentence about the new warning. Out of scope as a structural problem not introduced by this branch’s intent.
- **Suggested revision**: Address the concern above.

### FINDING_93: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`code-quality`) — [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) and related plan artifacts plus commit `59c4f13` — These look like flushed run-log / session artifacts bundled with the feature commit series; they add review noise and are unrelated to the dispatcher logic itself. **Why out of scope:** not part of the OOS-detection behavior under review unless the team policy requires log commits in the same PR.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Nit** (`code-quality`) — [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) and related plan artifacts plus commit `59c4f13` — These look like flushed run-log / session artifacts bundled with the feature commit series; they add review noise and are unrelated to the dispatcher logic itself. **Why out of scope:** not part of the OOS-detection behavior under review unless the team policy requires log commits in the same PR.
- **Suggested revision**: Address the concern above.

### FINDING_94: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit**, **architecture**, [`skills/implement/scripts/step2-implement.md`](skills/implement/scripts/step2-implement.md) / [`SECURITY.md`](SECURITY.md): Long trust-model paragraphs now mention the new warning; any internal inconsistency with older “advisory only” language is editorial pre-existing style, not a new trust boundary.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Nit**, **architecture**, [`skills/implement/scripts/step2-implement.md`](skills/implement/scripts/step2-implement.md) / [`SECURITY.md`](SECURITY.md): Long trust-model paragraphs now mention the new warning; any internal inconsistency with older “advisory only” language is editorial pre-existing style, not a new trust boundary.
- **Suggested revision**: Address the concern above.

### FINDING_95: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Out-of-scope** (`risk-integration`, noise) — [`larch-logs/implement/2B036492-…/*`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) (commit `59c4f13`): large run-log / plan artifact churn rides along the functional commit; it does not exercise CI logic directly but increases review noise and merge-conflict surface unrelated to the dispatcher behavior.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Out-of-scope** (`risk-integration`, noise) — [`larch-logs/implement/2B036492-…/*`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) (commit `59c4f13`): large run-log / plan artifact churn rides along the functional commit; it does not exercise CI logic directly but increases review noise and merge-conflict surface unrelated to the dispatcher behavior.
- **Suggested revision**: Address the concern above.

### FINDING_96: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: codex-generalist-output.txt
- **Concern**: No out-of-scope observations.
- **Suggested revision**: Address the concern above.

### FINDING_97: panel [code-review/accepted]

## `59c4f13 chore(larch-logs): flush implement run 2B036492-1DB7-464A-B254-4E6BB9D63853`  

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_98: panel [code-review/accepted]

## `59c4f13` — chore(larch-logs): flush implement run 2B036492-…  

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `59c4f13` — chore(larch-logs): flush implement run 2B036492-…  
- **Suggested revision**: Address the concern above.

### FINDING_99: panel [code-review/accepted]

## `68099ed Warn on undeclared implementer files`

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_100: panel [code-review/accepted]

## `68099ed` — Warn on undeclared implementer files  

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `68099ed` — Warn on undeclared implementer files
- **Suggested revision**: Address the concern above.

### FINDING_101: panel [code-review/accepted]

## ```

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_102: panel [code-review/accepted]

## ```text

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_103: panel [code-review/accepted]

## ```tsv

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_104: panel [code-review/accepted]

## schema_version

- **Reviewer**: scope
- **Concern**: severity	focus_area	location	what	scenario_or_breakage	suggested_fix
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## Completion guidance still says the dispatcher **does not** cross-check `files_touched` to the tree / diff and that accuracy is “not mechanically enforced,” while NEVER #8 and `step2-implement.sh` Step 7a.1 now **do** enforce a best-effort porcelain-vs-manifest warning. Impact: implementers get contradictory instructions (ignore vs. care about undeclared paths). Suggested fix: reword those bullets to match Step 7a.1 (non-blocking warning, still no bail) and drop “no longer mechanically enforced.”

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## Inside the `STATUS=complete` path the OOS block runs `trap '_oos_cleanup' EXIT` and ends with `trap - EXIT`, which **clears the global EXIT trap** and never restores `trap 'rm -f "$LAUNCHER_TMP"' EXIT` from line 405. Scenario: every successful external-implementer `complete` run with an executable `append-execution-issue.sh` exits normally and leaves `$LAUNCHER_TMP` (65 KiB-capped launcher capture) behind under `$TMPDIR_ARG` until external cleanup. Suggested fix: after `_oos_cleanup`, restore the original EXIT trap (`trap 'rm -f "$LAUNCHER_TMP"' EXIT`) or avoid clobbering EXIT entirely (e.g. inline `rm` of the three OOS temp files only, no `trap`).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## That artifact used `git status --porcelain` + `awk 'NF {print $NF}'`, which breaks on paths containing spaces and some rename/copy layouts, yielding false negatives for OOS detection. If any consumer still has that exact hunk, replace with the NUL-delimited parsing now in the checkout.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## The `<feature_description>` asked to cross-reference working-tree changes against the plan’s **“Files to modify”** section as well as the manifest. The shipped logic is explicitly manifest-vs-`git status` only (`# ... plan-scope cross-check is not implemented here`). Impact: files that are **in-plan** but omitted from `files_touched` still produce the same warning as truly out-of-scope edits, and true plan violations that *are* listed in the manifest are invisible to this check. Suggested fix: parse the plan section (or reuse an existing parser if one exists) and classify paths as (in-plan, in-manifest, in-porcelain) before emitting the warning, or narrow the product language so “OOS” means “undeclared in manifest” only.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## The plan listed `codex-implementer.md` and `cursor-implementer.md`; the branch also updates [`agents/_implementer-base.md`](agents/_implementer-base.md), [`agents/gemini-implementer.md`](agents/gemini-implementer.md), [`SECURITY.md`](SECURITY.md), [`skills/implement/scripts/step2-implement.md`](skills/implement/scripts/step2-implement.md), harness `.md`, and [`larch-logs/...`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) artifacts. Parity for Gemini/base is reasonable, but it widens review/merge surface beyond the stated file list.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## The section says any violation “MUST cause you to abort,” but rule 8 tells the model **not** to edit out-of-scope files and to use `oos_observations[]` instead—compliant behavior is **not** an abort. Suggested fix: qualify the intro (“items 1–7”) or rephrase rule 8 as aligned with the abort framing.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Commits (`git log $(git merge-base HEAD main)..HEAD --oneline`):** `59c4f13 chore(larch-logs): flush implement run 2B036492-1DB7-464A-B254-4E6BB9D63853` and `68099ed Warn on undeclared implementer files`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **Hard constraint:** No files were created or edited (including the `.tsv` sidecar). TSV records appear in a fenced block at the end for copy/paste.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **Important** (`code-quality`, `plan`) — [`agents/_implementer-base.md`](agents/_implementer-base.md) ~42 and [`agents/cursor-implementer.md`](agents/cursor-implementer.md) ~152 (same pattern)  

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Important** (`code-quality`, `plan`) — [`agents/_implementer-base.md`](agents/_implementer-base.md) ~42 and [`agents/cursor-implementer.md`](agents/cursor-implementer.md) ~152 (same pattern)  
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## **Important** (`correctness`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~405, 666–699  

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Important** (`correctness`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~405, 666–699  
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## **Important** (`correctness`, `docs`): `agents/_implementer-base.md:79-82`, `agents/codex-implementer.md:125-128`, `agents/cursor-implementer.md:131-174`, `agents/gemini-implementer.md:131-220` (same paragraph in each) — Item 3 under “How to declare completion” still says the dispatcher does **not** cross-check `files_touched` against the working tree; `step2-implement.sh` Step 7a.1 now appends a best-effort Warning from that comparison, and `SECURITY.md` was updated accordingly. **Scenario:** External implementers and operators follow stale guidance, skip updating `files_touched`, and assume no mechanical coupling—undermining the new signal. **Fix:** Rewrite that bullet to describe the diagnostic Warning (non-blocking) and that it is not a full `git diff` audit.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 4. **Important** (`correctness`, `docs`): `agents/_implementer-base.md:79-82`, `agents/codex-implementer.md:125-128`, `agents/cursor-implementer.md:131-174`, `agents/gemini-implementer.md:131-220` (same paragraph in each) — Item 3 under “How to declare completion” still says the dispatcher does **not** cross-check `files_touched` against the working tree; `step2-implement.sh` Step 7a.1 now appends a best-effort Warning from that comparison, and `SECURITY.md` was updated accordingly. **Scenario:** External implementers and operators follow stale guidance, skip updating `files_touched`, and assume no mechanical coupling—undermining the new signal. **Fix:** Rewrite that bullet to describe the diagnostic Warning (non-blocking) and that it is not a full `git diff` audit.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## **Important** (`correctness`, `plan`) — [`skills/implement/scripts/step2-implement.sh:666-699`](skills/implement/scripts/step2-implement.sh): The OOS block installs `trap '_oos_cleanup' EXIT` and ends with `trap - EXIT`, which **removes the global EXIT trap** that was registered at [`step2-implement.sh:404-405`](skills/implement/scripts/step2-implement.sh) to delete `$LAUNCHER_TMP`. **Concrete scenario:** On any `STATUS=complete` path where `append-execution-issue.sh` is executable and `$TMPDIR_ARG` is a directory, after Step 7a.1 the shell has **no** EXIT cleanup; the launcher capture file under `$TMPDIR_ARG/${TOOL_TAG}-launcher-output.*` is left behind (and any later `emit_bailed`/`exit 0` on that same invocation also skips `rm`). **Fix:** After `_oos_cleanup`, restore the original handler, e.g. `trap 'rm -f "$LAUNCHER_TMP"' EXIT`, instead of `trap - EXIT` (or chain cleanup into a single EXIT trap).

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Important** (`correctness`, `plan`) — [`skills/implement/scripts/step2-implement.sh:666-699`](skills/implement/scripts/step2-implement.sh): The OOS block installs `trap '_oos_cleanup' EXIT` and ends with `trap - EXIT`, which **removes the global EXIT trap** that was registered at [`step2-implement.sh:404-405`](skills/implement/scripts/step2-implement.sh) to delete `$LAUNCHER_TMP`. **Concrete scenario:** On any `STATUS=complete` path where `append-execution-issue.sh` is executable and `$TMPDIR_ARG` is a directory, after Step 7a.1 the shell has **no** EXIT cleanup; the launcher capture file under `$TMPDIR_ARG/${TOOL_TAG}-launcher-output.*` is left behind (and any later `emit_bailed`/`exit 0` on that same invocation also skips `rm`). **Fix:** After `_oos_cleanup`, restore the original handler, e.g. `trap 'rm -f "$LAUNCHER_TMP"' EXIT`, instead of `trap - EXIT` (or chain cleanup into a single EXIT trap).
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## **Important** (`correctness`, `requirements`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~653–700  

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** (`correctness`, `requirements`) — [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) ~653–700  
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## **Important** (`risk-integration`, `correctness`): `skills/implement/scripts/step2-implement.sh:653-676` — The check runs on the full repo porcelain at `STATUS=complete` without distinguishing paths that pre-existed from operator/dispatcher state versus paths introduced by the implementer. **Scenario:** Same as implementer prompts: on a first invocation the operator may leave deliberate unrelated dirty files (`agents/_implementer-base.md:56-58`); every such path is “not in manifest” and triggers the new Warning even when the implementer stayed in-scope, drowning real OOS signals. **Fix:** Compare against a snapshot taken at implementer start (baseline tree hash or path set), or subtract paths dirty before launcher return using recorded baseline metadata if available.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Important** (`risk-integration`, `correctness`): `skills/implement/scripts/step2-implement.sh:653-676` — The check runs on the full repo porcelain at `STATUS=complete` without distinguishing paths that pre-existed from operator/dispatcher state versus paths introduced by the implementer. **Scenario:** Same as implementer prompts: on a first invocation the operator may leave deliberate unrelated dirty files (`agents/_implementer-base.md:56-58`); every such path is “not in manifest” and triggers the new Warning even when the implementer stayed in-scope, drowning real OOS signals. **Fix:** Compare against a snapshot taken at implementer start (baseline tree hash or path set), or subtract paths dirty before launcher return using recorded baseline metadata if available.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## **Important** (`risk-integration`, `correctness`): `skills/implement/scripts/step2-implement.sh:653-676` — `git status --porcelain | awk 'NF {print $NF}'` is unsafe for paths with spaces or unusual porcelain shapes, so `comm` can silently mis-enumerate the working set. **Scenario:** A renamed or spaced path yields a truncated or wrong token; OOS is missed (false negative) or bogus tokens appear (false positive). **Fix:** Use NUL-delimited `git status --porcelain=v1 -z` and parse records the way the implementation plan’s edge-case notes describe (or an equivalent robust parser).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Important** (`risk-integration`, `correctness`): `skills/implement/scripts/step2-implement.sh:653-676` — `git status --porcelain | awk 'NF {print $NF}'` is unsafe for paths with spaces or unusual porcelain shapes, so `comm` can silently mis-enumerate the working set. **Scenario:** A renamed or spaced path yields a truncated or wrong token; OOS is missed (false negative) or bogus tokens appear (false positive). **Fix:** Use NUL-delimited `git status --porcelain=v1 -z` and parse records the way the implementation plan’s edge-case notes describe (or an equivalent robust parser).
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## **Important** (`risk-integration`, `plan`) — [`agents/_implementer-base.md:42`](agents/_implementer-base.md), [`agents/_implementer-base.md:126`](agents/_implementer-base.md) (and the same “How to declare completion” / tail guidance mirrored in `agents/codex-implementer.md`, `agents/cursor-implementer.md`, `agents/gemini-implementer.md`): Text still says the dispatcher **does not** mechanically cross-check `files_touched` against reality, while new hard-guard **#8** and Step 7a.1 claim a **working-tree vs manifest** warning exists. **Concrete scenario:** An implementer relies on the older bullets, under-declares `files_touched`, and assumes there is no mechanical signal—operators lose trust in the new warning and the new NEVER bullet reads as false. **Fix:** Update those bullets to describe the undeclared-path Warning (without overstating it as a full diff or plan-scope enforcement).

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **Important** (`risk-integration`, `plan`) — [`agents/_implementer-base.md:42`](agents/_implementer-base.md), [`agents/_implementer-base.md:126`](agents/_implementer-base.md) (and the same “How to declare completion” / tail guidance mirrored in `agents/codex-implementer.md`, `agents/cursor-implementer.md`, `agents/gemini-implementer.md`): Text still says the dispatcher **does not** mechanically cross-check `files_touched` against reality, while new hard-guard **#8** and Step 7a.1 claim a **working-tree vs manifest** warning exists. **Concrete scenario:** An implementer relies on the older bullets, under-declares `files_touched`, and assumes there is no mechanical signal—operators lose trust in the new warning and the new NEVER bullet reads as false. **Fix:** Update those bullets to describe the undeclared-path Warning (without overstating it as a full diff or plan-scope enforcement).
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## **Important** (`risk-integration`, `requirements` + `plan`) — `<feature_description>`: Cross-reference against the plan’s **“Files to modify”** section was required; the shipped logic (see comment at [`step2-implement.sh:653-656`](skills/implement/scripts/step2-implement.sh)) only compares **working tree vs manifest** paths and does **not** parse `--plan-file`. The internal implementation plan matches the code, but the **higher-level feature text** is not satisfied. **Fix:** Parse the plan file’s declared file list (or narrow the written requirement to manifest-only parity).

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Important** (`risk-integration`, `requirements` + `plan`) — `<feature_description>`: Cross-reference against the plan’s **“Files to modify”** section was required; the shipped logic (see comment at [`step2-implement.sh:653-656`](skills/implement/scripts/step2-implement.sh)) only compares **working tree vs manifest** paths and does **not** parse `--plan-file`. The internal implementation plan matches the code, but the **higher-level feature text** is not satisfied. **Fix:** Parse the plan file’s declared file list (or narrow the written requirement to manifest-only parity).
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## **Important** (`risk-integration`, `requirements` / `plan`): `skills/implement/scripts/step2-implement.sh:653-676` — The shipped check only diffs working-tree paths from `git status --porcelain` against manifest `files_touched` / `tests_added_or_modified`. `<feature_description>` explicitly asked to cross-reference the plan’s **“Files to modify”** section as well; that comparison is not implemented, so files that are in-plan but omitted from the manifest (or in-manifest but out-of-plan) are invisible to this detector. **Scenario:** Implementer edits a plan-listed file but forgets to list it in `files_touched`; no Warning fires even though the change is “out of scope” relative to the plan. **Fix:** Parse the plan artifact (`--plan-file`) for declared paths (or reuse an existing export) and emit a separate Warning category for plan-vs-tree / plan-vs-manifest skew, or narrow the product wording to “manifest OOS only.”

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`, `requirements` / `plan`): `skills/implement/scripts/step2-implement.sh:653-676` — The shipped check only diffs working-tree paths from `git status --porcelain` against manifest `files_touched` / `tests_added_or_modified`. `<feature_description>` explicitly asked to cross-reference the plan’s **“Files to modify”** section as well; that comparison is not implemented, so files that are in-plan but omitted from the manifest (or in-manifest but out-of-plan) are invisible to this detector. **Scenario:** Implementer edits a plan-listed file but forgets to list it in `files_touched`; no Warning fires even though the change is “out of scope” relative to the plan. **Fix:** Parse the plan artifact (`--plan-file`) for declared paths (or reuse an existing export) and emit a separate Warning category for plan-vs-tree / plan-vs-manifest skew, or narrow the product wording to “manifest OOS only.”
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## **Important** `correctness` — `skills/implement/scripts/step2-implement.sh:653-670`, `skills/implement/scripts/test-step2-dispatch.sh:918-981`: the new detector only compares working-tree paths against manifest-declared paths, but the feature requires cross-checking both against the plan’s “Files to modify” scope. Concrete failing scenario: plan allows only `README.md`; implementer edits `docs/extra.md` and includes `docs/extra.md` in `manifest.files_touched`; `comm -23` is empty, no Warning is logged, and `git add -A` commits the out-of-plan file. Parse the plan scope and warn on `(working-tree paths ∪ manifest paths) - plan files`, and add a regression where the out-of-plan file is declared in the manifest.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `skills/implement/scripts/step2-implement.sh:653-670`, `skills/implement/scripts/test-step2-dispatch.sh:918-981`: the new detector only compares working-tree paths against manifest-declared paths, but the feature requires cross-checking both against the plan’s “Files to modify” scope. Concrete failing scenario: plan allows only `README.md`; implementer edits `docs/extra.md` and includes `docs/extra.md` in `manifest.files_touched`; `comm -23` is empty, no Warning is logged, and `git add -A` commits the out-of-plan file. Parse the plan scope and warn on `(working-tree paths ∪ manifest paths) - plan files`, and add a regression where the out-of-plan file is declared in the manifest.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## **Important** `correctness` — `skills/implement/scripts/step2-implement.sh:664-666`: `git status --porcelain | awk '{print $NF}'` corrupts valid paths containing whitespace or quoting, producing false OOS warnings. Concrete failing scenario: implementer creates and declares `docs/my note.md`; porcelain output is quoted/split, awk extracts only the last whitespace-delimited token, so `comm` treats the declared file as undeclared. Use a NUL-delimited path source such as `git status --porcelain=v1 -z` or `git diff --name-only -z`, and add a regression for a declared path with spaces.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` — `skills/implement/scripts/step2-implement.sh:664-666`: `git status --porcelain | awk '{print $NF}'` corrupts valid paths containing whitespace or quoting, producing false OOS warnings. Concrete failing scenario: implementer creates and declares `docs/my note.md`; porcelain output is quoted/split, awk extracts only the last whitespace-delimited token, so `comm` treats the declared file as undeclared. Use a NUL-delimited path source such as `git status --porcelain=v1 -z` or `git diff --name-only -z`, and add a regression for a declared path with spaces.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## **Important** | **correctness** | [`skills/implement/scripts/step2-implement.sh:405-405`](skills/implement/scripts/step2-implement.sh) and [`skills/implement/scripts/step2-implement.sh:666-699`](skills/implement/scripts/step2-implement.sh) | After the OOS block runs successfully, `trap - EXIT` removes **all** EXIT handlers, including the original `trap 'rm -f "$LAUNCHER_TMP"' EXIT` registered before the launcher runs. The comment at 663–664 claims the cleanup function exists so the prior trap is “not overwritten,” but the sequence still ends with `trap - EXIT`, which leaves **no** EXIT trap for the rest of the script. | **Scenario:** On every `STATUS=complete` path that executes Step 7a.1, `${TOOL_TAG}-launcher-output.*` under `$TMPDIR_ARG` is no longer deleted on normal script exit; launcher output (up to what was written before `head -c` truncation of the in-memory read) can linger on disk in the session tmpdir until manual cleanup or TTL. | Restore the previous trap after `_oos_cleanup`, e.g. capture `trap -p EXIT` before line 666 and `eval` it after 699, or chain cleanup in one trap and avoid `trap - EXIT` without re-registering `rm -f "$LAUNCHER_TMP"`.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Important** | **correctness** | [`skills/implement/scripts/step2-implement.sh:405-405`](skills/implement/scripts/step2-implement.sh) and [`skills/implement/scripts/step2-implement.sh:666-699`](skills/implement/scripts/step2-implement.sh) | After the OOS block runs successfully, `trap - EXIT` removes **all** EXIT handlers, including the original `trap 'rm -f "$LAUNCHER_TMP"' EXIT` registered before the launcher runs. The comment at 663–664 claims the cleanup function exists so the prior trap is “not overwritten,” but the sequence still ends with `trap - EXIT`, which leaves **no** EXIT trap for the rest of the script. | **Scenario:** On every `STATUS=complete` path that executes Step 7a.1, `${TOOL_TAG}-launcher-output.*` under `$TMPDIR_ARG` is no longer deleted on normal script exit; launcher output (up to what was written before `head -c` truncation of the in-memory read) can linger on disk in the session tmpdir until manual cleanup or TTL. | Restore the previous trap after `_oos_cleanup`, e.g. capture `trap -p EXIT` before line 666 and `eval` it after 699, or chain cleanup in one trap and avoid `trap - EXIT` without re-registering `rm -f "$LAUNCHER_TMP"`.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## **Important** | **risk-integration** | [`skills/implement/scripts/step2-implement.sh:653-656`](skills/implement/scripts/step2-implement.sh); feature text in `<feature_description>` | The product ask was to cross-reference the working tree against both the manifest **and** the plan’s “Files to modify” section. The shipped logic explicitly compares porcelain paths only to manifest paths (`plan-scope cross-check is not implemented here`). | **Scenario:** An implementer edits a file **not** listed in the plan but adds it to `files_touched` to satisfy the manifest check — no warning despite plan-scope violation. Conversely, plan-only enforcement is still manual. | Parse `--plan-file` for declared paths when present and include them in the allowed set (or narrow SECURITY/agent copy so operators are not told plan scope is mechanically checked).

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Important** | **risk-integration** | [`skills/implement/scripts/step2-implement.sh:653-656`](skills/implement/scripts/step2-implement.sh); feature text in `<feature_description>` | The product ask was to cross-reference the working tree against both the manifest **and** the plan’s “Files to modify” section. The shipped logic explicitly compares porcelain paths only to manifest paths (`plan-scope cross-check is not implemented here`). | **Scenario:** An implementer edits a file **not** listed in the plan but adds it to `files_touched` to satisfy the manifest check — no warning despite plan-scope violation. Conversely, plan-only enforcement is still manual. | Parse `--plan-file` for declared paths when present and include them in the allowed set (or narrow SECURITY/agent copy so operators are not told plan scope is mechanically checked).
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## **Important**, `correctness`, [`skills/implement/scripts/step2-implement.sh:405-405`](skills/implement/scripts/step2-implement.sh) and [`skills/implement/scripts/step2-implement.sh:663-699`](skills/implement/scripts/step2-implement.sh): The early `trap 'rm -f "$LAUNCHER_TMP"' EXIT` is **replaced** by `trap '_oos_cleanup' EXIT` inside Step 7a.1, then cleared with `trap - EXIT`. After a successful `STATUS=complete` run, **no EXIT trap remains** to delete `$LAUNCHER_TMP`, so the launcher capture file is left under `$TMPDIR_ARG` until something else removes the tmpdir. Concrete scenario: every successful external-implementer completion leaks one `*-launcher-output.*` file for the lifetime of the tmpdir (wasted disk; noisy for operators inspecting tmpdir). **Suggested fix:** Save the prior trap (`prior=$(trap -p EXIT)`), run OOS cleanup, then `eval "$prior"` or use a dedicated `trap` that runs both `_oos_cleanup` and `rm -f "$LAUNCHER_TMP"` without ever calling bare `trap - EXIT`.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important**, `correctness`, [`skills/implement/scripts/step2-implement.sh:405-405`](skills/implement/scripts/step2-implement.sh) and [`skills/implement/scripts/step2-implement.sh:663-699`](skills/implement/scripts/step2-implement.sh): The early `trap 'rm -f "$LAUNCHER_TMP"' EXIT` is **replaced** by `trap '_oos_cleanup' EXIT` inside Step 7a.1, then cleared with `trap - EXIT`. After a successful `STATUS=complete` run, **no EXIT trap remains** to delete `$LAUNCHER_TMP`, so the launcher capture file is left under `$TMPDIR_ARG` until something else removes the tmpdir. Concrete scenario: every successful external-implementer completion leaks one `*-launcher-output.*` file for the lifetime of the tmpdir (wasted disk; noisy for operators inspecting tmpdir). **Suggested fix:** Save the prior trap (`prior=$(trap -p EXIT)`), run OOS cleanup, then `eval "$prior"` or use a dedicated `trap` that runs both `_oos_cleanup` and `rm -f "$LAUNCHER_TMP"` without ever calling bare `trap - EXIT`.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## **Important**, `risk-integration`, [`skills/implement/scripts/step2-implement.sh:653-656`](skills/implement/scripts/step2-implement.sh): The feature text and implementation plan call for cross-referencing the working tree against the plan’s **“Files to modify”** section; the shipped comment states **“plan-scope cross-check is not implemented here.”** The warning therefore attributes every undeclared porcelain path to the **external implementer**, even when the delta is only **manifest incompleteness** (implementer touched nothing extra) or **pre-existing operator dirt** (allowed by the start-of-invocation instructions). Concrete scenario: Operator leaves `notes.txt` dirty before Step 2; manifest lists only `foo.ts`; Step 7a.1 logs a loud Warning blaming the implementer for `notes.txt`. **Suggested fix:** Parse plan file paths and subtract them (and/or baseline dirty set taken before launch, if available), or soften the Warning copy to “undeclared vs manifest” without blaming the tool.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Important**, `risk-integration`, [`skills/implement/scripts/step2-implement.sh:653-656`](skills/implement/scripts/step2-implement.sh): The feature text and implementation plan call for cross-referencing the working tree against the plan’s **“Files to modify”** section; the shipped comment states **“plan-scope cross-check is not implemented here.”** The warning therefore attributes every undeclared porcelain path to the **external implementer**, even when the delta is only **manifest incompleteness** (implementer touched nothing extra) or **pre-existing operator dirt** (allowed by the start-of-invocation instructions). Concrete scenario: Operator leaves `notes.txt` dirty before Step 2; manifest lists only `foo.ts`; Step 7a.1 logs a loud Warning blaming the implementer for `notes.txt`. **Suggested fix:** Parse plan file paths and subtract them (and/or baseline dirty set taken before launch, if available), or soften the Warning copy to “undeclared vs manifest” without blaming the tool.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## **Latent** (`code-quality`, `architecture`): `agents/_implementer-base.md:64-73` (and mirrored `agents/codex-implementer.md:112-119`, `agents/cursor-implementer.md:118-165`, `agents/gemini-implementer.md:118-211`) — The “Hard guards” preamble states every violation **must** end in `status=bailed`, but new NEVER **#8** instructs using `oos_observations[]` instead of editing out-of-plan files, without a bail path if violation already occurred. **Scenario:** Prompt authors treat #8 as softer than other guards, or models over-bail trying to reconcile the section header with the rule. **Fix:** Move scope discipline to a separate “Scope / PR hygiene” section or qualify the preamble (mechanical git safety vs scope policy).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 5. **Latent** (`code-quality`, `architecture`): `agents/_implementer-base.md:64-73` (and mirrored `agents/codex-implementer.md:112-119`, `agents/cursor-implementer.md:118-165`, `agents/gemini-implementer.md:118-211`) — The “Hard guards” preamble states every violation **must** end in `status=bailed`, but new NEVER **#8** instructs using `oos_observations[]` instead of editing out-of-plan files, without a bail path if violation already occurred. **Scenario:** Prompt authors treat #8 as softer than other guards, or models over-bail trying to reconcile the section header with the rule. **Fix:** Move scope discipline to a separate “Scope / PR hygiene” section or qualify the preamble (mechanical git safety vs scope policy).
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## **Latent** (`correctness`) — Precomputed [`diff.txt`](file:///Users/zhupanov/.cache/larch/sessions/claude-implement-larch5-e9ECRm/round-5/diff.txt) hunks for `step2-implement.sh`  

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 6. **Latent** (`correctness`) — Precomputed [`diff.txt`](file:///Users/zhupanov/.cache/larch/sessions/claude-implement-larch5-e9ECRm/round-5/diff.txt) hunks for `step2-implement.sh`  
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## **Latent** (`correctness`, `plan`) — If `jq` fails or emits no manifest paths (corrupt/empty `files_touched` / `tests_added_or_modified`), `MANIFEST_PATHS_FILE` can be empty and **every** porcelain path becomes “OOS,” producing a **noisy false-positive** Warning. **Scenario:** Broken manifest after successful edit → operator sees a large spurious warning list. **Fix:** Treat `jq` failure separately (bail or skip) instead of silently emptying the allowlist.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 7. **Latent** (`correctness`, `plan`) — If `jq` fails or emits no manifest paths (corrupt/empty `files_touched` / `tests_added_or_modified`), `MANIFEST_PATHS_FILE` can be empty and **every** porcelain path becomes “OOS,” producing a **noisy false-positive** Warning. **Scenario:** Broken manifest after successful edit → operator sees a large spurious warning list. **Fix:** Treat `jq` failure separately (bail or skip) instead of silently emptying the allowlist.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## **Latent** (`correctness`, `plan`) — Precomputed [`diff.txt` hunk `step2-implement.sh:447-451`](file:///Users/zhupanov/.cache/larch/sessions/claude-implement-larch5-e9ECRm/round-5/diff.txt): `git status --porcelain | awk 'NF {print $NF}'` is **unsafe for paths with spaces** (and other multi-field porcelain shapes), so `comm` can compare the wrong path set. **Current branch file** replaces this with `status --porcelain=v1 -z` parsing ([`step2-implement.sh:668-682`](skills/implement/scripts/step2-implement.sh))—good—**but** if anything reverts to the awk form from the cached diff, the bug returns. **Fix:** Keep the `-z` path (or another porcelain-safe parser) in any merge.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 4. **Latent** (`correctness`, `plan`) — Precomputed [`diff.txt` hunk `step2-implement.sh:447-451`](file:///Users/zhupanov/.cache/larch/sessions/claude-implement-larch5-e9ECRm/round-5/diff.txt): `git status --porcelain | awk 'NF {print $NF}'` is **unsafe for paths with spaces** (and other multi-field porcelain shapes), so `comm` can compare the wrong path set. **Current branch file** replaces this with `status --porcelain=v1 -z` parsing ([`step2-implement.sh:668-682`](skills/implement/scripts/step2-implement.sh))—good—**but** if anything reverts to the awk form from the cached diff, the bug returns. **Fix:** Keep the `-z` path (or another porcelain-safe parser) in any merge.
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## **Latent** | **correctness** | [`skills/implement/scripts/step2-implement.sh:658-700`](skills/implement/scripts/step2-implement.sh) | The OOS diagnostic runs inside `{ … } || true` while `set -e` is active. For a `{ … } || true` disjunct, Bash suppresses `errexit` for commands inside the brace group, so intermediate failures (e.g. `git status`, `jq`, `comm`) may not abort the block; the group can continue with partial/empty inputs and still exit 0. | **Scenario:** Transient `git` or `jq` failure yields a false negative (no Warning) or a misleading empty OOS set without surfacing an error, because failures are swallowed by design. | Drop the blanket `|| true` on the outer group, handle errors explicitly, or re-enable strict failure for critical substeps.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Latent** | **correctness** | [`skills/implement/scripts/step2-implement.sh:658-700`](skills/implement/scripts/step2-implement.sh) | The OOS diagnostic runs inside `{ … } || true` while `set -e` is active. For a `{ … } || true` disjunct, Bash suppresses `errexit` for commands inside the brace group, so intermediate failures (e.g. `git status`, `jq`, `comm`) may not abort the block; the group can continue with partial/empty inputs and still exit 0. | **Scenario:** Transient `git` or `jq` failure yields a false negative (no Warning) or a misleading empty OOS set without surfacing an error, because failures are swallowed by design. | Drop the blanket `|| true` on the outer group, handle errors explicitly, or re-enable strict failure for critical substeps.
- **Suggested revision**: Address the concern above.

### FINDING_30: panel [code-review/accepted]

## **Latent** | **security** | [`skills/implement/scripts/step2-implement.sh:690-696`](skills/implement/scripts/step2-implement.sh) | OOS paths from `git`/`jq` are interpolated into `--entry` and written into `execution-issues.md` without redaction or delimiter hardening (unlike manifest text fields that go through `redact-secrets.sh` elsewhere). | **Scenario:** A hostile or buggy tool creates a path containing newlines or markdown-like text; the warning entry can distort `execution-issues.md` structure or add misleading prose when that file is later shown to humans or an LLM (prompt-injection-style confusion, not filesystem escape). | Stage the message with `--entry-file`, strip/escape newlines, or pipe through the same redaction helpers used for other execution-issue content.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Latent** | **security** | [`skills/implement/scripts/step2-implement.sh:690-696`](skills/implement/scripts/step2-implement.sh) | OOS paths from `git`/`jq` are interpolated into `--entry` and written into `execution-issues.md` without redaction or delimiter hardening (unlike manifest text fields that go through `redact-secrets.sh` elsewhere). | **Scenario:** A hostile or buggy tool creates a path containing newlines or markdown-like text; the warning entry can distort `execution-issues.md` structure or add misleading prose when that file is later shown to humans or an LLM (prompt-injection-style confusion, not filesystem escape). | Stage the message with `--entry-file`, strip/escape newlines, or pipe through the same redaction helpers used for other execution-issue content.
- **Suggested revision**: Address the concern above.

### FINDING_31: panel [code-review/accepted]

## **Latent**, `architecture`, [`skills/implement/scripts/test-step2-dispatch.sh:918-922`](skills/implement/scripts/test-step2-dispatch.sh): Test 18 documents that ordering relative to `git commit` is **not** asserted; the feature asked for visibility **before** `git add -A && git commit`. The test only checks file content and `STATUS=complete`, so a future regression could move the Warning **after** the commit (or omit it on some path) without failing the harness. **Suggested fix:** Assert timestamp/order (e.g. `execution-issues.md` mtime before new `HEAD` commit, or a sentinel written mid-script if you add one in tests only).

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 5. **Latent**, `architecture`, [`skills/implement/scripts/test-step2-dispatch.sh:918-922`](skills/implement/scripts/test-step2-dispatch.sh): Test 18 documents that ordering relative to `git commit` is **not** asserted; the feature asked for visibility **before** `git add -A && git commit`. The test only checks file content and `STATUS=complete`, so a future regression could move the Warning **after** the commit (or omit it on some path) without failing the harness. **Suggested fix:** Assert timestamp/order (e.g. `execution-issues.md` mtime before new `HEAD` commit, or a sentinel written mid-script if you add one in tests only).
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## **Latent**, `correctness`, [`agents/_implementer-base.md:42-42`](agents/_implementer-base.md): Bullet 3 under “How to declare completion” still says the dispatcher **does NOT cross-check** `files_touched` against the actual diff, which is **no longer strictly true** once Step 7a.1’s porcelain-vs-manifest Warning exists (while diff-based cross-check may still be absent). Readers get contradictory mental models of the trust boundary. **Suggested fix:** Reword to distinguish “no `git diff` / subject cross-check” vs “best-effort undeclared-path Warning (Step 7a.1).”

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **Latent**, `correctness`, [`agents/_implementer-base.md:42-42`](agents/_implementer-base.md): Bullet 3 under “How to declare completion” still says the dispatcher **does NOT cross-check** `files_touched` against the actual diff, which is **no longer strictly true** once Step 7a.1’s porcelain-vs-manifest Warning exists (while diff-based cross-check may still be absent). Readers get contradictory mental models of the trust boundary. **Suggested fix:** Reword to distinguish “no `git diff` / subject cross-check” vs “best-effort undeclared-path Warning (Step 7a.1).”
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## **Latent**, `risk-integration`, [`agents/_implementer-base.md:34`](agents/_implementer-base.md) vs [`agents/codex-implementer.md:54`](agents/codex-implementer.md) / [`agents/cursor-implementer.md`](agents/cursor-implementer.md) / [`agents/gemini-implementer.md:60`](agents/gemini-implementer.md): `_implementer-base.md` rule 8 ends with **“this rule is prospective guidance … not a bail trigger for scope already committed,”** but the generated `*-implementer.md` copies omit that clause and still sit under the global preamble **“Violating any of them MUST cause you to abort”** ([`agents/codex-implementer.md:45`](agents/codex-implementer.md)). Concrete scenario: A model infers it must `status=bailed` after any scope slip, or conversely treats the preamble as meaningless noise—both harm the “Hard guards” contract. **Suggested fix:** Regenerate the three implementer prompts from base (or hand-sync) and optionally narrow the preamble (“rules 1–6 …”) so it matches machine-enforced bails.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Latent**, `risk-integration`, [`agents/_implementer-base.md:34`](agents/_implementer-base.md) vs [`agents/codex-implementer.md:54`](agents/codex-implementer.md) / [`agents/cursor-implementer.md`](agents/cursor-implementer.md) / [`agents/gemini-implementer.md:60`](agents/gemini-implementer.md): `_implementer-base.md` rule 8 ends with **“this rule is prospective guidance … not a bail trigger for scope already committed,”** but the generated `*-implementer.md` copies omit that clause and still sit under the global preamble **“Violating any of them MUST cause you to abort”** ([`agents/codex-implementer.md:45`](agents/codex-implementer.md)). Concrete scenario: A model infers it must `status=bailed` after any scope slip, or conversely treats the preamble as meaningless noise—both harm the “Hard guards” contract. **Suggested fix:** Regenerate the three implementer prompts from base (or hand-sync) and optionally narrow the preamble (“rules 1–6 …”) so it matches machine-enforced bails.
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## **Nit** (`code-quality`) — [`agents/_implementer-base.md`](agents/_implementer-base.md) (Hard guards intro) + new item 8  

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 4. **Nit** (`code-quality`) — [`agents/_implementer-base.md`](agents/_implementer-base.md) (Hard guards intro) + new item 8  
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## **Nit** (`code-quality`, `plan`) — Implementation plan text called for `agents/cursor-implementer.md` **NEVER #7** “after NEVER #6”; the diff adds a new **#8** while keeping “Control artifacts” as **#7** (same for Codex / shared base). Behavior is fine; only the literal numbering in the plan note is off.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 5. **Nit** (`code-quality`, `plan`) — Implementation plan text called for `agents/cursor-implementer.md` **NEVER #7** “after NEVER #6”; the diff adds a new **#8** while keeping “Control artifacts” as **#7** (same for Codex / shared base). Behavior is fine; only the literal numbering in the plan note is off.
- **Suggested revision**: Address the concern above.

### FINDING_36: panel [code-review/accepted]

## **Nit** (`code-quality`, `plan`) — [`agents/_implementer-base.md`](agents/_implementer-base.md) (and mirrors): The “Hard guards” preamble still says violations **MUST** abort with `status=bailed`, while new **#8** tells the model to use `oos_observations[]` instead of editing—without stating that **editing** an out-of-plan file itself must trigger a bail. Minor normative tension.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 6. **Nit** (`code-quality`, `plan`) — [`agents/_implementer-base.md`](agents/_implementer-base.md) (and mirrors): The “Hard guards” preamble still says violations **MUST** abort with `status=bailed`, while new **#8** tells the model to use `oos_observations[]` instead of editing—without stating that **editing** an out-of-plan file itself must trigger a bail. Minor normative tension.
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## **Nit** (`code-quality`, `risk-integration`) — Scope vs. attached implementation plan  

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 5. **Nit** (`code-quality`, `risk-integration`) — Scope vs. attached implementation plan  
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## **Nit** (`risk-integration`): `skills/implement/scripts/test-step2-dispatch.sh:612-675` — Test 18 proves the Warning exists alongside `STATUS=complete` but does not assert ordering relative to `git commit` (only narrative in `test-step2-dispatch.md`). **Scenario:** A future refactor could move the append after the commit without failing the test. **Fix:** Add a cheap ordering probe (e.g., marker file touched before/after commit, or assert file mtime ordering vs `.git` commit) if ordering is load-bearing.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 7. **Nit** (`risk-integration`): `skills/implement/scripts/test-step2-dispatch.sh:612-675` — Test 18 proves the Warning exists alongside `STATUS=complete` but does not assert ordering relative to `git commit` (only narrative in `test-step2-dispatch.md`). **Scenario:** A future refactor could move the append after the commit without failing the test. **Fix:** Add a cheap ordering probe (e.g., marker file touched before/after commit, or assert file mtime ordering vs `.git` commit) if ordering is load-bearing.
- **Suggested revision**: Address the concern above.

### FINDING_39: panel [code-review/accepted]

## **Nit** (`risk-integration`, `plan`): `agents/cursor-implementer.md:163-165` — Plan text called for “NEVER #7” parity on Cursor while Codex got “NEVER #8”; the branch adds a new **#8** in all implementer prompts (including Gemini/base), so numbering diverges from the written plan only. **Fix:** None if team accepts unified numbering; otherwise renumber Cursor-only as specified.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 6. **Nit** (`risk-integration`, `plan`): `agents/cursor-implementer.md:163-165` — Plan text called for “NEVER #7” parity on Cursor while Codex got “NEVER #8”; the branch adds a new **#8** in all implementer prompts (including Gemini/base), so numbering diverges from the written plan only. **Fix:** None if team accepts unified numbering; otherwise renumber Cursor-only as specified.
- **Suggested revision**: Address the concern above.

### FINDING_40: panel [code-review/accepted]

## **Nit** | **code-quality** | [`agents/_implementer-base.md`](agents/_implementer-base.md) (and generated parity in `agents/codex-implementer.md`, `agents/cursor-implementer.md`, `agents/gemini-implementer.md` per diff) — “How to declare completion” bullet 3 still says the dispatcher does not cross-check the manifest against the actual diff, while NEVER #8 says undeclared working-tree paths are detected. | Readers get conflicting expectations about what is and is not mechanically checked. | Reword bullet 3 to describe the new manifest-vs-porcelain warning and clarify it is not a full diff/subject gate.

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 6. **Nit** | **code-quality** | [`agents/_implementer-base.md`](agents/_implementer-base.md) (and generated parity in `agents/codex-implementer.md`, `agents/cursor-implementer.md`, `agents/gemini-implementer.md` per diff) — “How to declare completion” bullet 3 still says the dispatcher does not cross-check the manifest against the actual diff, while NEVER #8 says undeclared working-tree paths are detected. | Readers get conflicting expectations about what is and is not mechanically checked. | Reword bullet 3 to describe the new manifest-vs-porcelain warning and clarify it is not a full diff/subject gate.
- **Suggested revision**: Address the concern above.

### FINDING_41: panel [code-review/accepted]

## **Nit** | **code-quality** | [`skills/implement/scripts/step2-implement.sh:663-664`](skills/implement/scripts/step2-implement.sh) | The comment says the cleanup function avoids overwriting the prior EXIT trap, but the implementation still replaces the trap and then clears it entirely with `trap - EXIT`, contradicting both the comment and the stated intent. | Align comment with behavior or fix the trap lifecycle (same as finding 1).

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **Nit** | **code-quality** | [`skills/implement/scripts/step2-implement.sh:663-664`](skills/implement/scripts/step2-implement.sh) | The comment says the cleanup function avoids overwriting the prior EXIT trap, but the implementation still replaces the trap and then clears it entirely with `trap - EXIT`, contradicting both the comment and the stated intent. | Align comment with behavior or fix the trap lifecycle (same as finding 1).
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## **Read-only note:** Hard constraints forbid writing the TSV sidecar to disk. Structured records are below for you to save as `…/review-output.tsv` if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## **Sidecar file:** Hard constraints forbid writing `*.tsv` to disk. TSV records are in the fenced block at the end for you to save if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## **Structured TSV** (copy to sidecar manually; read-only mode prevented writing `diff.txt.tsv`):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## **TSV (copy to sidecar manually — no file written per read-only constraint):**

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_46: panel [code-review/accepted]

## ---

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_47: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	code-quality	agents/_implementer-base.md:42 agents/cursor-implementer.md:152	Stale prose claims files_touched is not mechanically cross-checked	Conflicts with NEVER #8 and Step 7a.1; weakens implementer compliance	Reword to match best-effort 7a.1 warning semantics
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	code-quality	skills/implement/scripts/step2-implement.sh:653-700	Manifest-vs-porcelain warning only; no cross-check to plan Files to modify as required by feature_description	Paths allowed by the plan but missing from files_touched trigger the same warning as truly off-plan edits; plan-only scope violations fully declared in the manifest never surface	Parse plan scope or narrow the spec; optionally classify warnings
- **Suggested revision**: Address the concern above.

### FINDING_49: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	agents/_implementer-base.md:79-82;agents/codex-implementer.md:125-128;agents/cursor-implementer.md:171-174;agents/gemini-implementer.md:219-220	Stale claim dispatcher never cross-checks files_touched vs tree	Models skip manifest hygiene; operators misread safety net	Update bullet to describe Step 7a.1 Warning
- **Suggested revision**: Address the concern above.

### FINDING_50: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:405,666-699	OOS block clears EXIT trap without restoring LAUNCHER_TMP cleanup	Normal STATUS=complete runs leak the 65KiB-capped launcher temp file under TMPDIR_ARG	Restore trap 'rm -f "$LAUNCHER_TMP"' after OOS cleanup or avoid EXIT trap clobber
- **Suggested revision**: Address the concern above.

### FINDING_51: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:405-699	OOS Step 7a.1 replaces then clears EXIT trap so LAUNCHER_TMP is no longer removed on shell exit.	Each successful STATUS=complete leaves a stray *-launcher-output.* file in the implement tmpdir until external cleanup.	Restore prior EXIT trap or chain cleanup: run OOS temp rm without bare trap - EXIT.
- **Suggested revision**: Address the concern above.

### FINDING_52: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:405-699	OOS block ends with trap - EXIT clearing all EXIT traps including rm LAUNCHER_TMP.	Launcher transcript tmpfile under TMPDIR_ARG survives normal exit after complete+7a.1.	Restore prior trap after cleanup or chain rm LAUNCHER_TMP into the temporary trap.
- **Suggested revision**: Address the concern above.

### FINDING_53: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:659-661	awk on porcelain last field is fragile for spaced or complex paths	comm input wrong; missed OOS or bogus paths	Use status -z NUL parsing
- **Suggested revision**: Address the concern above.

### FINDING_54: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/scripts/step2-implement.sh:666-699	OOS block ends with trap - EXIT clearing the global EXIT trap that removes LAUNCHER_TMP	STATUS=complete with executable append-execution-issue leaves ${TOOL}-launcher-output.* under TMPDIR_ARG; later exits skip rm too	After _oos_cleanup restore trap 'rm -f "$LAUNCHER_TMP"' EXIT instead of trap - EXIT
- **Suggested revision**: Address the concern above.

### FINDING_55: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	agents/_implementer-base.md:42,126 (mirrored codex/cursor/gemini)	Stale bullets say files_touched not mechanically checked; conflicts with new NEVER #8 and Step 7a.1	Model under-declares files_touched assuming no mechanical signal	Update prose to describe undeclared-path Warning without claiming full diff/plan enforcement
- **Suggested revision**: Address the concern above.

### FINDING_56: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-656	Plan Files to modify cross-check not implemented; warning text blames implementer for any undeclared porcelain path.	Pre-existing operator dirty files or incomplete manifest produce misleading Warnings.	Subtract plan-listed paths or baseline pre-run dirt; soften log wording.
- **Suggested revision**: Address the concern above.

### FINDING_57: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-656	Plan Files to modify not cross-checked; only manifest vs porcelain.	Undeclared-in-plan edits can pass if listed in manifest; plan drift not detected.	Parse plan paths or narrow documented scope.
- **Suggested revision**: Address the concern above.

### FINDING_58: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-656 (no plan parse)	Feature asked plan Files to modify cross-check; code only compares manifest vs working tree	Operator expects plan-scope drift signal; only manifest-declared allowlist is checked	Parse plan file section or revise requirement
- **Suggested revision**: Address the concern above.

### FINDING_59: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-676	Full-tree porcelain includes pre-existing operator dirty paths	First-invocation deliberate dirty files flood Warnings with false OOS	Baseline-subtract paths or document and gate warning
- **Suggested revision**: Address the concern above.

### FINDING_60: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/scripts/step2-implement.sh:653-676	Only manifest vs working-tree; plan Files to modify not cross-checked	Implementer omits a plan-listed path from files_touched; no Warning despite plan OOS	Parse plan paths or re-scope requirements to manifest-only
- **Suggested revision**: Address the concern above.

### FINDING_61: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	architecture	skills/implement/scripts/test-step2-dispatch.sh:918-922	Test 18 does not pin Warning emission before git commit.	Regression could reorder or drop Warning without failing CI.	Add ordering assertion or sentinel.
- **Suggested revision**: Address the concern above.

### FINDING_62: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	code-quality	agents/_implementer-base.md:64-73;agents/codex-implementer.md:112-119;agents/cursor-implementer.md:156-165;agents/gemini-implementer.md:156-211	Hard-guards bail preamble conflicts with NEVER 8 scope rule	Ambiguous strictness; erratic bail vs observe behavior	Split section or qualify preamble
- **Suggested revision**: Address the concern above.

### FINDING_63: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	agents/_implementer-base.md:42	Still claims dispatcher does not cross-check files_touched vs reality; Step 7a.1 adds a partial mechanical check.	Implementers mis-calibrate how complete files_touched must be.	Update bullet 3 to mention Step 7a.1 Warning vs diff cross-check.
- **Suggested revision**: Address the concern above.

### FINDING_64: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	round-5/diff.txt step2-implement.sh porcelain awk (superseded by -z on branch if kept)	awk $NF breaks on paths containing spaces	Modified path foo bar.txt yields wrong token for comm	Use keep porcelain -z parsing
- **Suggested revision**: Address the concern above.

### FINDING_65: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh (precomputed diff.txt hunk)	Awk-based last-field porcelain parsing	Paths with spaces or awkward rename lines can hide undeclared files from the warning	Prefer NUL-delimited status parsing as in current checkout
- **Suggested revision**: Address the concern above.

### FINDING_66: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh jq manifest path extraction	jq failure or empty output yields empty allowlist → all WT paths reported OOS	Corrupt manifest after edits triggers huge spurious warning	Handle jq non-zero / empty allowlist explicitly
- **Suggested revision**: Address the concern above.

### FINDING_67: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/scripts/step2-implement.sh:658-700	Brace group under set -e with || true suppresses errexit; failures may be silent.	git/jq failure could skip or corrupt OOS warning silently.	Tighten error handling for substeps.
- **Suggested revision**: Address the concern above.

### FINDING_68: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	risk-integration	agents/_implementer-base.md:34 vs agents/codex-implementer.md:45-54	Generated implementer prompts omit base rule-8 bail-trigger clarification while Hard guards preamble still says every violation must bail.	Model confusion on whether scope edits require bail vs Warning-only path.	Regenerate *-implementer.md from base; tighten preamble scope.
- **Suggested revision**: Address the concern above.

### FINDING_69: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	security	skills/implement/scripts/step2-implement.sh:690-696	Raw git paths in execution-issues entry without redaction/escaping.	Malformed paths could distort markdown or mislead downstream LLM readers.	Use entry-file plus newline strip or redact helpers.
- **Suggested revision**: Address the concern above.

### FINDING_70: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	agents/_implementer-base.md (How to declare bullet 3) vs NEVER #8	Conflicting statements about dispatcher cross-checks.	Operator/implementer confusion.	Harmonize manifest documentation bullets.
- **Suggested revision**: Address the concern above.

### FINDING_71: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	agents/_implementer-base.md Hard guards preamble vs new item 8	Preamble requires bail on any hard-guard violation; item 8 does not spell bail for OOS edits	Ambiguous whether OOS edit is mandatory bail	Clarify bail token for direct OOS edits or soften preamble
- **Suggested revision**: Address the concern above.

### FINDING_72: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	agents/_implementer-base.md:Hard-guards	Hard-guards intro says every violation must abort while rule 8 prescribes non-abort compliance	Mild spec confusion in the prompt pack	Scope the abort sentence to rules 1-7 or rephrase rule 8
- **Suggested revision**: Address the concern above.

### FINDING_73: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	agents/cursor-implementer.md (NEVER numbering vs plan)	Plan said add NEVER #7 after #6; shipped adds #8	None beyond doc plan mismatch	Align plan note or renumber if editorially required
- **Suggested revision**: Address the concern above.

### FINDING_74: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	code-quality	skills/implement/scripts/step2-implement.sh:663-664	Comment contradicts trap behavior (claims no overwrite of prior trap).	Maintainer confusion.	Fix comment or trap lifecycle.
- **Suggested revision**: Address the concern above.

### FINDING_75: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	agents/cursor-implementer.md:163-165	Cursor NEVER numbering differs from plan text	None if intentional	Renumber if plan fidelity matters
- **Suggested revision**: Address the concern above.

### FINDING_76: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	multiple under agents/ SECURITY.md larch-logs/	Extra touched files beyond the four-file implementation plan	Wider diff for reviewers and voters	Keep if intentional parity/docs; otherwise trim before merge
- **Suggested revision**: Address the concern above.

### FINDING_77: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: nit	risk-integration	skills/implement/scripts/test-step2-dispatch.sh:612-675	Test 18 does not pin append-before-commit ordering	Refactor could reorder without failing test	Add ordering assertion if required
- **Suggested revision**: Address the concern above.

### FINDING_78: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	code-quality	docs/linting.md (session git status)	Possible unrelated local modification	Not part of supplied diff.txt	Confirm intent or revert separately
- **Suggested revision**: Address the concern above.

### FINDING_79: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	code-quality	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json	Chore commit may embed local operator paths	Policy noise on PRs	Confirm run-log policy
- **Suggested revision**: Address the concern above.

### FINDING_80: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/	Committed run-log noise in PR.	Review burden; unrelated to OOS logic correctness.	Separate chore or gitignore policy.
- **Suggested revision**: Address the concern above.

### FINDING_81: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/* ; SECURITY.md	Large non-core artifacts/docs churn alongside functional change.	PR review noise; unrelated to OOS detection correctness.	Split chore flush / doc edits from functional PR.
- **Suggested revision**: Address the concern above.

### FINDING_82: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	risk-integration	larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json	Committed run log embeds absolute operator_cwd paths	Minor hygiene/PII-adjacent noise in repo	Redact paths in log flush or adjust logging policy
- **Suggested revision**: Address the concern above.

### FINDING_83: panel [code-review/accepted]

## Checking `step2-implement.sh` for EXIT traps and `LAUNCHER_TMP` usage — the new block may clobber them.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_84: panel [code-review/accepted]

## Checking existing `trap` usage in `step2-implement.sh` and reading the remainder of Test 18.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_85: panel [code-review/accepted]

## Checking for an existing `EXIT` trap in `step2-implement.sh` and how `append-execution-issue.sh` handles `--entry`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_86: panel [code-review/accepted]

## Checking surrounding `trap`/EXIT handling in `step2-implement.sh` and whether the plan-vs-manifest gap is intentional.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_87: panel [code-review/accepted]

## Checking the hard-guards preamble against NEVER #8 and whether `docs/linting.md` appears in the diff.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_88: panel [code-review/accepted]

## Checking the workspace version of the OOS block and trap interactions; the cached diff may differ from the working tree.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_89: panel [code-review/accepted]

## Checking whether `LAUNCHER_TMP` in the trap is erroneous and reading the Test 18 hunk.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_90: panel [code-review/accepted]

## Commits on the branch since `merge-base(HEAD, main)` (from your requested command):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_91: panel [code-review/accepted]

## Commits vs `main` (read-only): `68099ed Warn on undeclared implementer files`, `59c4f13 chore(larch-logs): flush implement run ...`. The cached `diff.txt` is a subset of what is on disk for `step2-implement.sh` (it shows an older hunk with `awk`/`trap` including `LAUNCHER_TMP` in the inner trap string); the review below uses the **current** [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) in the workspace for accurate line numbers, and notes where it diverges from the truncated precomputed diff.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_92: panel [code-review/accepted]

## Creating the plan-mode deliverable summarizing the review.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_93: panel [code-review/accepted]

## Here is the read-only review. Commits on the branch since `merge-base(HEAD, main)`: `59c4f13 chore(larch-logs): flush implement run 2B036492-…` and `68099ed Warn on undeclared implementer files`. The precomputed diff is capped; the checkout under `/Users/zhupanov/larch5` already differs from that diff in `step2-implement.sh` (NUL-delimited `git status`, `_oos_cleanup`, `trap - EXIT`). Findings below treat the **effective branch state** (checkout + diff) so nothing load-bearing is missed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_94: panel [code-review/accepted]

## Note: the cached `diff.txt` shows an earlier `step2-implement.sh` hunk (`awk` on porcelain, `trap` including `LAUNCHER_TMP`). The current working tree has a more elaborate Step 7a.1 (`status --porcelain=v1 -z`, rename handling, explicit cleanup). Findings below use the **current** [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) line numbers unless noted.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_95: panel [code-review/accepted]

## Per your read-only constraint, no files were written (including no `.tsv` sidecar on disk). Structured TSV is in a fenced block at the end.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_96: panel [code-review/accepted]

## Read-only constraint: **no sidecar file was written**. TSV rows appear in a fenced block at the end for you to copy to `diff.txt.tsv` if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_97: panel [code-review/accepted]

## Read-only mode: **no** `.tsv` file was created on disk. TSV records (tabs between fields):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_98: panel [code-review/accepted]

## Reading diff hunks for `step2-implement.sh`, `test-step2-dispatch.sh`, and agent files.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_99: panel [code-review/accepted]

## Reviewed the precomputed diff at `round-5/diff.txt` (hunks capped at 20 lines), cross-checked against the current [`skills/implement/scripts/step2-implement.sh`](skills/implement/scripts/step2-implement.sh) on disk (it has diverged from the diff in a few places), and used `git log $(git merge-base HEAD main)..HEAD --oneline` (read-only): `68099ed Warn on undeclared implementer files`, `59c4f13 chore(larch-logs): flush implement run …`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_100: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: Gathering the pre-computed diff and commit history (read-only) for a correctness-focused review.
- **Suggested revision**: Address the concern above.

### FINDING_101: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only review. We won't write files (including the TSV sidecar); we'll include TSV rows inline per your hard constraints.
- **Suggested revision**: Address the concern above.

### FINDING_102: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Gathering the pre-computed diff and commit list for a read-only Plan Fidelity review.
- **Suggested revision**: Address the concern above.

### FINDING_103: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: Gathering the diff and commit history for a read-only security-focused review. We won't write files (including the TSV sidecar); we'll include TSV lines in the response per your hard constraint.
- **Suggested revision**: Address the concern above.

### FINDING_104: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Gathering the pre-computed diff and commit history for a read-only review. We won't write files; we'll include TSV records in the response because hard constraints forbid creating the sidecar file.
- **Suggested revision**: Address the concern above.

### FINDING_105: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: Gathering the branch diff and commit list (read-only) to review testing, regression risk, and plan alignment.
- **Suggested revision**: Address the concern above.

### FINDING_106: panel [code-review/accepted]

## Searching the diff for planned files and reading relevant hunks.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_107: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading key sections of the changed files.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_108: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading key sections of the repo for line context.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_109: panel [code-review/accepted]

## Searching the diff for relevant hunks and reading key sections.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_110: panel [code-review/accepted]

## Searching the diff for relevant hunks; the full diff exceeds the read limit.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_111: panel [code-review/accepted]

## Verifying the branch vs main diff for `step2-implement.sh` — the cached diff may be stale relative to the working tree.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_112: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`code-quality`) — [`docs/linting.md`](docs/linting.md) appeared dirty in the session snapshot but is **not** in the provided `diff.txt`; if it still differs on the branch, it is unrelated noise for this feature unless intentionally bundled.

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Nit** (`code-quality`) — [`docs/linting.md`](docs/linting.md) appeared dirty in the session snapshot but is **not** in the provided `diff.txt`; if it still differs on the branch, it is unrelated noise for this feature unless intentionally bundled.
- **Suggested revision**: Address the concern above.

### FINDING_113: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`code-quality`): Second commit `59c4f13 chore(larch-logs): flush implement run …` bundles run metadata; worth confirming repo policy that operator-local paths in committed `larch-logs/` are acceptable—pre-existing pattern, not introduced by the OOS logic itself.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Nit** (`code-quality`): Second commit `59c4f13 chore(larch-logs): flush implement run …` bundles run metadata; worth confirming repo policy that operator-local paths in committed `larch-logs/` are acceptable—pre-existing pattern, not introduced by the OOS logic itself.
- **Suggested revision**: Address the concern above.

### FINDING_114: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`risk-integration`, `out_of_scope`) — Second commit on the branch adds/edits [`larch-logs/implement/2B036492-…/manifest.json`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) with absolute `operator_cwd` / `operator_repo_root` paths; that is run-log hygiene rather than OOS-detection logic, but it bakes machine-specific paths into the repo. Out of scope for OOS correctness, still worth a quick policy glance before merge.

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Nit** (`risk-integration`, `out_of_scope`) — Second commit on the branch adds/edits [`larch-logs/implement/2B036492-…/manifest.json`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/manifest.json) with absolute `operator_cwd` / `operator_repo_root` paths; that is run-log hygiene rather than OOS-detection logic, but it bakes machine-specific paths into the repo. Out of scope for OOS correctness, still worth a quick policy glance before merge.
- **Suggested revision**: Address the concern above.

### FINDING_115: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** | **out_of_scope** | [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/*`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) (from branch diff) | Run-log artifacts under `larch-logs/` add noise to PR review and can accidentally encourage committing session-local content; not a trust-boundary change introduced solely by the OOS feature. | Keep run logs out of the same commit as functional changes or document policy in contributing docs (pre-existing process issue).

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Nit** | **out_of_scope** | [`larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/*`](larch-logs/implement/2B036492-1DB7-464A-B254-4E6BB9D63853/) (from branch diff) | Run-log artifacts under `larch-logs/` add noise to PR review and can accidentally encourage committing session-local content; not a trust-boundary change introduced solely by the OOS feature. | Keep run logs out of the same commit as functional changes or document policy in contributing docs (pre-existing process issue).
- **Suggested revision**: Address the concern above.

### FINDING_116: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit**, `risk-integration`, `larch-logs/...` and large `SECURITY.md` / plan-goals churn in the branch diff: Appear driven by the flushed implement run (`59c4f13`) rather than the OOS-warning mechanics; they widen review surface and may be undesirable on the same PR as the functional change, but that is a process/PR-hygiene concern outside Step 7a.1 logic.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Nit**, `risk-integration`, `larch-logs/...` and large `SECURITY.md` / plan-goals churn in the branch diff: Appear driven by the flushed implement run (`59c4f13`) rather than the OOS-warning mechanics; they widen review surface and may be undesirable on the same PR as the functional change, but that is a process/PR-hygiene concern outside Step 7a.1 logic.
- **Suggested revision**: Address the concern above.

### FINDING_117: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: codex-generalist-output.txt
- **Concern**: No out-of-scope observations.
- **Suggested revision**: Address the concern above.

### FINDING_118: panel [code-review/accepted]

## `59c4f13` — chore(larch-logs): flush implement run …

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `59c4f13` — chore(larch-logs): flush implement run …
- **Suggested revision**: Address the concern above.

### FINDING_119: panel [code-review/accepted]

## `68099ed` — Warn on undeclared implementer files

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `68099ed` — Warn on undeclared implementer files
- **Suggested revision**: Address the concern above.

### FINDING_120: panel [code-review/accepted]

## ```

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_121: panel [code-review/accepted]

## ```text

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_122: panel [code-review/accepted]

## ```tsv

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_123: panel [code-review/accepted]

## `git show` was rejected in this environment; line ranges below are taken from the `git diff main...HEAD` hunks (new file sides).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_124: panel [code-review/accepted]

## schema_version

- **Reviewer**: scope
- **Concern**: severity	focus_area	location	what	scenario_or_breakage	suggested_fix
- **Suggested revision**: Address the concern above.

