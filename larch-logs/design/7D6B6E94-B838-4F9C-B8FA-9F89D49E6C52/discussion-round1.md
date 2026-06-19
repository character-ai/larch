## Decision 1: Scope is exactly the ~19 listed git/phantom bash helpers
- **Question**: What is in-scope vs out-of-scope for this slice?
- **Resolution**: Repoint every consumer of the ~19 listed `scripts/*.sh` git/phantom helpers to direct `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git …` / `git phantom-probe` calls, then delete the `.sh` + `.md` siblings + their `test-*.sh`/`.md` harnesses, in one atomic hard-cutover PR. Native `python/git.py` / `python/phantom.py` ports already exist (parity-verified) — this is a consumer cutover + delete, NOT a re-port.
- **Source**: user (baked-in clarifications, 2026-06-18 session)

## Decision 2: Parity-gap handling — fix gaps in this slice
- **Question**: If the parity audit finds a `cli.py` git/phantom verb that is not a complete replacement (flags, exit codes, output), what happens?
- **Resolution**: Fix it in this slice — extend `python/git.py` / `python/phantom.py` so every listed script still deletes atomically in one PR. No deferral.
- **Source**: user (Resolved decision 1)

## Decision 3: Test-coverage bar — no silent coverage loss
- **Question**: What is the bar before deleting each bash harness?
- **Resolution**: Before deleting each bash harness, confirm `python/test_git.py` / `python/test_phantom.py` cover its behavior. Add pytest cases for any gap. No silent coverage loss.
- **Source**: user (Resolved decision 2)

## Decision 4: Non-goals (hard constraints — must NOT do)
- **Question**: What must this change explicitly NOT do?
- **Resolution**: (a) No re-porting logic — native modules exist and are parity-verified. (b) Do NOT migrate non-listed scripts (`create-pr.sh`, `merge-pr.sh`, `lib-phantom-probe.sh`) beyond repointing their references. (c) No shim/forwarding `.sh` stubs and no new abstractions.
- **Source**: user (Non-goals)

## Decision 5: Definition of done
- **Question**: When is this slice complete?
- **Resolution**: All consumers on `cli.py`; bash + `.md` siblings + harnesses deleted; `python/migrated-scripts.tsv` updated with every deleted path; `make lint-retired-scripts` clean and `make lint` clean; no test-coverage regression.
- **Source**: user (Definition of done)

## Decision 6: Two open questions deferred to Step 2b codebase audit
- **Question**: (1) Does `lib-phantom-probe.sh` (not in retire list) stay as a repointed consumer or is it dead once `phantom-probe-with-warn.sh` goes? (2) Do `python/push.py` / `python/rebase.py` own the push/rebase verbs, or does `git.py`?
- **Resolution**: Both explicitly deferred to Step 2b audit — resolved by direct codebase inspection during plan drafting, not by user question.
- **Source**: user (Open questions)
