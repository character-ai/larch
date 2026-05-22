### FINDING_1: code-quality: Makefile:30-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Shard comment documents equal-count fill for shards 5-20 not per-harness LPT from CI timings Feature text asked for LPT greedy repartition from scraped timings to minimize max shard time across all 20 shards; hybrid packing can leave multiple mid-slow harnesses on one shard and re-inflate the wall-time ceiling relative to a true LPT remainder Either rerun full LPT on all harnesses or update the requirement PR description to the hybrid algorithm actually used
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: larch-logs/implement/BB37BF44-F430-44DF-A543-28AF3D40E517/plan-goals-test.md:36
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Committed plan-goals CI snippet shows ~/.local site-packages cache path unlike merged ci.yaml Someone copying the flushed plan into a new workflow could reintroduce a brittle hardcoded path that does not match setup-python install layout Align the snippet with ci.yaml or annotate it as historical
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: .github/workflows/requirements-lint.txt:1-2
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header comment omits requirements-test-harnesses.txt as a PyYAML pin peer Maintainer might bump PyYAML in pre-commit and requirements-lint but forget the harness-only requirements file File not touched on this branch; extend comment in a follow-up to list all three pin locations
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: Makefile:119-128
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Shard rebalance does not implement full LPT across all harnesses as required; Makefile admits equal-count packing for shards 5–20. Two remaining slow harnesses can share a shard while another stays light, so max shard wall time stays above an LPT optimum and the stated minimize-max-runtime goal is only partially met. Either apply full LPT from scraped timings for all shards or update the feature/plan text to match the hybrid heuristic.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: .github/workflows/ci.yaml:187-198
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Site-packages cache path uses site.getsitepackages()[0] while skipping pip on cache hit, assuming pip always installs there. If pip ever targets a different directory than getsitepackages()[0], a cache hit could skip install and leave PyYAML missing, breaking harnesses that import yaml. Align cache path with pip’s actual install target and/or verify import after restore.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: .github/workflows/ci.yaml:181-198
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Dual pip caching: setup-python cache: pip plus separate site-packages actions/cache. Minor complexity; no definite runtime failure. Consolidate caching strategy after benchmarking if redundant.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture: larch-logs/implement/BB37BF44-F430-44DF-A543-28AF3D40E517/manifest.json:1-21
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Scrubbed placeholders in implement manifest. Intentional per docs; not introduced as a CI/cache defect. No change required for this feature review.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: Makefile:20-38
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Shard rebalance docs admit shards 5–20 are count-packed with LPT tie-break only, not full per-harness LPT from CI timings across all 20 shards as required by the feature/plan text. Max shard wall time may remain higher than the stated LPT-minimax target; reviewers may believe all shards were timing-driven when only 1–4 were. Either rerun true per-harness LPT across all shards using scraped timings and align comments, or narrow the feature/plan to the hybrid strategy actually used.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: .github/workflows/ci.yaml:181-198
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Overlapping Python dependency caching: setup-python pip cache plus separate site-packages cache and conditional pip install. Future edits may mis-edit the wrong cache layer or remove the wrong `if:` guard when dependencies change. Document which cache enables skipping `pip install`, or remove redundant `cache: pip` if redundant in practice.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: .github/workflows/ci.yaml:187-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Site-packages cache path is site.getsitepackages()[0] while pip may install elsewhere on some layouts. cache-hit skips pip install but PyYAML missing at import time causes late shard failures. Add unconditional import check after cache or align cache path with pip target metadata.
- **Suggested revision**: Address the concern above.

### FINDING_11: architecture: Makefile:30-34
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Shards 5-20 used equal-count greedy packing not full per-harness LPT. A mid-pack harness grows slower and again dominates a shard wall time despite rebalance narrative. Run full LPT on remainder or document the weaker optimization explicitly in tracking docs.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: .github/workflows/ci.yaml:187-189
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Resolve step uses python while harnesses use python3. If PATH ever splits python vs python3 the cached tree may not match test interpreter. Use python3 for path resolution and pip invocation consistently.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: .github/workflows/ci.yaml:213-221
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Ripgrep binary fetched via curl without checksum in workflow. Tamper or partial download risk unchanged from prior workflow. Out of scope for this PR; consider checksum verify in a separate change.
- **Suggested revision**: Address the concern above.

### FINDING_14: architecture: Makefile:30-35
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Shard rebalance for shards 5-20 uses equal-count packing with LPT tie-break only among equal-size bins, not full timing LPT as required by the plan. Slow harnesses among the long tail can cluster on one shard, raising wall time toward the job timeout while other shards stay comparatively idle; the plan’s goal of minimizing max shard runtime via LPT is only partially met. Implement per-harness timing LPT for shards 5-20 as specified, or revise the written plan/feature to the hybrid strategy and accept the longer-pole risk explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: .github/workflows/ci.yaml:187-198
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Site-packages cache path uses site.getsitepackages()[0] instead of the plan’s ~/.local/... path. If pip’s install prefix diverged from getsitepackages()[0] on a future image, cache-hit could skip pip while PyYAML is missing from the import path, failing all matrix shards until the cache key invalidates. Document equivalence to pip’s target, pin behavior to setup-python’s install layout, or add a lightweight import check after restore.
- **Suggested revision**: Address the concern above.

### FINDING_16: **risk-integration** `.github/workflows/ci.yaml:181-198` — The job now restores `actions/setup-python`’s pip download cache (`cache: pip` with `cache-dependency-path: .github/workflows/requirements-test-harnesses.txt`) and, separately, may restore the entire `site.getsitepackages()[0]` tree via `actions/cache` (`key` uses `runner.os`, `steps.setup-python.outputs.python-version`, and `hashFiles('.github/workflows/requirements-test-harnesses.txt')`). Those keys stay aligned on the requirements hash, so there is no realistic “pip cache hit + site-packages miss” split that skips `pip install` while leaving wheels-only state: `pip install` is skipped only on an exact site-packages cache hit, which restores the installed artifacts the job relies on. The main residual integration risk is cache **key axes vs ABI**: `runner.os` remains `Linux` across `ubuntu-latest` image retargets, so a site-packages tarball that includes binary wheels (PyYAML’s compiled extension) could theoretically be restored after a future hosted-image libc/OpenSSL baseline shift while still matching the key; this is not introduced by having two pip-related caches (they do not compose into a partial-install state), but it is amplified versus “pip download cache only” because you are persisting importable binaries, not just tarballs in `/.cache/pip`. **Suggested fix:** Tie the site-packages cache key to a stronger runner baseline signal you control (for example encode the literal `runs-on` label if you pin `ubuntu-24.04`, or include an explicit repo-maintained bump token in the key on known runner migrations), or drop site-packages caching if the marginal savings aren’t worth ABI coupling to `ubuntu-latest` movement.
- **Reviewer**: dyn-ci-cache-interaction-output.txt
- **Concern**: - **risk-integration** `.github/workflows/ci.yaml:181-198` — The job now restores `actions/setup-python`’s pip download cache (`cache: pip` with `cache-dependency-path: .github/workflows/requirements-test-harnesses.txt`) and, separately, may restore the entire `site.getsitepackages()[0]` tree via `actions/cache` (`key` uses `runner.os`, `steps.setup-python.outputs.python-version`, and `hashFiles('.github/workflows/requirements-test-harnesses.txt')`). Those keys stay aligned on the requirements hash, so there is no realistic “pip cache hit + site-packages miss” split that skips `pip install` while leaving wheels-only state: `pip install` is skipped only on an exact site-packages cache hit, which restores the installed artifacts the job relies on. The main residual integration risk is cache **key axes vs ABI**: `runner.os` remains `Linux` across `ubuntu-latest` image retargets, so a site-packages tarball that includes binary wheels (PyYAML’s compiled extension) could theoretically be restored after a future hosted-image libc/OpenSSL baseline shift while still matching the key; this is not introduced by having two pip-related caches (they do not compose into a partial-install state), but it is amplified versus “pip download cache only” because you are persisting importable binaries, not just tarballs in `/.cache/pip`. **Suggested fix:** Tie the site-packages cache key to a stronger runner baseline signal you control (for example encode the literal `runs-on` label if you pin `ubuntu-24.04`, or include an explicit repo-maintained bump token in the key on known runner migrations), or drop site-packages caching if the marginal savings aren’t worth ABI coupling to `ubuntu-latest` movement.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] **Branch diff vs stated goal (not cache interaction):** `Makefile:121-126` (as merged on the branch) documents that shards 5–20 were not repacked by full per-harness timing LPT, which diverges from the high-level “re-partition all 20 shards from timings” framing in the surrounding plan text; worth reconciling in docs or rerunning the packer if wall-time parity was the intent.
- **Reviewer**: dyn-ci-cache-interaction-output.txt
- **Concern**: - **Branch diff vs stated goal (not cache interaction):** `Makefile:121-126` (as merged on the branch) documents that shards 5–20 were not repacked by full per-harness timing LPT, which diverges from the high-level “re-partition all 20 shards from timings” framing in the surrounding plan text; worth reconciling in docs or rerunning the packer if wall-time parity was the intent.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] **Unrelated surface area in the same branch diff:** new files under `larch-logs/implement/BB37BF44-F430-44DF-A543-28AF3D40E517/` (`manifest.json`, `parent-issue.md`, `plan-goals-test.md`, `plan-review-tally.json`) are orthogonal to CI caching and increase review noise.
- **Reviewer**: dyn-ci-cache-interaction-output.txt
- **Concern**: - **Unrelated surface area in the same branch diff:** new files under `larch-logs/implement/BB37BF44-F430-44DF-A543-28AF3D40E517/` (`manifest.json`, `parent-issue.md`, `plan-goals-test.md`, `plan-review-tally.json`) are orthogonal to CI caching and increase review noise.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] **Pre-existing pattern elsewhere in the workflow:** `lint` / `shellcheck` / `agent-sync` jobs still use `requirements-lint.txt` with `cache: pip` only; no change required for this review’s cache-interaction scope.
- **Reviewer**: dyn-ci-cache-interaction-output.txt
- **Concern**: - **Pre-existing pattern elsewhere in the workflow:** `lint` / `shellcheck` / `agent-sync` jobs still use `requirements-lint.txt` with `cache: pip` only; no change required for this review’s cache-interaction scope.
- **Suggested revision**: Address the concern above.

