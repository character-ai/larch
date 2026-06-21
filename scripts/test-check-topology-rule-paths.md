# scripts/test-check-topology-rule-paths.sh

Offline regression harness for `python3 python/cli.py lint topology-rule-paths`. The primary contract is `python/check_topology_rule_paths.md`.

The harness builds throwaway fixture trees under `mktemp -d`, lays out canonical inputs (`skills/shared/topology.tsv` and `.claude/rules/topology-generation.md`), and invokes `python3 "$REPO_ROOT/python/cli.py" lint topology-rule-paths --root "$dir"` from each fixture cwd. Real-registry and non-root-cwd smokes invoke the CLI without `--root` so they validate the live checkout.

It is invoked by `make test-check-topology-rule-paths` through the harness shard wiring. Keep it as the regression authority for topology parsing and validation.
