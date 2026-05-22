### FINDING_1: correctness: .github/workflows/ci.yaml:187-195
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Site-packages cache path uses ~/.local/... while setup-python pip installs usually land under the toolcache prefix. Cache hit skips pip install but PyYAML is not on the interpreter path used by harnesses; import yaml fails on subsequent runs. Also possible mismatch if python-version output includes patch. Point cache path at the real site-packages after pip (or use pip install --user consistently); validate with sys.prefix / site.getsitepackages() on the runner.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: .github/workflows/ci.yaml:193-195
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Step title still says lint dependencies though installs harness requirements only. Log triage friction. Rename the step to reflect harness/Python deps.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: .github/workflows/ci.yaml:187-195
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Site-packages cache path uses ~/.local and setup-python python-version interpolation while pip install is not user-scoped; toolcache install path and user-site dir naming likely differ. Cache hit can skip pip while PyYAML is not on sys.path; shards fail on import or behave inconsistently. Point cache at real site-packages (discovered via site module), align user vs global install, or remove redundant cache and use setup-python pip cache only.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: .github/workflows/ci.yaml:187-195
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Site-packages cache path plus skip-pip-on-hit may not match where pip installs PyYAML on setup-python runners. On cache hit the workflow skips pip install; if wheels live under the toolcache prefix while the cache only restores ~/.local/... (or a python-version-shaped path that does not match user-site layout), python3 cannot import yaml and shard jobs fail at harnesses that require PyYAML. Align cache path with the real prefix (verify in CI logs), or use pip install --user with a path from python -m site --user-site, or avoid skipping pip; add import yaml smoke if retaining skip-on-hit.
- **Suggested revision**: Address the concern above.


### FINDING_14: code-quality: .github/workflows/ci.yaml:193-195
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Step name says Install lint dependencies but installs harness requirements. Harder to scan Actions logs and conflates two CI contracts. Rename to reflect harness Python deps.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: .github/workflows/ci.yaml:187-195
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Site-packages cache path uses ~/.local/... while pip install has no --user/PIP_USER, so it likely does not match setup-python’s install prefix on hosted runners. On cache hit pip install is skipped but PyYAML may never be installed where the job’s python looks, breaking yaml imports; or the cache never captures real installs so the speedup does not materialize. Cache the real site-packages path (e.g. via python -m site / getsitepackages()) or use pip install --user and cache the user-site path returned by python -m site --user-site; align with actual install mode.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: .github/workflows/ci.yaml:191-192
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Cache path interpolates steps.setup-python.outputs.python-version into a directory name python${version}; if output is a full patch semver the path may not match lib/pythonX.Y layout. Wrong or non-existent cache directory → misses or restores the wrong tree relative to pip. Derive directory from python -m site (or normalize to X.Y only per pip’s layout).
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: Makefile:115-118
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Makefile comment describes shard 5–20 packing as by count with LPT tie-break, not LPT greedy on scraped per-harness CI times as the plan states. Future reshards may follow the wrong algorithm; plan-to-code traceability for requirement (3) is broken. Update comment to the true procedure or rerun LPT-by-timing and document that.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: .github/workflows/ci.yaml:193-194
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step still titled Install lint dependencies though it only installs harness requirements. Maintainers misread logs when triaging CI. Rename step to reflect test-harness Python deps only.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: .github/workflows/ci.yaml:193-194
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Step name says Install lint dependencies for harness-only requirements. Mild operational confusion in CI logs. Rename step to reflect harness Python deps only.
- **Suggested revision**: Address the concern above.


### FINDING_22: **correctness** `.github/workflows/ci.yaml:187-195` — The new `actions/cache` step archives `~/.local/lib/python${{ steps.setup-python.outputs.python-version }}/site-packages`, but the install step runs plain `pip install -r …` with no `PIP_USER=1`, `--user`, or other guarantee that wheels land under `~/.local`. With `actions/setup-python`, the interpreter normally installs into the toolcache prefix (environment `site-packages`), not the user-local tree, so the cached tree is often empty or unrelated while `pip` still mutates the real prefix on misses. A later cache “hit” can skip `pip install` and leave `yaml` (or other deps) missing for harness steps that run `python3 -c 'import yaml'`, or conversely you may get perpetual misses and no speedup. Separately, `steps.setup-python.outputs.python-version` is typically a full `3.12.x` string, whereas Linux `site.getusersitepackages()` uses a `python3.12`-style directory (major.minor), so even a `--user` layout would not reliably match `python${{ … }}` if that expands to `python3.12.10`. **Suggested fix:** Either install and cache the same path: e.g. run `pip install --user -r …` and set `path` to the result of `python -c "import site; print(site.getusersitepackages())"`, or drop the user-local indirection and cache `python -c "import site; print(site.getsitepackages()[0])"` (or `pip cache dir` / explicit `$(python -m site --site-packages)`-style resolution) so the cached tree is exactly where `pip` writes; keep the cache key aligned with `hashFiles('.github/workflows/requirements-test-harnesses.txt')` and the resolved Python version.
- **Reviewer**: dyn-ci-cache-correctness-output.txt
- **Concern**: - **correctness** `.github/workflows/ci.yaml:187-195` — The new `actions/cache` step archives `~/.local/lib/python${{ steps.setup-python.outputs.python-version }}/site-packages`, but the install step runs plain `pip install -r …` with no `PIP_USER=1`, `--user`, or other guarantee that wheels land under `~/.local`. With `actions/setup-python`, the interpreter normally installs into the toolcache prefix (environment `site-packages`), not the user-local tree, so the cached tree is often empty or unrelated while `pip` still mutates the real prefix on misses. A later cache “hit” can skip `pip install` and leave `yaml` (or other deps) missing for harness steps that run `python3 -c 'import yaml'`, or conversely you may get perpetual misses and no speedup. Separately, `steps.setup-python.outputs.python-version` is typically a full `3.12.x` string, whereas Linux `site.getusersitepackages()` uses a `python3.12`-style directory (major.minor), so even a `--user` layout would not reliably match `python${{ … }}` if that expands to `python3.12.10`. **Suggested fix:** Either install and cache the same path: e.g. run `pip install --user -r …` and set `path` to the result of `python -c "import site; print(site.getusersitepackages())"`, or drop the user-local indirection and cache `python -c "import site; print(site.getsitepackages()[0])"` (or `pip cache dir` / explicit `$(python -m site --site-packages)`-style resolution) so the cached tree is exactly where `pip` writes; keep the cache key aligned with `hashFiles('.github/workflows/requirements-test-harnesses.txt')` and the resolved Python version.
- **Suggested revision**: Address the concern above.


### FINDING_25: **risk-integration** `.github/workflows/ci.yaml:181-195` — The job still enables `actions/setup-python`’s built-in `cache: pip` (wheel/HTTP cache under the pip data directory, keyed off `requirements-test-harnesses.txt`) and adds a second `actions/cache` pass over `~/.local/lib/python${{ steps.setup-python.outputs.python-version }}/site-packages`, then skips `pip install` when that second cache reports a hit. Those layers are not inherently inconsistent if both keys rotate together, but they are only safe if installed artifacts actually land under that `~/.local/.../site-packages` tree. With a normal `pip install` (no `PIP_USER=1` / `--user`), `setup-python`’s interpreter on hosted runners typically installs into the tool-installed prefix (for example under the hosted toolcache), not the PEP 370 user-site tree under `$HOME/.local`, and the `python-version` step output can also disagree with the `pythonX.Y` segment used for user-site paths. In the mismatched case you either pay for two restores with little benefit (wheel cache + wrong-path site-packages cache) or, worse, a hit on a tree that does not contain the `pip`-installed `pyyaml` layout combined with skipping `pip install` breaks imports or poisons the saved archive—i.e. the interaction between “skip install on site-packages hit” and “pip cache + install location” is the real integration hazard, not a silent version skew from divergent keys (both incorporate the same requirements hash). **Suggested fix:** Drop the site-packages cache and rely on `cache: pip` alone, or make the cached directory exactly match the environment `pip` writes to (for example derive `site-packages` from `python -c 'import site; print(site.getsitepackages()[0])'` after `setup-python`, or set `PIP_USER=1` and cache `python -m site --user-site`), and only then consider removing redundant `cache: pip` on this job if measurements show the extra restore is not worth it.
- **Reviewer**: dyn-ci-redundant-caching-output.txt
- **Concern**: - **risk-integration** `.github/workflows/ci.yaml:181-195` — The job still enables `actions/setup-python`’s built-in `cache: pip` (wheel/HTTP cache under the pip data directory, keyed off `requirements-test-harnesses.txt`) and adds a second `actions/cache` pass over `~/.local/lib/python${{ steps.setup-python.outputs.python-version }}/site-packages`, then skips `pip install` when that second cache reports a hit. Those layers are not inherently inconsistent if both keys rotate together, but they are only safe if installed artifacts actually land under that `~/.local/.../site-packages` tree. With a normal `pip install` (no `PIP_USER=1` / `--user`), `setup-python`’s interpreter on hosted runners typically installs into the tool-installed prefix (for example under the hosted toolcache), not the PEP 370 user-site tree under `$HOME/.local`, and the `python-version` step output can also disagree with the `pythonX.Y` segment used for user-site paths. In the mismatched case you either pay for two restores with little benefit (wheel cache + wrong-path site-packages cache) or, worse, a hit on a tree that does not contain the `pip`-installed `pyyaml` layout combined with skipping `pip install` breaks imports or poisons the saved archive—i.e. the interaction between “skip install on site-packages hit” and “pip cache + install location” is the real integration hazard, not a silent version skew from divergent keys (both incorporate the same requirements hash). **Suggested fix:** Drop the site-packages cache and rely on `cache: pip` alone, or make the cached directory exactly match the environment `pip` writes to (for example derive `site-packages` from `python -c 'import site; print(site.getsitepackages()[0])'` after `setup-python`, or set `PIP_USER=1` and cache `python -m site --user-site`), and only then consider removing redundant `cache: pip` on this job if measurements show the extra restore is not worth it.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: Makefile:103-118
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Comment describes count-based packing for shards 5-20 while the plan promised LPT from CI timings for all shards. Future resharding may follow the wrong procedure or expect timing-balanced bins 5-20. Either apply full LPT to all harnesses or document the hybrid (timing for four slow harnesses, count bins for the rest).
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: .github/workflows/ci.yaml:187-195
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Site-packages cache path (~/.local/.../python${setup-python.outputs.python-version}) does not match default pip install location for setup-python; conditional pip skip on cache hit. Restored cache can be empty or unrelated while PyYAML lives under the toolcache prefix; next job skips pip and harnesses that require PyYAML fail (e.g. import yaml checks). Cache the actual site-packages directory used by that interpreter (from site.getsitepackages / pip show -f), or use pip --user and cache user-site from python -m site, or remove skip and rely on setup-python pip cache only; avoid string-building python version into ~/.local path without verifying site module layout.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: .github/workflows/ci.yaml:193-195
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Step label still says Install lint dependencies though only harness requirements are installed. Misleading when triaging logs / comparing to lint job. Rename step to reflect test-harnesses-only Python deps.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: .github/workflows/ci.yaml:187-195
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Site-packages cache path likely does not match where pip installs packages after setup-python on hosted runners; python-version output may not match directory layout. On a warm cache, pip install is skipped but PyYAML is not on sys.path → ModuleNotFoundError in harnesses across shards. Cache the directory returned by the active interpreter (e.g. site.getsitepackages()[0] / pythonLocation-relative path) or use explicit pip --user and cache python -m site --user-site; optionally assert import yaml when skipping install.
- **Suggested revision**: Address the concern above.


