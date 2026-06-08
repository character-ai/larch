## Proposed Design Outline

### Goals
- Port the doc-facing leaf linters into the `python/` runtime, each registered as a `lint` verb in `cli.py`.
- Complete the orchestration cutover so `checks.py` runs the checks in Python instead of shelling out to `scripts/relevant-checks.sh`.
- Hard-cut every consumer (Makefile, pre-commit, CI, `.md`) and delete the retired bash + harnesses; keep `make lint` / `py-lint` / `py-test` green.

### Non-goals
- Touching the bash-staying linters (`lint-bash32`, `lint-bare-grep-probe`, `lint-awk-multibyte-regex`, `lint-renderer-substitution-safety`, `pre-commit-shellcheck`) or any hook.
- Changing lint rules or message semantics beyond what parity requires.
- Re-balancing the 20 CI harness shards after harness deletion (downstream; likely OOS).

### Approach sketch
- One stdlib-only module per linter under flat `python/`, each with `main(argv)` and a `("lint", "<verb>")` `_REGISTRY` entry (additive, merge-order-agnostic vs in-flight #3668).
- Relocate the already-Python `scripts/lint-skill-invocations.py` into `python/` + cli.py verb + colocated pytest.
- Port the `relevant-checks.sh` dispatcher into Python; rewire `checks.py` to call it directly; retire `run-relevant-checks-captured.sh`, `lint-fix-loop.sh`, `surface-lint-fix-stderr-tail.sh`.
- Parity-gate each retargeted `test-*.sh` once, then delete it and replace with `python/test_<module>.py`.
- Repoint Makefile `lint-*` targets, `.pre-commit-config.yaml` `entry:` lines, CI steps, and `.md` refs to `python3 cli.py lint <verb>`; append retired paths to `migrated-scripts.tsv`; run `lint-retired-scripts`.

### Surfaces in scope
- `python/` (new linter modules, `checks.py` rewire, `cli.py` registry, pytest); `scripts/lint-*.sh` + `relevant-checks.sh` + `run-relevant-checks-captured.sh` + `lint-fix-loop.sh` + `surface-lint-fix-stderr-tail.sh` (+ `.md` siblings + `test-*.sh`); `Makefile`; `.pre-commit-config.yaml`; `.github/workflows/ci.yaml`; `python/migrated-scripts.tsv`; doc refs.

### Open questions
- None. Scope forks resolved in Step 1c; behavior preservation is governed by the playbook parity-gate.
