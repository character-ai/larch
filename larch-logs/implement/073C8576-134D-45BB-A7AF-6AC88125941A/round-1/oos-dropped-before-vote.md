### OOS_1: [OUT_OF_SCOPE] Refactor preserves edge-case invariants (path guards, subprocess, step 6, API, tests)
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Path/symlink guards remain on issue-body files, result-env reads/writes (`O_NOFOLLOW` / `O_EXCL`), `run-params.json`, and `--failure-detail-log` containment under `design_tmpdir` (`design_terminal.py`). Subprocess usage is unchanged (argv lists, no new `shell=True`); baseline entries were relocated, not rewritten. Step 6 in-flight detection (`step-5c-terminal` vs `.bg-wait-active`) is unchanged in `design_step6.py`. Public surface stays stable via the facade; `clarify.py` and `plan_review.py` imports from `design_lifecycle` still resolve. Tests retarget monkeypatches to defining modules (`design_step0`, `design_step5b`, `design_step6`, etc.) while still exercising `design_lifecycle.*` entrypoints, matching the new import graph; no diff hunk changes control flow, validation, or error handling versus `origin/main` beyond file moves and import rewiring.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Step 6 couples to Step 2b for `_read_simple_env`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/design/design_step2b.py:111` / `python/larch/design/design_step6.py:24-25` — Step 6 imports `_read_simple_env` from Step 2b for sidecar parsing. That couples teardown to the drafter module for a generic KV helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: move `_read_simple_env` to `design_core.py` or `design_session.py` on a follow-up hygiene pass.

### OOS_3: [OUT_OF_SCOPE] Largest post-split modules remain near prior god-module scale
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/design/design_step2b.py` (941 LOC), `python/larch/design/design_terminal.py` (965 LOC) — largest post-split modules are still near prior god-module scale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: treat these as the next split candidates in the umbrella series.

### OOS_4: [OUT_OF_SCOPE] Complexity baseline and ruff ignores relocated rather than reduced
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `python/complexity-baseline.json`, `python/ruff.toml` — baseline rows and per-file complexity ignores were relocated/duplicated to the new modules rather than reduced per plan wording. Plan acceptance says to remove obsolete complexity-baseline rows; the diff relocates all 124 entries to new file paths rather than deleting any. That is consistent with unchanged per-function complexity metrics and keeping `make py-lint` green, but it does not reduce baseline debt the plan wording implies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: drop shim-only `design_lifecycle.py` ignores once the capstone re-tighten lands (13/14).
  - From cursor-specialist-testing: Treat relocation as sufficient for this slice, or schedule a follow-up once complexity actually drops below thresholds.

### OOS_5: [OUT_OF_SCOPE] `_DIRECT_TARGET_RULES` still keys on obsolete flat `design_lifecycle.py` path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `python/larch/implement/checks.py:542-557` — `_DIRECT_TARGET_RULES` still keys on the obsolete flat path `python/design_lifecycle.py`, which no longer exists (only `python/larch/design/design_lifecycle.py` remains). Edits to any of the 11 new split modules therefore do not trigger focused design harness targets (`test-design-step0-init`, `test-design-step2b-drafter`, `test-design-driver`, etc.) under relevant-checks. The split widens that pre-existing gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add `_DIRECT_TARGET_RULES` rows for `python/larch/design/design_lifecycle.py` and the split siblings (or a glob), mirroring the existing harness list.

### OOS_6: [OUT_OF_SCOPE] `test-design-structure.sh` relies on manually maintained file list
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh:19-38` — Structural grep coverage now depends on a manually maintained `cat` list of 12 files. A future submodule added without updating that list would pass `test-design-structure` while missing string anchors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Derive the list from a glob (`python/larch/design/design_{core,session,terminal,router,step*}.py`) or add a small assertion that every non-shim `design_*.py` under `larch/design/` appears in the concat set.

