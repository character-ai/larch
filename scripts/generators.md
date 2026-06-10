# scripts/generators.tsv

`scripts/generators.tsv` is the registry consumed by `python3 python/cli.py generate check`. Each non-comment row is a tab-separated `(generator-verb, output-path)` pair: column 1 is `generate <verb>`, matching a registered Python CLI generator, and column 2 is the repo-relative committed artifact that the verb's `--check` mode validates.

The walker validates row shape, duplicate verbs, duplicate outputs, path hygiene, tracked output existence, and no post-run working-tree delta, then invokes each row in-process as `python3 python/cli.py generate <verb> --check`.

Adding a row requires a registered `generate <verb>` entry in `python/cli.py`, pytest coverage in `python/test_rendering.py`, and a committed generated output path. Changes to registry grammar must update `python/rendering.py` and its tests in the same PR.
