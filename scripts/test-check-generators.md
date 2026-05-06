# scripts/test-check-generators.sh - contract

Offline regression harness for `scripts/check-generators.sh`. The full walker contract is in `scripts/check-generators.md`; this harness builds throwaway git fixtures under `mktemp -d`, commits registered outputs with per-command test git identity, covers registry parsing and drift cases, and is invoked from CI through the Makefile shard target `test-check-generators`.
