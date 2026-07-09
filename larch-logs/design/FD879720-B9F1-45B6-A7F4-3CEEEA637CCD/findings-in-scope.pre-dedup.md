### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py
- **Concern**: _read_active_run_id must normalize pointer text before validate_run_id. Scenario: activate_run writes a newline-terminated run ID to current, but validate_run_id rejects whitespace and only allows [A-Za-z0-9._-]+. Reading the pointer verbatim makes validation fail on the normal activation format, so cleanup treats no run as active and can delete the active run directory despite a valid current pointer.
- **Proposed resolution**: In _read_active_run_id, read only the first line, strip trailing newline/whitespace, then call validate_run_id. Document that this matches activate_run output. Seed the active-run cleanup test via activate_run (or an equivalent newline-terminated pointer) so the reader contract is exercised.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: security
- **Location**: plan.txt:36-51
- **Concern**: The new write helpers still resolve the target path again at temp/open time after the final ancestry check.. Scenario: A clone-dir swap between the check and the write can redirect `current` or `breadcrumbs.log` outside `progress_root`.
- **Proposed resolution**: Bind the temp/open step to a verified directory FD or another helper that cannot re-resolve the parent path after the last check.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:65-79
- **Concern**: Cleanup never says how it will delete a non-empty run dir.. Scenario: Each aged run dir will still contain `breadcrumbs.log`, so a plain `rmdir` path will fail and stale runs will survive cleanup.
- **Proposed resolution**: Spell out the removal step, either recursive delete or unlink the log before `rmdir`, and keep the symlink re-check right before deletion.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py
- **Concern**: `_read_active_run_id` must strip trailing newline/whitespace before `validate_run_id`. Scenario: `activate_run` writes a newline-terminated pointer, but the plan never says to strip on read. A pointer like `design-20260708.1\n` fails validation, `_read_active_run_id` returns `None`, and cleanup drops the still-active run directory even though `current` exists.
- **Proposed resolution**: In `_read_active_run_id`, read the pointer best-effort, strip trailing `\n`/`\r`/whitespace, then call `validate_run_id`. Add a test that uses `activate_run` output and asserts cleanup keeps the named run dir when only its directory mtime is stale.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/report/progress_file.py
- **Concern**: Cleanup must skip symlinked clone directories at the outer loop. Scenario: The plan requires symlink skips for run-id children and says cleanup must not delete outside `progress_root`, but it never guards the clone-dir entries themselves. A symlinked `progress/<hash>` entry makes `is_dir()` true; pruning its children can follow the link and remove trees outside the cache.
- **Proposed resolution**: Mirror `cleanup_skill._should_remove_by_age` / `_remove_entry`: skip any clone-dir candidate where `entry.is_symlink()` or `not entry.is_dir()`. Re-check `not run_dir.is_symlink()` immediately before removal. Add a test with a symlinked clone dir and assert nothing outside `progress_root` is deleted.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py
- **Concern**: Cleanup should remove run directories with `shutil.rmtree`. Scenario: The plan says "remove the directory" for aged run-id subdirs but does not name a recursive delete. A non-empty run dir (`breadcrumbs.log` inside) will not be removed by `Path.rmdir`/`unlink`, so retention silently stops working while the flat-log pass still succeeds.
- **Proposed resolution**: Specify `shutil.rmtree` (after the final symlink re-check), matching `cleanup_skill._remove_entry`, inside the best-effort `except OSError: continue` loop. Add a test that an aged run dir with a log file is actually removed.



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: plan.txt:36-43
- **Concern**: The final ancestry check does not pin the parent of `.current.`. Scenario: A clone-dir swap after that check can move temp-file creation under a different parent, so the pointer write lands outside the validated tree.
- **Proposed resolution**: Create the temp file through an already-open clone-dir handle, or make the atomic writer accept a pinned directory FD instead of a bare path.



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: plan.txt:45-51
- **Concern**: The explicit-run append path still trusts path checks before the leaf open. Scenario: A swap after `mkdir` can redirect the append through a different ancestor; `O_NOFOLLOW` only blocks a symlinked final component, not the parent chain.
- **Proposed resolution**: Pin the run directory with an open handle and open `breadcrumbs.log` relative to it, or otherwise close the TOCTOU window around the write.



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: plan.txt:65-79
- **Concern**: Cleanup never rejects symlinked clone dirs before descending. Scenario: A planted symlink at a clone-hash directory can make the sweep read `current` and delete run dirs outside `progress_root`.
- **Proposed resolution**: Skip symlinked clone dirs up front, and re-check the clone root immediately before enumerating or removing child run dirs.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py
- **Concern**: `_read_active_run_id` must strip the pointer newline before `validate_run_id`. Scenario: `activate_run` writes `f"{run_id}\n"` to `current`, but `validate_run_id` rejects whitespace. A literal read fails validation, returns `None`, and cleanup drops the active-run exemption even while that run is still in use.
- **Proposed resolution**: Add an explicit contract step: read `current`, take the first line or strip trailing newline/whitespace, then call `validate_run_id`. Add a cleanup test that activates a run, ages the run-directory mtime, and confirms the named run dir survives retention.



### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/report/progress_file.py:activate_run
- **Concern**: Accepted parent-swap fix is still path-based. Scenario: The plan rechecks `current_run_path` immediately before `atomic_write`, but `atomic_write` resolves `dest.parent` by name. If the clone dir is swapped to a symlink after that check and before temp creation or replace, `progress activate` can write `current` in the symlink target, so the accepted race remains.
- **Proposed resolution**: Make activation fd-anchored to the verified clone dir. Open the clone dir with `O_DIRECTORY|O_NOFOLLOW` after mkdir and recheck, create the temp file and replace `current` using dir-fd relative operations or an equivalent helper, and add a race test that swaps the clone dir between the final check and write.



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/report/progress_file.py
- **Concern**: Cleanup clone-dir pass must skip symlinked clone-directory roots. Scenario: The per-clone-dir loop guards symlinked run-id children and re-checks before rmtree, but it never says to skip a symlinked clone-directory root. Failure modes require cleanup not to follow symlinks; iterating a symlinked clone root can reap run trees outside the intended progress cache.
- **Proposed resolution**: Mirror the flat `*.log` pass: when building or walking clone-dir candidates, skip any entry where `entry.is_symlink()` or `not entry.is_dir()`. Only process regular clone directories under `progress_dir`.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py
- **Concern**: `_read_active_run_id` must strip pointer content before `validate_run_id`. Scenario: `activate_run` writes a newline-terminated run ID to `current`. `validate_run_id` rejects whitespace, so reading the raw file and validating it always fails. Cleanup then treats no run as active and can delete the directory named by `current` even while that run is still live.
- **Proposed resolution**: Read the first line (or full small file), strip trailing newline/whitespace, then call `validate_run_id`. Return `None` on empty, unreadable, symlinked, or invalid content. ### 1. [security] `python/larch/report/progress_file.py` — Cleanup must skip symlinked clone-directory roots The plan’s failure modes say cleanup must not follow symlinks. The flat-log pass already skips `entry.is_symlink()`. The clone-dir pass only skips symlinked run-id children and re-checks before removal; it never says to skip a symlinked clone-directory root. If a clone hash path is swapped to a symlink, iterating it can delete run trees outside the progress cache. **Suggested revision:** When enumerating clone-dir candidates (from `*.log` stems and from `progress_dir.iterdir()`), skip symlinked or non-directory roots, same as the flat-log pass. ### 2. [correctness] `python/larch/report/progress_file.py` — `_read_active_run_id` must strip before validation `activate_run` writes `f"{run_id}\n"` to `current`. `validate_run_id` rejects whitespace. Without stripping the pointer payload first, `_read_active_run_id` always returns `None`. Cleanup then never exempts the active run directory, which breaks the plan’s “preserve active run dir named by `current`” rule and the mandated cleanup test. **Suggested revision:** Specify that `_read_active_run_id` reads the first line, strips trailing newline/whitespace, then validates with `validate_run_id`. --- **Ledger check:** Prior accepted items (breadcrumbs.log mtime aging, active-run dir exemption, `current` reservation, symlink-ancestor checks on explicit append, `activate_run` final ancestry check before `atomic_write`) are present in the current plan. Rejected/OOS items (`..` substring dedup, shared `validate_run_id_slug`, max-length alignment) were not re-raised. **Scope:** The three-file, dormant-only boundary matches the partition piece and acceptance criteria. No material scope creep found.



### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/report/progress_file.py:new activate_run
- **Concern**: The prior parent-swap fix is incomplete because the plan still relies on a final path ancestry check before calling path-based atomic_write.. Scenario: A clone dir can be swapped to a symlink after the final check but before atomic_write creates the temp file and replaces current, redirecting the pointer write outside the verified progress tree.
- **Proposed resolution**: Revise activate_run to anchor the current write to a verified clone-directory fd, or otherwise make temp creation and replace fd-relative to that directory. Add a swap test for the gap between the final check and write.



