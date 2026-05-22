### FINDING_1: code-quality: Makefile:30-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Shard comment documents equal-count fill for shards 5-20 not per-harness LPT from CI timings Feature text asked for LPT greedy repartition from scraped timings to minimize max shard time across all 20 shards; hybrid packing can leave multiple mid-slow harnesses on one shard and re-inflate the wall-time ceiling relative to a true LPT remainder Either rerun full LPT on all harnesses or update the requirement PR description to the hybrid algorithm actually used
- **Suggested revision**: Address the concern above.


### FINDING_11: architecture: Makefile:30-34
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Shards 5-20 used equal-count greedy packing not full per-harness LPT. A mid-pack harness grows slower and again dominates a shard wall time despite rebalance narrative. Run full LPT on remainder or document the weaker optimization explicitly in tracking docs.
- **Suggested revision**: Address the concern above.


### FINDING_14: architecture: Makefile:30-35
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Shard rebalance for shards 5-20 uses equal-count packing with LPT tie-break only among equal-size bins, not full timing LPT as required by the plan. Slow harnesses among the long tail can cluster on one shard, raising wall time toward the job timeout while other shards stay comparatively idle; the plan’s goal of minimizing max shard runtime via LPT is only partially met. Implement per-harness timing LPT for shards 5-20 as specified, or revise the written plan/feature to the hybrid strategy and accept the longer-pole risk explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_16: **risk-integration** `.github/workflows/ci.yaml:181-198` — The job now restores `actions/setup-python`’s pip download cache (`cache: pip` with `cache-dependency-path: .github/workflows/requirements-test-harnesses.txt`) and, separately, may restore the entire `site.getsitepackages()[0]` tree via `actions/cache` (`key` uses `runner.os`, `steps.setup-python.outputs.python-version`, and `hashFiles('.github/workflows/requirements-test-harnesses.txt')`). Those keys stay aligned on the requirements hash, so there is no realistic “pip cache hit + site-packages miss” split that skips `pip install` while leaving wheels-only state: `pip install` is skipped only on an exact site-packages cache hit, which restores the installed artifacts the job relies on. The main residual integration risk is cache **key axes vs ABI**: `runner.os` remains `Linux` across `ubuntu-latest` image retargets, so a site-packages tarball that includes binary wheels (PyYAML’s compiled extension) could theoretically be restored after a future hosted-image libc/OpenSSL baseline shift while still matching the key; this is not introduced by having two pip-related caches (they do not compose into a partial-install state), but it is amplified versus “pip download cache only” because you are persisting importable binaries, not just tarballs in `/.cache/pip`. **Suggested fix:** Tie the site-packages cache key to a stronger runner baseline signal you control (for example encode the literal `runs-on` label if you pin `ubuntu-24.04`, or include an explicit repo-maintained bump token in the key on known runner migrations), or drop site-packages caching if the marginal savings aren’t worth ABI coupling to `ubuntu-latest` movement.
- **Reviewer**: dyn-ci-cache-interaction-output.txt
- **Concern**: - **risk-integration** `.github/workflows/ci.yaml:181-198` — The job now restores `actions/setup-python`’s pip download cache (`cache: pip` with `cache-dependency-path: .github/workflows/requirements-test-harnesses.txt`) and, separately, may restore the entire `site.getsitepackages()[0]` tree via `actions/cache` (`key` uses `runner.os`, `steps.setup-python.outputs.python-version`, and `hashFiles('.github/workflows/requirements-test-harnesses.txt')`). Those keys stay aligned on the requirements hash, so there is no realistic “pip cache hit + site-packages miss” split that skips `pip install` while leaving wheels-only state: `pip install` is skipped only on an exact site-packages cache hit, which restores the installed artifacts the job relies on. The main residual integration risk is cache **key axes vs ABI**: `runner.os` remains `Linux` across `ubuntu-latest` image retargets, so a site-packages tarball that includes binary wheels (PyYAML’s compiled extension) could theoretically be restored after a future hosted-image libc/OpenSSL baseline shift while still matching the key; this is not introduced by having two pip-related caches (they do not compose into a partial-install state), but it is amplified versus “pip download cache only” because you are persisting importable binaries, not just tarballs in `/.cache/pip`. **Suggested fix:** Tie the site-packages cache key to a stronger runner baseline signal you control (for example encode the literal `runs-on` label if you pin `ubuntu-24.04`, or include an explicit repo-maintained bump token in the key on known runner migrations), or drop site-packages caching if the marginal savings aren’t worth ABI coupling to `ubuntu-latest` movement.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: Makefile:119-128
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Shard rebalance does not implement full LPT across all harnesses as required; Makefile admits equal-count packing for shards 5–20. Two remaining slow harnesses can share a shard while another stays light, so max shard wall time stays above an LPT optimum and the stated minimize-max-runtime goal is only partially met. Either apply full LPT from scraped timings for all shards or update the feature/plan text to match the hybrid heuristic.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: Makefile:20-38
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Shard rebalance docs admit shards 5–20 are count-packed with LPT tie-break only, not full per-harness LPT from CI timings across all 20 shards as required by the feature/plan text. Max shard wall time may remain higher than the stated LPT-minimax target; reviewers may believe all shards were timing-driven when only 1–4 were. Either rerun true per-harness LPT across all shards using scraped timings and align comments, or narrow the feature/plan to the hybrid strategy actually used.
- **Suggested revision**: Address the concern above.


