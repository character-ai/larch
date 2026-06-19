### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=2, transient-retries=1)**:
  ```
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Password not found for account 'cursor-user' and service 'cursor-access-token'
Failed with exit code 1. Output size: 0 bytes.
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Password not found for account 'cursor-user' and service 'cursor-access-token'
Failed with exit code 1. Output size: 0 bytes.
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-migration-fidelity.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-migration-fidelity.txt)

Searching the repo for the G13 plan and cross-checking it against live consumers.
Found the G13 plan in the design session cache. Reading it and cross-checking against the codebase.
**Verdict:** The G13 plan (`~<TMPDIR>/plan.txt`, issue #4642) has a correct 16-entry verb map and a complete deletion/manifest inventory, but it under-specifies checkpoint-probe parity and omits several live `make lint` harnesses that still pin retired `.sh` paths.


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-migration-fidelity.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-migration-fidelity.txt)

Found **4 migration-fidelity issues**. I found no literal `G13` marker, so I reviewed the matching B1 migration plan at `larch-logs/design/2FCA6DE8-95ED-475C-A7AF-E8FA0EE1A819/plan.txt`.

## Findings

1. **[P1] Python checkpoint consumers are omitted from the cutover sweep.**
   - **Plan section:** `UPDATED: call-site cutover`, `larch-logs/design/2FCA6DE8-95ED-475C-A7AF-E8FA0EE1A819/plan.txt:156-160`.
   - **Plan deletion gate:** `Deletions`, `plan.txt:170-175`.
   - **Repo evidence:** `python/bootstrap.py:1435-1451` still invokes `scripts/rebase-checkpoint-probe.sh` with `--forked-target` and parses `ROUTE`.
   - **Repo evidence:** `python/step_7a.py:290-305` still invokes `scripts/rebase-checkpoint-probe.sh`.
   - **Issue:** The sweep lists `scripts/`, `skills/**`, `.claude/**`, docs, `Makefile`, workflows, README, and SECURITY. It does **not** include `python/**`. If the probe script is deleted after that sweep, these live Python consumers break.

2. **[P1] `push checkpoint-probe` lacks the live `--forked-target` and `ROUTE=` contract.**
   - **Plan section:** `Domain → verb → backing function mapping`, `plan.txt:59-65`.
   - **Plan section:** `structural + lint pins`, `plan.txt:159-160`.
   - **Repo evidence:** Bash probe accepts `--forked-target`, `scripts/rebase-checkpoint-probe.sh:12-47`, and maps it to `upstream/main`, `scripts/rebase-checkpoint-probe.sh:51-61`.
   - **Repo evidence:** Bash probe emits `ROUTE=continue|conflict|bail`, `scripts/rebase-checkpoint-probe.sh:340-381`.
   - **Repo evidence:** The CLI parser only accepts `step_prefix`, `short_name`, `--base-remote`, and `--base-ref`, `python/push.py:274-280`.
   - **Repo evidence:** The CLI emit path has no `ROUTE=` output, `python/push.py:176-203` and `python/push.py:292-304`.
   - **Issue:** Live orchestrator contracts require `ROUTE`, `skills/implement/SKILL.md:147-153`, and current live calls pass `--forked-target`, `skills/implement/SKILL.md:533-536` and `skills/implement/SKILL.md:717-720`.

3. **[P2] Makefile cleanup is too generic for the named deleted harnesses.**
   - **Plan section:** `structural + lint pins`, `plan.txt:159-160`.
   - **Plan section:** `Deletions`, `plan.txt:170-175`.
   - **Repo evidence:** `.PHONY` still includes probe and rebase-push harness targets, `Makefile:7`.
   - **Repo evidence:** shards still include `test-rebase-checkpoint-probe`, `test-phantom-probe-with-warn`, and `test-rebase-push-*`, `Makefile:122-144`.
   - **Repo evidence:** target recipes still call the shell harnesses, `Makefile:583-603`.
   - **Issue:** The plan says remove or retarget shard targets, but it does not enumerate the exact targets that correspond to the named deletions. If the scripts are deleted and any target remains, `make lint` still depends on deleted files.

4. **[P2] Deleted-file manifest coverage is not auditable from the plan.**
   - **Plan section:** `UPDATED: python/migrated-scripts.tsv`, `plan.txt:150-151`.
   - **Plan section:** `Deletions`, `plan.txt:170-175`.
   - **Repo contract:** manifest rows must be full repo-relative paths with issue IDs, `docs/python-migration.md:52-66`.
   - **Repo evidence:** current manifest format and rows are path-specific, `python/migrated-scripts.tsv:10-23`.
   - **Issue:** The plan gives a template, `scripts/<name>.sh`, and examples, but not the exact deleted path list. That makes `.md` sibling and `test-*.md` coverage hard to verify before implementation.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-migration-fidelity.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-migration-fidelity.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-migration-fidelity.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-migration-fidelity.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-migration-fidelity.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
✓ codex agent: completed (exit code 0, output 3445 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-retired-reference-sweeper.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-retired-reference-sweeper.txt)

Searching the repo for the G13 plan and cross-checking referenced paths against current files.
**Blocked:** Read-only tools could not access the repository. Every `Read`, `Grep`, `Glob`, and shell probe returned “Service temporarily unavailable” or empty output, so this G13 stale-reference review was **not executed**.

**What I attempted**
- `G13` search across `<OPERATOR_REPO_PATH>
- Read of `docs/python-migration.md`, `README.md`, and retired-script manifest candidates
- Agent transcript lookup under `<OPERATOR_REPO_PATH>/projects/Users-zhupanov-larch7/agent-transcripts`
- A delegated read-only subagent (same failures)

**What I need to deliver the review you asked for**
1. **G13 plan source** (GitHub issue URL/number, pasted plan block, or path in-repo), or a fresh turn once tools recover.
2. Successful read access to all of:
   - `docs/`, `skills/*/SKILL.md`, `.claude/rules/`
   - `python/` comments/docstrings
   - Test fixtures and allowlists (e.g. `lint-retired-scripts`, manifest files)
   - Retired-script manifest per `docs/python-migration.md`

**Planned sweep (not run yet)**
For each path the plan marks **retired** or **repointed to `python/cli.py`**:
- Literal `scripts/...` references in docs/skills/rules/comments/fixtures
- Fixtures embedding old bash paths
- Allowlists/manifest rows still listing live paths or omitting newly retired ones
- Plan sections naming surfaces with no matching repo update

**Output format I will use on retry** (per your wrapper):
- Each finding: **Plan section** + **repo path** + **file:line range**
- Separate lists for **stale references** vs **likely missing file surface**

**Next step:** Retry in a new turn with “retry G13 stale-reference review”, or paste the G13 plan block / issue link here. I will not invent plan sections or stale-reference findings without reading the files.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-retired-reference-sweeper.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-retired-reference-sweeper.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-retired-reference-sweeper.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-retired-reference-sweeper.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-retired-reference-sweeper.txt.launch-stderr)

❌ cursor agent: FAILED (exit code 1, output 0 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 2205 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-retired-reference-sweeper.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-retired-reference-sweeper.txt)

Found **3 in-scope issues**.


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt)

Reading the plan and tracing cited paths against the feature scope.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	blocking	completeness	python/release_finish.py:42-50	`_origin_repo` still shells out to `scripts/github-remote-repo.sh` but the plan only says to preserve the env override	The sibling `release_prepare.py` cutover is planned; `release_finish.py` is not. After deleting `github-remote-repo.sh`, `python/cli.py release finish` returns no origin repo when `LARCH_RELEASE_FINISH_ORIGIN_REPO` is unset, breaking the release skill finish step	Add `### UPDATED: python/release_finish.py` to replace the bash helper with `gh remote-repo` (mirror `release_prepare.py`); keep override semantics
2	in_scope	important	risk-integration	plan.txt:58-68	The issue E1 gate requires verifying `ci-failed-jobs.sh` / `ci-rerun-failed.sh` are ship-pr-only leftovers before deletion; the plan deletes them after harness parity only, with no explicit live-consumer audit step	An undiscovered bash caller outside the parity harnesses would break after deletion; the feature text calls for verify-before-delete, not assume-after-harness	Add a pre-delete grep/consumer checklist step (confirm callers are harness-only or already on `python/ci_monitor.py` / `cli.py ci failed-jobs` / `ci rerun-failed`) before manifest append and file deletion

**1. `python/release_finish.py` consumer cutover missing (blocking, completeness)**

The plan cuts over `python/release_prepare.py`, `python/session_env.py`, and `python/admission.py` from `github-remote-repo.sh`, but `### UPDATED: python/release_finish.py` only says to preserve `LARCH_RELEASE_FINISH_ORIGIN_REPO`. `_origin_repo()` still runs `bash scripts/github-remote-repo.sh origin` at lines 46–49. After the helper is deleted, release finish loses origin resolution unless the override is set.

**2. E1 verify-before-delete gate not spelled out (important, risk-integration)**

The feature scope requires confirming `ci-failed-jobs.sh` / `ci-rerun-failed.sh` are ship-pr-only leftovers before deletion. The plan maps them to CLI verbs, runs retargeted harnesses, and deletes them, but never documents an explicit live-consumer audit. Repo inspection suggests `python/ci_monitor.py` already owns the behavior and remaining references are harness/Makefile/docs, yet the issue gate asks for verification, not inference from harness parity alone.

---

**Assessment:** The plan otherwise tracks the G13 definition of done well: all 16 helpers are mapped, checkpoint-probe parity (including `ROUTE=` and larch-log trivial conflicts) is sequenced before probe deletion, structural harnesses and `migrated-scripts.tsv` are covered, and `make lint-retired-scripts` is in the test gate. The `release_finish.py` gap is the one materially blocking hole against “all consumers on `cli.py`.”
## Reviewer stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
✓ cursor agent: completed (exit code 0, output 3228 bytes)
  ```
### In-Scope Findings

1. **Important** - `risk-integration` - `larch-logs/design/2FCA6DE8-95ED-475C-A7AF-E8FA0EE1A819/plan.txt:108-109`, `:195-199`  
   The plan adds `python/test_migration_lint.py` coverage that embeds newly retired paths literally. Current fixture lines already use exact strings such as `scripts/resolve-repo.sh`, `scripts/ci-wait.sh`, and `scripts/git-current-branch.sh` at `python/test_migration_lint.py:282-331`, while the manifest warns not to put retired path literals directly in fixtures at `python/migrated-scripts.tsv:6-8`. Once those paths are appended to the manifest, `make lint-retired-scripts` can flag the tests themselves. Build those paths piecewise in fixtures.

2. **Important** - `risk-integration` - `larch-logs/design/2FCA6DE8-95ED-475C-A7AF-E8FA0EE1A819/plan.txt:123-127`, `:156-157`  
   The stale-reference sweep omits **Python comments/docstrings** as an explicit surface. Current Python docstrings contain full retired paths: `python/git.py:276` references `scripts/git-commit.sh`, and `python/push.py:1-2` references `scripts/git-push.sh`. If those paths are added to `python/migrated-scripts.tsv`, lint can fail or stale parity prose can survive. Add `python/**/*.py` comments/docstrings to the sweep.

3. **Important** - `security` - `larch-logs/design/2FCA6DE8-95ED-475C-A7AF-E8FA0EE1A819/plan.txt:159-160`, `:170-175`  
   The allowlist cleanup names `agent-lint.toml`, but not `.gitleaks.toml`. `.gitleaks.toml:14-15` and `:28` still allowlist `scripts/test-create-pr.sh`, `scripts/test-merge-pr.sh`, and `scripts/test-ci-wait.sh`, which the plan may delete under the `test-*.sh` retirement rule. If left behind, future files at those paths can bypass secret scanning. Add `.gitleaks.toml` to the allowlist sweep for every deleted harness.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-retired-reference-sweeper.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-retired-reference-sweeper.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-retired-reference-sweeper.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-retired-reference-sweeper.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-retired-reference-sweeper.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
✓ codex agent: completed (exit code 0, output 1823 bytes)
  ```
### In-Scope Findings

- **checkpoint-probe routing** Plan § **Approach** item 2 / **UPDATED: python/push.py** — omits **larch-log trivial-conflict auto-resolution**, which issue #4642’s design snapshot requires before deleting `rebase-checkpoint-probe.sh`. Bash implements the loop at ```257:337:scripts/rebase-checkpoint-probe.sh```; Python `checkpoint_probe_main` only calls `rebase.rebase_push` once at ```274:304:python/push.py``` with no `ROUTE=` and no `--forked-target`. **Suggested fix:** Add an explicit **UPDATED: python/push.py** (or `python/rebase.py`) step to port the `larch-logs/*` pre-pass, empty-continue rc=3 handling, and iteration cap; extend **UPDATED: python/test_push.py** beyond ROUTE/fork tests to cover those cases (today ```138:175:python/test_push.py``` has no `ROUTE=` or `--forked-target` coverage).

- **checkpoint-probe routing** Plan § **UPDATED: python/bootstrap.py** — live Step **1.r** routing depends on `ROUTE=` from the probe stdout. Bootstrap still shells to the `.sh` at ```1436:1447:python/bootstrap.py``` and defaults missing/invalid `ROUTE` to `bail`. Current Python probe cannot satisfy that contract. **Suggested fix:** Treat checkpoint-probe as a **re-port**, not a mechanical argv swap, and gate deletion on bootstrap routing tests passing with `push checkpoint-probe`.

- **checkpoint-probe routing** Plan § **UPDATED: python/step_7a.py** — Step **7a.r** still calls the bash probe at ```291:304:python/step_7a.py```. Fork base derivation exists in Python (```232:234:python/step_7a.py```), but cutover still needs the full probe contract (including `ROUTE=` if routing consumers parse it). **Suggested fix:** Align the **UPDATED: python/step_7a.py** step with the expanded probe port, not only `_run_cli("push", "checkpoint-probe", ...)`.

- **retirement-hygiene** Plan § **Files to modify** — missing updates for structural harnesses that `make lint` runs and that hard-require retired paths:
  - ```12:55:scripts/test-implement-rebase-macro.sh``` (`rebase-checkpoint-probe.sh` in bootstrap, SKILL fences, probe source)
  - ```221:222:scripts/test-implement-structure.sh``` and ```313:313:scripts/test-implement-structure.sh```
  - ```356:356:scripts/test-implement-fence-shape.sh``` (`create-branch.sh --check`)
  - ```19:19:scripts/test-implement-step8-exit3-first-fixer.sh``` (`scripts/gh-run-logs.sh` needle; plan updates `ship-pr-exit-matrix.md` but not this harness)

  Targets: `test-harnesses-4`, `test-harnesses-14`, `test-harnesses-16` in `Makefile`. **Suggested fix:** Add **UPDATED** rows for all four harnesses to the plan’s **Files to modify** section.

- **Makefile / parity gate** Plan § **Testing strategy** item 3 — does not address `python/test_merge_bash_parity.py`, which binds to `scripts/merge-pr.sh` at ```28:33:python/test_merge_bash_parity.py```. After deletion those tests **skip silently** (`skipif not MERGE_SH.is_file()`), weakening the plan Scope gate “confirm parity per verb before delete.” **Suggested fix:** Either retire/replace bash parity with pure pytest before delete, or add an explicit **UPDATED: python/test_merge_bash_parity.py** step.

- **plan fidelity** Plan § **Approach** item 4 vs issue #4642 design snapshot — **contradictory parity strategy**. Plan step 4 says temporarily retarget each `scripts/test-*.sh` harness; issue comment says “Do **not** retarget the legacy `test-*.sh` harnesses; pytest supersedes them.” **Suggested fix:** Pick one gate and align Approach §4, Testing strategy §2, and Failure modes §1.

- **verb map / live consumers** Plan § **UPDATED: .claude/skills/release/SKILL.md** — incomplete. Plan lists `gh resolve-repo`, `pr create`, `ci wait`, `merge pr`, but the release skill still invokes retired helpers at ```76:76:.claude/skills/release/SKILL.md``` (`rebase-push.sh` dry-run prose) and ```144:151:.claude/skills/release/SKILL.md``` (`create-pr.sh`, `ci-wait.sh`, `merge-pr.sh`). **Suggested fix:** Expand the release-skill update to cover every remaining `.sh` fence and dry-run prose.

- **deleted-file manifest** Plan § **UPDATED: python/migrated-scripts.tsv** — deletion inventory is complete for the 16 helpers plus listed harness `.sh`/`.md` pairs (lines 313–583). **Gap:** plan § **Clean references** does not list `skills/shared/skill-design-principles.md`, which still names `rebase-push.sh` at ```78:78:skills/shared/skill-design-principles.md```, or `skills/implement/scripts/step-7a.md` at ```29:29:skills/implement/scripts/step-7a.md```. **Suggested fix:** Add both to the prose-cleanup sweep (or manifest if deleted).

- **Makefile target cleanup** Plan § **UPDATED: Makefile** — correctly targets the 18 domain harness targets (`test-merge-pr`, `test-create-pr`, `test-rebase-push-*`, `test-rebase-checkpoint-probe`, `test-ci-*`, `test-gh-*`, `test-github-remote-repo`, `test-resolve-repo`). **Gap:** surviving harness targets above are not mentioned; shard coverage will fail until they are updated, not removed.

- **verb map** Plan § **Approach** item 1 — the 16-entry map matches `python/cli.py` registrations at ```428:447:python/cli.py```. **No map error found.** Current live Python subprocess consumers match the plan’s consumer list and still call `.sh` today:
  - `python/bootstrap.py` ```367:367```, ```776:776``` (`create-branch.sh`)
  - `python/admission.py` ```295:295``` (`github-remote-repo.sh`)
  - `python/session_env.py` ```1481:1481```
  - `python/release_prepare.py` ```75:75```, `python/release_finish.py` ```46:46```

- **missing CLI flag (current tree)** Plan § **Approach** item 2 — `push checkpoint-probe` today accepts only `step_prefix`, `short_name`, `--base-remote`, `--base-ref` at ```274:279:python/push.py```. Live callers pass `--forked-target` (bootstrap ```1439:1439```, SKILL.md ```533:533```, ```717:717```) or derived `--base-remote upstream` (step_7a ```297:299```). A naive 1:1 repoint would break forked `/implement` checkpoints and Step 1.r `ROUTE=` routing.

### Out-of-Scope Observations

- **Verb map:** All 16 retired helpers map to registered `python/cli.py` verbs; no missing CLI registration was found for the listed helpers.
- **Manifest rows:** The plan’s **UPDATED: scripts/** deletion block (lines 313–583) appears to cover every intended `.sh`, contract `.md`, and harness sibling; `gh-pr-checks.sh` correctly has no harness pair.
- **`pr create` redaction:** Older run-log concern about `create_main` lacking body redaction appears **already fixed**; `create_pr_parity` calls `pr_body.redact_pr_body` at ```288:299:python/pr.py```.
- **`ci-failed-jobs` / `ci-rerun-failed`:** No live non-test consumers found outside docstrings; safe to delete per plan, with docstring cleanup as planned.
- **Plan status:** Issue #4642 has no committed `larch:plan` block; the draft lives in the design session cache above and was halted before plan review.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-migration-fidelity.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-migration-fidelity.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-migration-fidelity.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-migration-fidelity.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-migration-fidelity.txt.launch-stderr)

❌ cursor agent: FAILED (exit code 1, output 0 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
✓ cursor agent: completed (exit code 0, output 7758 bytes)
  ```
