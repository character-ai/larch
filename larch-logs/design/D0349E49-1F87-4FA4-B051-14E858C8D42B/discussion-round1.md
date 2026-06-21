## Decision 1: Scope is exactly the two named sourced libs (no broader sweep)
- **Question**: Does "eliminate sourced Bash libraries" mean a repo-wide sweep, or only the two named libs?
- **Resolution**: Only the two named libs. A scan confirms `lib-plan-optional-trailers.sh` and `lib-implement-clone-tag.sh` are the ONLY remaining sourced bash libraries (`lib-*.sh` / `*.inc.bash`) in the runtime tree, so handling these two fully satisfies the goal. No broader sweep.
- **Source**: codebase

## Decision 2: Design side is retirement-only (Python port already exists)
- **Question**: Does the optional-trailers Python port still need to be written?
- **Resolution**: No. `python/plan_quality.py` already owns the optional-trailers logic (`optional_trailers_main`, `validate_optional_trailer_keys_preserved`, `validate_optional_trailers_preserved`) and `cli.py plan optional-trailers` is registered. Runtime consumers (`plan check-size`, `plan_review.py`, `plan-review gate-b-dedup`) already use Python. The issue's "repoint 4 design sourcing sites" is STALE — `lib-plan-optional-trailers.sh` + `.awk` are dead at runtime, sourced only by the bash trailer harnesses. Design-side work is therefore RETIREMENT-ONLY: delete the dead lib + awk, port/retire the bash trailer harnesses, prune `residual-bash-paths.txt`, append `migrated-scripts.tsv`.
- **Source**: codebase

## Decision 3: clone-tag derivation lands in a new cli.py verb
- **Question**: Fold `lib-implement-clone-tag.sh` into its 2 consumers (inline) or into a `cli.py` verb?
- **Resolution**: New `cli.py` verb (user-selected). The verb emits `CLONE_TAG_FULL=` / `EXPECTED_TMPDIR_BASENAME_PREFIX=`; both Step 8 wrappers (`step-8-seed-initial.sh`, `step-8-ship.sh`) consume it (eval/source the KV). DRY across the 2 consumers, python-first, directly matches AGENTS.md "no shared bash libraries."
- **Source**: user

## Decision 4: Trailer harness assertions ported to pytest; bash harnesses deleted
- **Question**: Keep the bash trailer harnesses (repointed) or port assertions to pytest?
- **Resolution**: Port any unique assertions into `python/test_plan_quality.py`, then delete the bash trailer harnesses. Matches the migration recipe (write colocated pytest → run retargeted harness as a parity gate → delete) and the acceptance criterion "trailer harness assertions ported." `test_plan_quality.py` already has substantial trailer coverage; verify parity and fill any gaps before deletion.
- **Source**: codebase + acceptance criterion

## Hard constraints (must not break)
- **clone-tag byte-parity**: the cli.py verb must produce `CLONE_TAG_FULL` / `EXPECTED_TMPDIR_BASENAME_PREFIX` byte-identical to today's bash derivation (`CLONE_TAG` passthrough; else `basename "$PWD"` → `tr -c 'A-Za-z0-9_-' '_'` → 32-char truncation → fallback `_`). Used for `/implement` Step 8 tmpdir-prefix validation.
- **optional-trailer behavior parity**: plan-size gating, snapshot/validate/dedup-preserve behavior unchanged.
- **No shims**: consumers call `cli.py` directly; no forwarding `.sh` stubs (docs/python-migration.md).
- **Manifest + lint**: append deleted paths to `python/migrated-scripts.tsv` with `#4971`; prune the deleted harness lines from `scripts/residual-bash-paths.txt`; `make lint-retired-scripts` must be clean.
- **Siblings**: delete `.md` siblings alongside each deleted `.sh`/`.awk` (script-md-siblings rule).
