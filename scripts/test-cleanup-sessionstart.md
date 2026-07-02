# scripts/test-cleanup-sessionstart.sh contract

Regression harness for `scripts/cleanup-sessionstart.sh`, the SessionStart wrapper that launches `python3 python/cli.py cleanup run` in the background.

**Scope:** The harness pins the executable-bit precondition, `hooks/hooks.json` registration, missing-`python3` and missing-`cli.py` fail-open behavior, no-stdout contract, stub CLI argument receipt, background launch syntax, `disown`, and unconditional `exit 0` source invariant.

**Executable precondition:** The harness fails first if `scripts/cleanup-sessionstart.sh` is missing or not executable (`100755`). Hooks invoke the script directly, so this is part of the runtime contract.

**Makefile target:** `make test-cleanup-sessionstart` wraps this harness through `python3 python/cli.py timing harness-mark` and is included in the bash harness shards.

**Edit-in-sync:** Update this harness when changing the hook command, matcher, timeout, CLI verb, detached-launch contract, or skip behavior documented in `scripts/cleanup-sessionstart.md`.
